from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models


class MenuContent(models.Model):
    section = models.CharField(max_length=50, unique=True, verbose_name='Секция')
    title_kr = models.CharField(max_length=200, verbose_name='Заголовок корейский')
    title_ru = models.CharField(max_length=200, verbose_name='Заголовок русский')
    content_ru = models.TextField(verbose_name='Текст русский')
    image = models.ImageField(upload_to='menu/', blank=True, null=True, verbose_name='Изображение')

    class Meta:
        verbose_name = 'Контент меню'
        verbose_name_plural = 'Контент меню'

    def __str__(self):
        return self.section


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

    is_active = models.BooleanField(default=True, verbose_name='Активное бронирование')

    class Meta:
        ordering = ['-date', '-time']
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
        if self.is_active:
            # Проверяем, что время еще не занято
            conflicting_booking = Booking.objects.filter(
                date=self.date,
                time=self.time,
                is_active=True
            ).exclude(pk=self.pk).first()

            if conflicting_booking:
                raise ValidationError(
                    f"Время {self.time} на дату {self.date} уже занято"
                )

            # Проверяем доступность мест
            available_capacity = self.get_available_capacity(self.date, self.time)
            if available_capacity < self.guests:
                raise ValidationError(
                    f"Недостаточно свободных мест. Доступно: {available_capacity}"
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

    @classmethod
    def get_available_capacity(cls, date, time):
        """Возвращает количество свободных мест на указанные дату и время"""
        try:
            capacity_settings = RestaurantCapacity.objects.first()
            total_capacity = capacity_settings.total_capacity if capacity_settings else 50
        except (RestaurantCapacity.DoesNotExist, AttributeError):
            total_capacity = 50

        # Суммируем всех гостей на выбранные дату и время
        booked_guests = cls.objects.filter(
            date=date,
            time=time,
            is_active=True
        ).aggregate(total=models.Sum('guests'))['total'] or 0

        available = total_capacity - booked_guests
        return max(0, available)

    @classmethod
    def get_capacity_info(cls, date, time):
        """Полная информация о вместимости"""
        available = cls.get_available_capacity(date, time)

        try:
            capacity_settings = RestaurantCapacity.objects.first()
            total_capacity = capacity_settings.total_capacity if capacity_settings else 50
            max_per_booking = capacity_settings.max_guests_per_booking if capacity_settings else 10
        except (RestaurantCapacity.DoesNotExist, AttributeError):
            total_capacity = 50
            max_per_booking = 10

        return {
            'available_capacity': available,
            'total_capacity': total_capacity,
            'max_per_booking': max_per_booking,
            'is_available': available > 0
        }

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


class RestaurantCapacity(models.Model):
    """Модель для хранения вместимости ресторана"""
    total_capacity = models.PositiveIntegerField(default=50, verbose_name='Общее количество мест')
    max_guests_per_booking = models.PositiveIntegerField(default=10,
                                                         verbose_name='Максимум гостей в одном бронировании')

    class Meta:
        verbose_name = 'Вместимость ресторана'
        verbose_name_plural = 'Вместимость ресторана'

    def save(self, *args, **kwargs):
        # Разрешаем только одну запись
        if not self.pk and RestaurantCapacity.objects.exists():
            return
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Вместимость: {self.total_capacity} мест"
