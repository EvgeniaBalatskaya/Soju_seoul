from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.contrib import messages
from django.contrib.auth.forms import UserChangeForm  # Добавьте этот импорт
from .models import CustomUser, Booking


class CustomUserChangeForm(UserChangeForm):  # Наследуем от UserChangeForm вместо ModelForm
    class Meta:
        model = CustomUser
        fields = '__all__'


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    readonly_fields = ('date', 'time', 'guests', 'phone', 'comment', 'created_at', 'is_active')
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    form = CustomUserChangeForm

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_email_verified', 'date_joined',
                    'has_active_booking')
    list_filter = ('is_staff', 'is_active', 'is_email_verified', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('last_login', 'date_joined')

    inlines = [BookingInline]

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),  # Добавил секцию с именами
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Status', {'fields': ('is_email_verified',)}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),  # Добавил секцию с датами
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
         ),
    )

    actions = ['delete_selected']

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            if 'delete_selected' in actions:
                del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        try:
            user_email = obj.email  # Сохраняем email до удаления
            Booking.objects.filter(user=obj).delete()
            obj.delete()
            messages.success(request, f'Пользователь {user_email} и все его бронирования успешно удалены.')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении пользователя: {str(e)}')

    def delete_queryset(self, request, queryset):
        try:
            count = queryset.count()
            # Удаляем бронирования всех пользователей одним запросом
            user_ids = queryset.values_list('id', flat=True)
            Booking.objects.filter(user_id__in=user_ids).delete()
            queryset.delete()  # Удаляем пользователей одним запросом
            messages.success(request, f'Успешно удалено {count} пользователей и их бронирования.')
        except Exception as e:
            messages.error(request, f'Ошибка при массовом удалении: {str(e)}')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'time', 'guests', 'is_active', 'created_at')
    list_filter = ('date', 'is_active', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('created_at',)
    date_hierarchy = 'date'  # Добавляет навигацию по датам

    fieldsets = (
        (None, {'fields': ('user', 'date', 'time', 'guests', 'is_active')}),
        ('Contact Information', {'fields': ('phone',)}),
        ('Additional Information', {'fields': ('comment',)}),
        ('System Information', {'fields': ('created_at',)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.register(CustomUser, CustomUserAdmin)
