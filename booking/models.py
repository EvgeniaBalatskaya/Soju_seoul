from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)

        # Убеждаемся, что date_joined установлен
        if 'date_joined' not in extra_fields:
            extra_fields['date_joined'] = timezone.now()

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='Email')
    is_active = models.BooleanField(default=False, verbose_name='Активен')
    is_staff = models.BooleanField(default=False, verbose_name='Персонал')
    is_email_verified = models.BooleanField(default=False, verbose_name='Email подтвержден')

    # Добавляем недостающие поля
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')
    first_name = models.CharField(max_length=30, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=30, blank=True, verbose_name='Фамилия')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Возвращает полное имя пользователя"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Возвращает короткое имя пользователя"""
        return self.first_name

    @property
    def has_active_booking(self):
        """Проверяет, есть ли у пользователя активное бронирование"""
        return self.bookings.filter(is_active=True).exists()

    def get_active_booking(self):
        """Возвращает активное бронирование пользователя"""
        return self.bookings.filter(is_active=True).first()


class Booking(models.Model):
    TIME_SLOTS = [
        ('10:00', '10:00'),
        ('12:00', '12:00'),
        ('14:00', '14:00'),
        ('16:00', '16:00'),
        ('18:00', '18:00'),
        ('20:00', '20:00'),
        ('22:00', '22:00'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    date = models.DateField()
    time = models.CharField(max_length=5, choices=TIME_SLOTS)
    guests = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    phone = models.CharField(max_length=20, blank=True)
    comment = models.TextField(blank=True)

    # Поле is_active для бронирования
    is_active = models.BooleanField(default=True, verbose_name='Активное бронирование')

    class Meta:
        ordering = ['-date', '-time']
        # Уникальность даты и времени для активных бронирований
        constraints = [
            models.UniqueConstraint(
                fields=['date', 'time'],
                condition=models.Q(is_active=True),
                name='unique_active_booking_per_datetime'
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.date} {self.time}"

    def clean(self):
        """Валидация при сохранении"""
        # Проверяем, что время еще не занято
        if self.is_active:
            conflicting_booking = Booking.objects.filter(
                date=self.date,
                time=self.time,
                is_active=True
            ).exclude(pk=self.pk).first()

            if conflicting_booking:
                raise ValidationError(
                    f"Время {self.time} на дату {self.date} уже занято"
                )

        # Проверяем, что у пользователя нет других активных бронирований
        if self.is_active and self.user_id:
            existing_active = Booking.objects.filter(
                user=self.user,
                is_active=True
            ).exclude(pk=self.pk).first()

            if existing_active:
                raise ValidationError(
                    f"У пользователя уже есть активное бронирование на {existing_active.date} {existing_active.time}"
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_available_slots(cls, date):
        """Возвращает список свободных временных слотов на указанную дату"""
        booked_slots = cls.objects.filter(
            date=date,
            is_active=True
        ).values_list('time', flat=True)

        all_slots = [slot[0] for slot in cls.TIME_SLOTS]
        available_slots = [slot for slot in all_slots if slot not in booked_slots]

        return available_slots

    @property
    def is_upcoming(self):
        """Проверяет, является ли бронирование будущим"""
        from django.utils import timezone
        import datetime
        booking_datetime = datetime.datetime.combine(
            self.date,
            datetime.time.fromisoformat(self.time)
        )
        return booking_datetime > timezone.now()