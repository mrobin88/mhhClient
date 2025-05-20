from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'dob', 'gender', 'language', 'staff_name')
    list_filter = ('gender', 'language', 'demographic_info', 'orientation', 'highest_degree', 'employment_status')
    search_fields = ('first_name', 'last_name', 'phone', 'staff_name', 'nonprofit')
