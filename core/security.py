import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

from core.models import Account, AuthSession, RolePermission


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    session: AuthSession


def _utc_timestamp(dt):
    return int(dt.timestamp())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def verify_password(raw_password: str, password_hash: str) -> bool:
    return check_password(raw_password, password_hash)


def get_client_ip(request) -> Optional[str]:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def create_token_pair(user: Account, request=None) -> TokenPair:
    now = timezone.now()
    access_expires_at = now + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)
    refresh_expires_at = now + timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    jti = uuid.uuid4().hex
    refresh_token = secrets.token_urlsafe(48)

    session = AuthSession.objects.create(
        user=user,
        jti=jti,
        refresh_token_hash=hash_token(refresh_token),
        user_agent=(request.META.get('HTTP_USER_AGENT', '')[:255] if request else ''),
        ip_address=get_client_ip(request) if request else None,
        expires_at=refresh_expires_at,
    )

    payload = {
        'type': 'access',
        'sub': str(user.id),
        'email': user.email,
        'jti': jti,
        'iat': _utc_timestamp(now),
        'exp': _utc_timestamp(access_expires_at),
    }
    access_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    return TokenPair(access_token=access_token, refresh_token=refresh_token, session=session)


def read_access_token_from_header(request) -> str:
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        raise NotAuthenticated('Не передан заголовок Authorization: Bearer <token>.')
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise AuthenticationFailed('Неверный формат Authorization. Используйте Bearer <token>.')
    return parts[1]



def create_access_token_for_session(user: Account, session: AuthSession) -> str:
    now = timezone.now()
    access_expires_at = now + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)
    payload = {
        'type': 'access',
        'sub': str(user.id),
        'email': user.email,
        'jti': session.jti,
        'iat': _utc_timestamp(now),
        'exp': _utc_timestamp(access_expires_at),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def refresh_access_token(refresh_token: str) -> tuple[str, Account]:
    session = AuthSession.objects.select_related('user').filter(refresh_token_hash=hash_token(refresh_token)).first()
    if session is None or not session.is_active:
        raise AuthenticationFailed('Refresh-токен недействителен или сессия завершена.')

    user = session.user
    if not user.is_active or user.is_deleted:
        raise AuthenticationFailed('Пользователь удален или заблокирован.')

    return create_access_token_for_session(user, session), user

def get_authenticated_user(request) -> Account:
    token = read_access_token_from_header(request)
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationFailed('Access-токен истек.') from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationFailed('Access-токен некорректен.') from exc

    if payload.get('type') != 'access':
        raise AuthenticationFailed('Передан токен неверного типа.')

    user_id = payload.get('sub')
    jti = payload.get('jti')
    if not user_id or not jti:
        raise AuthenticationFailed('В токене отсутствуют обязательные поля.')

    try:
        user = Account.objects.get(id=user_id, is_active=True, is_deleted=False)
    except Account.DoesNotExist as exc:
        raise AuthenticationFailed('Пользователь не найден или заблокирован.') from exc

    session = AuthSession.objects.filter(user=user, jti=jti).first()
    if session is None or not session.is_active:
        raise AuthenticationFailed('Сессия завершена или недействительна.')

    request.auth_session = session
    request.current_user = user
    return user


def has_access(user: Account, resource_code: str, action_code: str) -> bool:
    if not user.is_active or user.is_deleted:
        return False

    return RolePermission.objects.filter(
        role__user_roles__user=user,
        resource__code=resource_code,
        action__code=action_code,
        is_allowed=True,
    ).exists()
