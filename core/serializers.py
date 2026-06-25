from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from core.models import Account, Action, Resource, Role, RolePermission, UserRole


class AccountSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'email', 'last_name', 'first_name', 'middle_name',
            'full_name', 'is_active', 'is_deleted', 'created_at', 'updated_at', 'roles',
        ]
        read_only_fields = ['id', 'full_name', 'is_active', 'is_deleted', 'created_at', 'updated_at', 'roles']

    def get_roles(self, obj):
        return list(obj.user_roles.select_related('role').values_list('role__code', flat=True))


class RegisterSerializer(serializers.Serializer):
    last_name = serializers.CharField(max_length=100)
    first_name = serializers.CharField(max_length=100)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_repeat = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        email = value.lower().strip()
        if Account.objects.filter(email=email).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует.')
        return email

    def validate(self, attrs):
        if attrs['password'] != attrs['password_repeat']:
            raise serializers.ValidationError({'password_repeat': 'Пароли не совпадают.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_repeat')
        raw_password = validated_data.pop('password')
        user = Account.objects.create(password_hash=make_password(raw_password), **validated_data)
        role, _ = Role.objects.get_or_create(code='user', defaults={'title': 'Обычный пользователь'})
        UserRole.objects.get_or_create(user=user, role=role)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['last_name', 'first_name', 'middle_name', 'email']

    def validate_email(self, value):
        email = value.lower().strip()
        user = self.instance
        if Account.objects.exclude(id=user.id).filter(email=email).exists():
            raise serializers.ValidationError('Этот email уже занят.')
        return email


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'code', 'title', 'description']


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id', 'code', 'title', 'description']


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['id', 'code', 'title']


class RolePermissionSerializer(serializers.ModelSerializer):
    role_code = serializers.SlugRelatedField(source='role', slug_field='code', queryset=Role.objects.all())
    resource_code = serializers.SlugRelatedField(source='resource', slug_field='code', queryset=Resource.objects.all())
    action_code = serializers.SlugRelatedField(source='action', slug_field='code', queryset=Action.objects.all())

    class Meta:
        model = RolePermission
        fields = ['id', 'role_code', 'resource_code', 'action_code', 'is_allowed']


class UserRoleSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(source='user', queryset=Account.objects.all())
    role_code = serializers.SlugRelatedField(source='role', slug_field='code', queryset=Role.objects.all())

    class Meta:
        model = UserRole
        fields = ['id', 'user_id', 'role_code', 'assigned_at']
        read_only_fields = ['id', 'assigned_at']
