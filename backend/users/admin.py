from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import StaffUser

@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'nonprofit', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'nonprofit', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'nonprofit')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Staff info', {'fields': ('role', 'nonprofit')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'role', 'nonprofit'),
        }),
    )
