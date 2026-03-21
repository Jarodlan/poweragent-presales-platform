from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Department, Role, User, UserRole


class Command(BaseCommand):
    help = "Create or update the initial super administrator account."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument("--display-name", default="超级管理员")
        parser.add_argument("--department-code", default="platform")
        parser.add_argument("--department-name", default="平台管理部")

    @transaction.atomic
    def handle(self, *args, **options):
        role = Role.objects.filter(code="super_admin").first()
        if not role:
            raise CommandError("super_admin role does not exist. Please run bootstrap_rbac first.")

        department, _ = Department.objects.get_or_create(
            code=options["department_code"],
            defaults={"name": options["department_name"], "status": "active"},
        )

        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={
                "email": options["email"],
                "display_name": options["display_name"],
                "department": department,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "account_status": "active",
                "data_scope": "all",
                "force_password_change": False,
                "password_changed_at": timezone.now(),
            },
        )

        user.email = options["email"]
        user.display_name = options["display_name"]
        user.department = department
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.account_status = "active"
        user.data_scope = "all"
        user.force_password_change = False
        user.password_changed_at = timezone.now()
        user.set_password(options["password"])
        user.save()

        UserRole.objects.get_or_create(user=user, role=role, department=department)

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Super admin {action}: {user.username}"))
