from django.contrib import admin
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
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
    actions = ('disable_staff_login', 'text_staff_login_help')
    
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

    def has_add_permission(self, request):
        """Only superusers can create new staff logins from admin."""
        return bool(request.user and request.user.is_superuser)

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

    @admin.action(description='Text login link and username to selected staff')
    def text_staff_login_help(self, request, queryset):
        from clients.notifications import send_phone_text_message

        if not getattr(settings, 'AZURE_COMMUNICATION_CONNECTION_STRING', ''):
            self.message_user(
                request,
                'SMS not configured: missing AZURE_COMMUNICATION_CONNECTION_STRING in app settings.',
                level=messages.ERROR,
            )
            return
        if not getattr(settings, 'AZURE_COMMUNICATION_SMS_FROM', ''):
            self.message_user(
                request,
                'SMS not configured: missing AZURE_COMMUNICATION_SMS_FROM in app settings.',
                level=messages.ERROR,
            )
            return

        sent = 0
        skipped = 0
        failed = 0
        email_backup_sent = 0
        email_backup_failed = 0
        reason_counts = {}

        for user in queryset:
            phone = (user.phone or '').strip()
            if not phone:
                skipped += 1
                continue

            username = (user.username or '').strip() or 'your username'
            message_body = (
                "Mission Hiring Hall Admin login:\n"
                "https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/\n"
                f"Username: {username}\n"
                "If you cannot log in, contact 9255507522 Matthew Robin."
            )
            ok, detail = send_phone_text_message(phone=phone, body=message_body[:480])
            if ok:
                sent += 1
            else:
                failed += 1
                reason_counts[detail] = reason_counts.get(detail, 0) + 1

            # Carrier delivery can still fail after a 202 acceptance; email backup keeps
            # internal login instructions reachable.
            if getattr(settings, 'SMS_FORCE_EMAIL_BACKUP', True):
                email = (user.email or '').strip()
                if email:
                    try:
                        send_mail(
                            subject='Mission Hiring Hall Admin Login Help',
                            message=message_body,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@missionhiringhall.org'),
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        email_backup_sent += 1
                    except Exception as exc:
                        email_backup_failed += 1
                        reason = f'Email backup failed: {exc}'
                        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        level = messages.SUCCESS if failed == 0 else messages.WARNING
        reason_text = ''
        if reason_counts:
            top_reasons = ', '.join(f'{reason} ({count})' for reason, count in list(reason_counts.items())[:3])
            reason_text = f' Top failures: {top_reasons}.'
        self.message_user(
            request,
            (
                f'Staff login texts queued: {sent}. Skipped (no phone): {skipped}. Failed: {failed}. '
                f'Email backup sent: {email_backup_sent}. Email backup failed: {email_backup_failed}.{reason_text}'
            ),
            level=level,
        )
