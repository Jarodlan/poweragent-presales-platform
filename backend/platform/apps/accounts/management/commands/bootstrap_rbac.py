from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Permission, Role, RolePermission
from apps.accounts.rbac import PERMISSION_SEEDS, ROLE_SEEDS


class Command(BaseCommand):
    help = "Initialize departments, roles and permissions for RBAC."

    @transaction.atomic
    def handle(self, *args, **options):
        permission_map = {}
        created_permissions = 0
        for seed in PERMISSION_SEEDS:
            permission, created = Permission.objects.update_or_create(
                code=seed.code,
                defaults={
                    "name": seed.name,
                    "module": seed.module,
                    "action": seed.action,
                    "resource_scope": seed.resource_scope,
                    "description": seed.description,
                },
            )
            permission_map[seed.code] = permission
            created_permissions += int(created)

        created_roles = 0
        for role_code, role_config in ROLE_SEEDS.items():
            role, created = Role.objects.update_or_create(
                code=role_code,
                defaults={
                    "name": role_config["name"],
                    "description": role_config["description"],
                    "data_scope": role_config["data_scope"],
                    "is_system": True,
                },
            )
            created_roles += int(created)
            RolePermission.objects.filter(role=role).exclude(
                permission__code__in=role_config["permissions"]
            ).delete()
            for permission_code in role_config["permissions"]:
                RolePermission.objects.get_or_create(role=role, permission=permission_map[permission_code])

        self.stdout.write(
            self.style.SUCCESS(
                f"RBAC initialized: permissions(created={created_permissions}, total={Permission.objects.count()}), roles(created={created_roles}, total={Role.objects.count()})"
            )
        )
