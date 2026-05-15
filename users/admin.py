from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import StaffUser

class StaffUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = StaffUser
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'role', 'nonprofit', 'phone')

class StaffUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = StaffUser
        fields = '__all__'

@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    form = StaffUserChangeForm
    add_form = StaffUserCreationForm
    actions = ('disable_staff_login',)
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'nonprofit', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'nonprofit', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'nonprofit')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Staff info', {'fields': ('role', 'nonprofit')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'role', 'nonprofit', 'phone', 'is_staff', 'is_active'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')

    def has_delete_permission(self, request, obj=None):
        """Staff user history should be retained; disable login instead."""
        return False

    def delete_model(self, request, obj):
        obj.is_active = False
        obj.save(update_fields=['is_active'])

    def delete_queryset(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description='Disable login for selected staff users')
    def disable_staff_login(self, request, queryset):
        updated = queryset.exclude(pk=request.user.pk).update(is_active=False)
        skipped_self = queryset.filter(pk=request.user.pk).exists()

        message = f'Login disabled for {updated} staff user(s).'
        if skipped_self:
            message += ' Your own login was left active.'

        self.message_user(request, message)
