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
