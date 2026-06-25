from django.db import models
from django.utils import timezone


class Account(models.Model):
    """Собственная таблица пользователей, не django.contrib.auth.User."""

    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts'
        ordering = ['id']

    def __str__(self):
        return self.email

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return ' '.join(part for part in parts if part).strip()


class AuthSession(models.Model):
    """Серверная часть JWT-сессии. Logout делает токены недействительными."""

    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sessions')
    jti = models.CharField(max_length=64, unique=True)
    refresh_token_hash = models.CharField(max_length=128, unique=True)
    user_agent = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    logged_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'auth_sessions'
        ordering = ['-created_at']

    @property
    def is_active(self) -> bool:
        return self.logged_out_at is None and self.expires_at > timezone.now()


class Role(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'roles'
        ordering = ['code']

    def __str__(self):
        return self.code


class UserRole(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'user_roles'
        unique_together = ('user', 'role')


class Resource(models.Model):
    code = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'resources'
        ordering = ['code']

    def __str__(self):
        return self.code


class Action(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    title = models.CharField(max_length=100)

    class Meta:
        db_table = 'actions'
        ordering = ['code']

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='permissions')
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='permissions')
    is_allowed = models.BooleanField(default=True)

    class Meta:
        db_table = 'role_permissions'
        unique_together = ('role', 'resource', 'action')
        ordering = ['role__code', 'resource__code', 'action__code']

    def __str__(self):
        return f'{self.role.code}:{self.resource.code}:{self.action.code}={self.is_allowed}'
