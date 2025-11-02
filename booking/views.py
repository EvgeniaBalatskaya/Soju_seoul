from django.views.generic import TemplateView
from django.contrib.auth import login, logout
from .forms import UserRegistrationForm, UserLoginForm
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Booking, CustomUser
from django.utils.http import urlsafe_base64_decode
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
import datetime
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from .models import MenuContent


# Страницы
class HomeView(TemplateView):
    template_name = 'booking/home_page.html'


def menu_page(request):
    # Получаем или создаем контент по умолчанию
    sections = ['intro', 'kimchi', 'kimbap', 'tteokbokki', 'jjajangmyeon', 'soju', 'footer']

    for section in sections:
        MenuContent.objects.get_or_create(section=section)

    content_items = MenuContent.objects.all()
    content_dict = {item.section: item for item in content_items}

    context = {
        'intro': content_dict.get('intro'),
        'kimchi': content_dict.get('kimchi'),
        'kimbap': content_dict.get('kimbap'),
        'tteokbokki': content_dict.get('tteokbokki'),
        'jjajangmyeon': content_dict.get('jjajangmyeon'),
        'soju': content_dict.get('soju'),
        'footer': content_dict.get('footer'),
    }
    return render(request, 'booking/menu_page.html', context)


# Регистрация
def register_user(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        login_form = UserLoginForm()
        if form.is_valid():
            email = form.cleaned_data['email']

            # Проверяем, есть ли неактивный пользователь с таким email
            try:
                existing_user = CustomUser.objects.get(email=email, is_active=False)
                # Если есть неактивный пользователь, удаляем его и создаем нового
                existing_user.delete()
            except CustomUser.DoesNotExist:
                pass

            # Создаем нового пользователя
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.is_active = False
            user.is_email_verified = False
            user.save()

            # Отправка email подтверждения
            current_site = get_current_site(request)
            mail_subject = 'Подтвердите ваш email - Soju & Seoul'

            try:
                html_message = render_to_string('booking/email_verification.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                    'protocol': 'https' if request.is_secure() else 'http',
                })

                send_mail(
                    mail_subject,
                    '',  # пустой текст
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                    html_message=html_message
                )
                messages.success(request, 'Регистрация успешна! Проверьте вашу почту для подтверждения.',
                                 extra_tags='registration_success')
            except Exception as e:
                print(f"Email sending error: {e}")
                # Все равно создаем пользователя, даже если email не отправился
                messages.success(request, 'Регистрация успешна!', extra_tags='registration_success')

            return render(request, "booking/home_page.html", {
                "login_form": login_form,
                "register_form": UserRegistrationForm(),
            })
        else:
            # Обрабатываем ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    if field == 'email' and 'already exists' in error:
                        messages.error(request,
                                       'Пользователь с таким email уже зарегистрирован. Попробуйте войти или восстановить пароль.',
                                       extra_tags='register')
                    else:
                        messages.error(request, f'{error}', extra_tags='register')
            return render(request, "booking/home_page.html", {
                "login_form": login_form,
                "register_form": form
            })
    return redirect("home")


# Подтверждение email
def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        if hasattr(user, 'is_email_verified'):
            user.is_email_verified = True
        user.save()
        messages.success(request, 'Email успешно подтвержден! Теперь вы можете войти в систему.',
                         extra_tags='email_verified')
        return redirect("home")
    else:
        messages.error(request, 'Ссылка для подтверждения недействительна или устарела.',
                       extra_tags='email_verified_error')
        return redirect("home")


# Логин (отдельный endpoint)
def login_user(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)

                return redirect('home')
            else:
                messages.error(request, 'Неверный email или пароль', extra_tags='login error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}', extra_tags='login error')
    return redirect('home')


# Выход
def logout_user(request):
    logout(request)
    return redirect("home")


