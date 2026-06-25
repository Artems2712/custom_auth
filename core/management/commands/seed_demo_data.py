from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from core.models import Account, Action, Resource, Role, RolePermission, UserRole


class Command(BaseCommand):
    help = 'Создает тестовые роли, ресурсы, действия, права и пользователей.'

    def handle(self, *args, **options):
        actions = {
            'read': 'Чтение',
            'create': 'Создание',
            'update': 'Изменение',
            'delete': 'Удаление',
            'manage': 'Управление',
        }
        resources = {
            'documents': 'Документы',
            'reports': 'Отчеты',
            'profile': 'Профиль пользователя',
            'admin_rules': 'Правила доступа',
            'admin_dashboard': 'Административная панель',
        }
        roles = {
            'admin': ('Администратор', 'Полный доступ к управлению правилами и mock-ресурсам.'),
            'manager': ('Менеджер', 'Может читать отчеты и читать/создавать документы.'),
            'user': ('Пользователь', 'Минимальный доступ только к документам.'),
        }

        action_map = {}
        for code, title in actions.items():
            action_map[code], _ = Action.objects.get_or_create(code=code, defaults={'title': title})

        resource_map = {}
        for code, title in resources.items():
            resource_map[code], _ = Resource.objects.get_or_create(code=code, defaults={'title': title})

        role_map = {}
        for code, (title, description) in roles.items():
            role_map[code], _ = Role.objects.get_or_create(code=code, defaults={'title': title, 'description': description})

        # Администратор получает все права на все ресурсы и действия.
        for resource in resource_map.values():
            for action in action_map.values():
                RolePermission.objects.update_or_create(
                    role=role_map['admin'],
                    resource=resource,
                    action=action,
                    defaults={'is_allowed': True},
                )

        manager_rules = [
            ('documents', 'read'),
            ('documents', 'create'),
            ('documents', 'update'),
            ('reports', 'read'),
            ('profile', 'read'),
            ('profile', 'update'),
        ]
        user_rules = [
            ('documents', 'read'),
            ('profile', 'read'),
            ('profile', 'update'),
        ]
        for resource_code, action_code in manager_rules:
            RolePermission.objects.update_or_create(
                role=role_map['manager'],
                resource=resource_map[resource_code],
                action=action_map[action_code],
                defaults={'is_allowed': True},
            )
        for resource_code, action_code in user_rules:
            RolePermission.objects.update_or_create(
                role=role_map['user'],
                resource=resource_map[resource_code],
                action=action_map[action_code],
                defaults={'is_allowed': True},
            )

        demo_users = [
            ('admin@example.com', 'Admin123!', 'Админов', 'Админ', 'Админович', 'admin'),
            ('manager@example.com', 'Manager123!', 'Иванов', 'Иван', 'Иванович', 'manager'),
            ('user@example.com', 'User123!', 'Петров', 'Петр', 'Петрович', 'user'),
        ]
        for email, password, last_name, first_name, middle_name, role_code in demo_users:
            user, created = Account.objects.get_or_create(
                email=email,
                defaults={
                    'password_hash': make_password(password),
                    'last_name': last_name,
                    'first_name': first_name,
                    'middle_name': middle_name,
                    'is_active': True,
                    'is_deleted': False,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан пользователь {email} / {password}'))
            UserRole.objects.get_or_create(user=user, role=role_map[role_code])

        self.stdout.write(self.style.SUCCESS('Демо-данные готовы.'))
