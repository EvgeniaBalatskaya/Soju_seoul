from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('menu/', views.menu_page, name='menu_page'),

    # Бронирование
    path('booking/', views.booking_view, name='booking_page'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('booking/slots/', views.get_available_slots, name='get_available_slots'),

    # Аккаунт
    path('account/', views.personal_account, name='personal_account'),

    # Аутентификация
    path('login/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout_user'),
    path('register/', views.register_user, name='register_user'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),

    # Обратная связь
    path('send-feedback/', views.send_feedback, name='send_feedback'),
]