# Бронирование
def booking_page(request, booking_id=None):
    """
    Универсальный view для бронирования:
    - Для неавторизованных: информационная страница booking_page.html
    - Для авторизованных: форма бронирования (через модалку)
    """
    # Если пользователь не авторизован - показываем гостевую страницу
    if not request.user.is_authenticated:
        return render(request, 'booking/booking_page.html')

    # Дальше код для авторизованных пользователей (обработка формы из модалки)
    # Если передан booking_id - это редактирование существующего бронирования
    editing_booking = None
    if booking_id:
        try:
            editing_booking = Booking.objects.get(id=booking_id, user=request.user)
            if not editing_booking.is_active:
                messages.error(request, 'Нельзя редактировать отмененное бронирование.')
                return redirect('personal_account')
        except Booking.DoesNotExist:
            messages.error(request, 'Бронирование не найдено.')
            return redirect('personal_account')

    if request.method == 'POST':
        date = request.POST.get('date')
        time = request.POST.get('time')
        guests = request.POST.get('guests')
        phone = request.POST.get('phone', '')
        comment = request.POST.get('comment', '')

        # При редактировании не проверяем активное бронирование
        if not booking_id and request.user.has_active_booking:
            messages.error(request, 'У вас уже есть активное бронирование. Отмените его чтобы создать новое.')
            return redirect('personal_account')

        try:
            guests = int(guests)
            if guests <= 0 or guests > 20:
                messages.error(request, 'Количество гостей должно быть от 1 до 20.')
                return redirect('home')  # Возвращаем на главную, где есть модалка

            if booking_id and editing_booking:
                # Обновляем существующее бронирование
                editing_booking.date = date
                editing_booking.time = time
                editing_booking.guests = guests
                editing_booking.phone = phone
                editing_booking.comment = comment
                editing_booking.save()
            else:
                # Создаем новое бронирование
                booking = Booking(
                    user=request.user,
                    date=date,
                    time=time,
                    guests=guests,
                    phone=phone,
                    comment=comment
                )
                booking.save()

            return redirect('personal_account')

        except ValidationError as e:
            messages.error(request, f'Ошибка при бронировании: {str(e)}', extra_tags='booking error')
            return redirect('home')  # Возвращаем на главную, где есть модалка
        except Exception as e:
            messages.error(request, f'Ошибка при бронировании: {str(e)}', extra_tags='booking error')
            return redirect('home')  # Возвращаем на главную, где есть модалка

    # GET запрос для авторизованных не должен сюда попадать (они используют модалку)
    return redirect('home')


# Отмена бронирования
@login_required
def cancel_booking(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        if booking.is_active:
            booking.is_active = False
            booking.save()
        else:
            messages.error(request, 'Это бронирование уже отменено.')
    except Booking.DoesNotExist:
        messages.error(request, 'Бронирование не найдено.')

    return redirect('personal_account')


def get_available_slots(request):
    """
    Получение доступных слотов для бронирования.
    Доступно для всех пользователей (авторизованных и нет)
    """
    date = request.GET.get('date')
    if date:
        try:
            selected_date = datetime.date.fromisoformat(date)
            available_slots = Booking.get_available_slots(selected_date)
            return JsonResponse({'available_slots': available_slots})
        except ValueError:
            return JsonResponse({'error': 'Неверный формат даты'}, status=400)
    return JsonResponse({'error': 'Дата не указана'}, status=400)


def get_capacity_info(request):
    """API для получения информации о свободных местах"""
    if request.method == 'GET':
        selected_date = request.GET.get('date')
        selected_time = request.GET.get('time')

        if selected_date and selected_time:
            capacity_info = Booking.get_capacity_info(selected_date, selected_time)
            return JsonResponse(capacity_info)

    return JsonResponse({'error': 'Invalid request'})


# Аккаунт
@login_required
def personal_account(request):
    # Получаем все бронирования пользователя (активные и неактивные)
    bookings = Booking.objects.filter(user=request.user).order_by('-date', '-time')

    # Получаем активное бронирование
    active_booking = request.user.get_active_booking()

    return render(request, 'booking/personal_account.html', {
        'bookings': bookings,
        'active_booking': active_booking
    })


# Обратная связь
def send_feedback(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        message = request.POST.get('message')

        # Импортируем CustomUser вместо стандартного User
        from .models import CustomUser

        # Получаем всех суперпользователей из CustomUser
        superusers = CustomUser.objects.filter(is_superuser=True)

        if superusers.exists():
            admin_emails = [user.email for user in superusers]
        else:
            admin_emails = [settings.DEFAULT_FROM_EMAIL]

        subject = f'Обратная связь от {name} - Soju & Seoul'
        email_message = f"""
        Новое сообщение обратной связи с сайта Soju & Seoul:

        Имя: {name}
        Email: {email}
        Телефон: {phone if phone else 'Не указан'}

        Сообщение:
        {message}

        ---
        Отправлено через форму обратной связи сайта.
        """

        try:
            from django.core.mail import send_mail
            send_mail(
                subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=False,
            )

            messages.success(request, '✅ Ваше сообщение успешно отправлено! Мы свяжемся с вами в ближайшее время.')

        except Exception as e:
            messages.error(request, '❌ Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.')
            print(f"Email sending error: {e}")

        return redirect('home')

    return redirect('home')
