from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    
    def ready(self):
        # Admin site customization
        from django.contrib import admin
        admin.site.site_header = "Mission Hiring Hall - Staff Admin"
        admin.site.site_title = "Staff Admin"
        admin.site.index_title = "Welcome to Staff Administration"