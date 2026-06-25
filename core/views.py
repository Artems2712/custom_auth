from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Account, Action, AuthSession, Resource, Role, RolePermission, UserRole
from core.security import create_token_pair, get_authenticated_user, has_access, refresh_access_token, verify_password
from core.serializers import (
    AccountSerializer,
    ActionSerializer,
    LoginSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    ResourceSerializer,
    RolePermissionSerializer,
    RoleSerializer,
    UpdateProfileSerializer,
    UserRoleSerializer,
)


class AuthenticatedAPIView(APIView):
    """Базовый класс: 401, если пользователя нельзя определить по JWT."""

    current_user = None

    def get_authenticate_header(self, request):
        # Нужно, чтобы DRF возвращал именно 401, а не 403, когда токен отсутствует/битый.
        return 'Bearer'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.current_user = get_authenticated_user(request._request)


class AccessControlledAPIView(AuthenticatedAPIView):
    """Базовый класс: 403, если пользователь есть, но правила доступа не разрешают действие."""

    resource_code = None
    action_code = None
    method_action_map = {}

    def get_required_action(self, request):
        return self.method_action_map.get(request.method.lower(), self.action_code)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        required_action = self.get_required_action(request)
        if not has_access(self.current_user, self.resource_code, required_action):
            raise PermissionDenied(
                f'Нет доступа: требуется право {self.resource_code}:{required_action}.'
            )


class HealthView(APIView):
    def get(self, request):
        return Response({'status': 'ok'})


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AccountSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower().strip()
        password = serializer.validated_data['password']

        try:
            user = Account.objects.get(email=email, is_active=True, is_deleted=False)
        except Account.DoesNotExist:
            raise ValidationError({'credentials': 'Неверный email или пароль.'})

        if not verify_password(password, user.password_hash):
            raise ValidationError({'credentials': 'Неверный email или пароль.'})

        pair = create_token_pair(user, request._request)
        return Response({
            'access_token': pair.access_token,
            'refresh_token': pair.refresh_token,
            'token_type': 'Bearer',
            'expires_in_minutes': settings.JWT_ACCESS_TTL_MINUTES,
            'user': AccountSerializer(user).data,
        })


class RefreshTokenView(APIView):
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token, user = refresh_access_token(serializer.validated_data['refresh_token'])
        return Response({
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in_minutes': settings.JWT_ACCESS_TTL_MINUTES,
            'user': AccountSerializer(user).data,
        })


class LogoutView(AuthenticatedAPIView):
    def post(self, request):
        request._request.auth_session.logged_out_at = timezone.now()
        request._request.auth_session.save(update_fields=['logged_out_at'])
        return Response({'detail': 'Logout выполнен. Текущая JWT-сессия завершена.'})


class MeView(AuthenticatedAPIView):
    def get(self, request):
        return Response(AccountSerializer(self.current_user).data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(self.current_user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AccountSerializer(self.current_user).data)

    @transaction.atomic
    def delete(self, request):
        user = self.current_user
        user.is_active = False
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.save(update_fields=['is_active', 'is_deleted', 'deleted_at', 'updated_at'])
        AuthSession.objects.filter(user=user, logged_out_at__isnull=True).update(logged_out_at=timezone.now())
        return Response({'detail': 'Аккаунт мягко удален. Повторный вход невозможен.'})


class AdminAccessRulesView(AccessControlledAPIView):
    resource_code = 'admin_rules'
    action_code = 'manage'

    def get(self, request):
        return Response({
            'users': AccountSerializer(Account.objects.all(), many=True).data,
            'roles': RoleSerializer(Role.objects.all(), many=True).data,
            'resources': ResourceSerializer(Resource.objects.all(), many=True).data,
            'actions': ActionSerializer(Action.objects.all(), many=True).data,
            'permissions': RolePermissionSerializer(RolePermission.objects.select_related('role', 'resource', 'action'), many=True).data,
            'user_roles': UserRoleSerializer(UserRole.objects.select_related('user', 'role'), many=True).data,
        })


class AdminRolesView(AccessControlledAPIView):
    resource_code = 'admin_rules'
    action_code = 'manage'

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


class AdminResourcesView(AccessControlledAPIView):
    resource_code = 'admin_rules'
    action_code = 'manage'

    def post(self, request):
        serializer = ResourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resource = serializer.save()
        return Response(ResourceSerializer(resource).data, status=status.HTTP_201_CREATED)


class AdminActionsView(AccessControlledAPIView):
    resource_code = 'admin_rules'
    action_code = 'manage'

    def post(self, request):
        serializer = ActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.save()
        return Response(ActionSerializer(action).data, status=status.HTTP_201_CREATED)


class AdminPermissionsView(AccessControlledAPIView):
    resource_code = 'admin_rules'
    action_code = 'manage'

    def post(self, request):
        serializer = RolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data['role']
        resource = serializer.validated_data['resource']
        action = serializer.validated_data['action']
        permission, _ = RolePermission.objects.update_or_create(
            role=role,
            resource=resource,
            action=action,
            defaults={'is_allowed': serializer.validated_data.get('is_allowed', True)},
        )
        return Response(RolePermissionSerializer(permission).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        role_code = request.data.get('role_code')
        resource_code = request.data.get('resource_code')
        action_code = request.data.get('action_code')
        deleted, _ = RolePermission.objects.filter(
            role__code=role_code,
            resource__code=resource_code,
            action__code=action_code,
        ).delete()
        if deleted == 0:
            raise NotFound('Такое правило доступа не найдено.')
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserRolesView(AccessControlledAPIView):
    resource_code = 'admin_rules'
    action_code = 'manage'

    def post(self, request):
        serializer = UserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_role, _ = UserRole.objects.get_or_create(
            user=serializer.validated_data['user'],
            role=serializer.validated_data['role'],
        )
        return Response(UserRoleSerializer(user_role).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        user_id = request.data.get('user_id')
        role_code = request.data.get('role_code')
        deleted, _ = UserRole.objects.filter(user_id=user_id, role__code=role_code).delete()
        if deleted == 0:
            raise NotFound('Такая роль у пользователя не найдена.')
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentsView(AccessControlledAPIView):
    resource_code = 'documents'
    action_code = 'read'
    method_action_map = {'get': 'read', 'post': 'create'}

    def get(self, request):
        return Response({
            'objects': [
                {'id': 1, 'title': 'Положение о проекте', 'status': 'published'},
                {'id': 2, 'title': 'Техническое задание', 'status': 'draft'},
            ]
        })

    def post(self, request):
        return Response({
            'detail': 'Документ создан в mock-режиме. Таблица бизнес-объектов не используется.',
            'payload': request.data,
        }, status=status.HTTP_201_CREATED)


class ReportsView(AccessControlledAPIView):
    resource_code = 'reports'
    action_code = 'read'

    def get(self, request):
        return Response({
            'objects': [
                {'id': 1, 'title': 'Финансовый отчет', 'period': '2026-Q2'},
                {'id': 2, 'title': 'Отчет по пользователям', 'period': '2026-06'},
            ]
        })


class AdminDashboardView(AccessControlledAPIView):
    resource_code = 'admin_dashboard'
    action_code = 'read'

    def get(self, request):
        return Response({
            'message': 'Это mock-ресурс административной панели.',
            'stats': {'users': Account.objects.count(), 'roles': Role.objects.count()},
        })
