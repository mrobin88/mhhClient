from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from users.models import StaffUser


class Command(BaseCommand):
    help = 'Fix staff user permissions and create necessary groups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-groups',
            action='store_true',
            help='Create default staff groups with permissions',
        )

    def handle(self, *args, **options):
        self.stdout.write("Fixing staff user permissions...")

        # Fix existing staff users
        staff_users = StaffUser.objects.all()
        fixed_count = 0

        for user in staff_users:
            updated = False
            
            # Ensure staff users have is_staff=True
            if user.role in ['admin', 'case_manager', 'counselor'] and not user.is_staff:
                user.is_staff = True
                updated = True
                self.stdout.write(f"  - Set is_staff=True for {user.username}")

            # Ensure users are active
            if not user.is_active:
                user.is_active = True
                updated = True
                self.stdout.write(f"  - Set is_active=True for {user.username}")

            if updated:
                user.save()
                fixed_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Fixed {fixed_count} staff users')
        )

        # Create groups if requested
        if options['create_groups']:
            self.create_default_groups()

    def create_default_groups(self):
        self.stdout.write("Creating default staff groups...")

        # Get content types
        user_ct = ContentType.objects.get_for_model(StaffUser)
        
        # Define groups and their permissions
        groups_config = {
            'Administrators': {
                'permissions': ['add_staffuser', 'change_staffuser', 'delete_staffuser', 'view_staffuser']
            },
            'Case Managers': {
                'permissions': ['add_staffuser', 'change_staffuser', 'view_staffuser']
            },
            'Counselors': {
                'permissions': ['change_staffuser', 'view_staffuser']
            },
            'Volunteers': {
                'permissions': ['view_staffuser']
            }
        }

        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                self.stdout.write(f"  - Created group: {group_name}")
            else:
                self.stdout.write(f"  - Group already exists: {group_name}")

            # Add permissions to group
            for perm_codename in config['permissions']:
                try:
                    permission = Permission.objects.get(
                        codename=perm_codename,
                        content_type=user_ct
                    )
                    group.permissions.add(permission)
                    self.stdout.write(f"    - Added permission: {perm_codename}")
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"    - Permission not found: {perm_codename}")
                    )

        self.stdout.write(
            self.style.SUCCESS('Default groups created successfully')
        )
