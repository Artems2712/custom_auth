# Backend-приложение: собственная система аутентификации и авторизации

Учебный проект реализует backend API на **Django REST Framework + PostgreSQL**.  
Главная идея: не использовать готовую систему `django.contrib.auth` как основу логина/прав, а показать собственную модель:

- собственная таблица пользователей `accounts`;
- собственная таблица JWT-сессий `auth_sessions`;
- собственные таблицы ролей, ресурсов, действий и разрешений;
- ручная проверка пользователя по `Authorization: Bearer <access_token>`;
- ручная проверка прав доступа по схеме `роль -> ресурс -> действие`.

---

## 1. Запуск проекта

### Вариант 1. Через Docker Compose

```bash
docker compose up --build
```

При запуске контейнер автоматически выполнит:

```bash
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver 0.0.0.0:8000
```

API будет доступно по адресу:

```text
http://localhost:8000/api/
```

### Вариант 2. Локально

1. Создать БД PostgreSQL:

```sql
CREATE DATABASE auth_project;
CREATE USER auth_user WITH PASSWORD 'auth_password';
GRANT ALL PRIVILEGES ON DATABASE auth_project TO auth_user;
```

2. Установить зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Создать `.env` из примера:

```bash
cp .env.example .env
```

4. Выполнить миграции и заполнить тестовые данные:

```bash
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

---

## 2. Тестовые пользователи

После команды `seed_demo_data` создаются пользователи:

| Email | Пароль | Роль | Что может делать |
|---|---|---|---|
| `admin@example.com` | `Admin123!` | `admin` | Управляет правилами доступа, видит все mock-ресурсы |
| `manager@example.com` | `Manager123!` | `manager` | Читает отчеты, читает/создает документы |
| `user@example.com` | `User123!` | `user` | Читает только документы и свой профиль |

---

## 3. Разница между аутентификацией и авторизацией

### Аутентификация

Аутентификация отвечает на вопрос: **кто делает запрос?**

В проекте это реализовано так:

1. Пользователь отправляет `email` и `password` на `/api/auth/login/`.
2. Backend ищет пользователя в таблице `accounts`.
3. Пароль сравнивается с сохраненным хешем.
4. Если пароль верный, создается запись в `auth_sessions`.
5. Пользователь получает `access_token` и `refresh_token`.
6. При следующих запросах клиент отправляет заголовок:

```http
Authorization: Bearer <access_token>
```

7. Backend проверяет JWT, ищет активную сессию и активного пользователя.

Если пользователя определить нельзя, API возвращает **401 Unauthorized**.

### Авторизация

Авторизация отвечает на вопрос: **что этому пользователю разрешено делать?**

Даже если пользователь успешно вошел в систему, ему доступны не все ресурсы. Доступ проверяется по таблицам:

```text
accounts -> user_roles -> roles -> role_permissions -> resources + actions
```

Если пользователь найден, но права на ресурс нет, API возвращает **403 Forbidden**.

---

## 4. Схема БД для собственной системы доступа

### `accounts`

Собственная таблица пользователей.

| Поле | Назначение |
|---|---|
| `id` | ID пользователя |
| `email` | Email для входа |
| `password_hash` | Хеш пароля |
| `last_name` | Фамилия |
| `first_name` | Имя |
| `middle_name` | Отчество |
| `is_active` | Можно ли пользователю входить |
| `is_deleted` | Был ли пользователь мягко удален |
| `deleted_at` | Дата мягкого удаления |

Удаление пользователя реализовано мягко: запись остается в БД, но `is_active=false`, `is_deleted=true`, все активные сессии завершаются.

### `auth_sessions`

Серверная таблица сессий для JWT.

| Поле | Назначение |
|---|---|
| `user_id` | К какому пользователю относится сессия |
| `jti` | Уникальный ID access-токена |
| `refresh_token_hash` | Хеш refresh-токена |
| `expires_at` | Срок жизни refresh-сессии |
| `logged_out_at` | Если заполнено, сессия завершена |

Зачем нужна эта таблица: обычный JWT сам по себе живет до истечения срока. Но задание требует `logout`. Поэтому при `logout` мы помечаем сессию завершенной, и даже ранее выданный JWT больше не принимается.

### `roles`

Роли пользователей.

Примеры:

- `admin`;
- `manager`;
- `user`.

### `user_roles`

Связь пользователей и ролей. Один пользователь может иметь несколько ролей.

Пример:

```text
admin@example.com -> admin
manager@example.com -> manager
user@example.com -> user
```

### `resources`

Ресурсы системы, к которым применяются права.

Примеры:

- `documents`;
- `reports`;
- `profile`;
- `admin_rules`;
- `admin_dashboard`.

### `actions`

Действия, которые можно совершать над ресурсами.

Примеры:

- `read`;
- `create`;
- `update`;
- `delete`;
- `manage`.

### `role_permissions`

Главная таблица правил доступа.

| Поле | Назначение |
|---|---|
| `role_id` | Роль |
| `resource_id` | Ресурс |
| `action_id` | Действие |
| `is_allowed` | Разрешено или нет |

Пример правила:

```text
role=manager, resource=reports, action=read, is_allowed=true
```

Это означает: пользователь с ролью `manager` может читать отчеты.

---

## 5. Реализованные endpoint'ы

### Auth и пользователь

| Метод | URL | Назначение |
|---|---|---|
| `POST` | `/api/auth/register/` | Регистрация пользователя |
| `POST` | `/api/auth/login/` | Login по email и паролю |
| `POST` | `/api/auth/logout/` | Logout, завершение текущей JWT-сессии |
| `POST` | `/api/auth/refresh/` | Получение нового access-токена по refresh-токену |
| `GET` | `/api/users/me/` | Получение своего профиля |
| `PATCH` | `/api/users/me/` | Обновление своего профиля |
| `DELETE` | `/api/users/me/` | Мягкое удаление аккаунта |

### Управление правилами доступа, только для администратора

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/api/admin/access/rules/` | Получить пользователей, роли, ресурсы, действия и правила |
| `POST` | `/api/admin/access/roles/` | Создать роль |
| `POST` | `/api/admin/access/resources/` | Создать ресурс |
| `POST` | `/api/admin/access/actions/` | Создать действие |
| `POST` | `/api/admin/access/permissions/` | Создать или изменить правило доступа |
| `DELETE` | `/api/admin/access/permissions/` | Удалить правило доступа |
| `POST` | `/api/admin/access/user-roles/` | Назначить роль пользователю |
| `DELETE` | `/api/admin/access/user-roles/` | Удалить роль у пользователя |

### Mock-объекты бизнес-приложения

Таблицы бизнес-объектов по заданию можно не создавать, поэтому здесь используются mock-view.

| Метод | URL | Требуемое право |
|---|---|---|
| `GET` | `/api/business/documents/` | `documents:read` |
| `POST` | `/api/business/documents/` | `documents:create` |
| `GET` | `/api/business/reports/` | `reports:read` |
| `GET` | `/api/business/admin-dashboard/` | `admin_dashboard:read` |

---

## 6. Примеры запросов

### Login администратора

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!"}'
```

Ответ содержит:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer"
}
```

Дальше access-токен нужно передавать так:

```bash
-H "Authorization: Bearer <access_token>"
```

### Получить свой профиль

```bash
curl http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer <access_token>"
```

### Проверка 401

Запрос без токена:

```bash
curl http://localhost:8000/api/business/documents/
```

Результат: **401 Unauthorized**.

### Проверка 403

Обычный пользователь `user@example.com` может читать документы, но не может читать отчеты.

```bash
curl http://localhost:8000/api/business/reports/ \
  -H "Authorization: Bearer <user_access_token>"
```

Результат: **403 Forbidden**.

### Получить правила доступа администратором

```bash
curl http://localhost:8000/api/admin/access/rules/ \
  -H "Authorization: Bearer <admin_access_token>"
```

### Выдать пользователю право через роль

Например, разрешить роли `user` читать отчеты:

```bash
curl -X POST http://localhost:8000/api/admin/access/permissions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_access_token>" \
  -d '{
    "role_code": "user",
    "resource_code": "reports",
    "action_code": "read",
    "is_allowed": true
  }'
```

После этого пользователь с ролью `user` сможет открыть `/api/business/reports/`.

### Logout

```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer <access_token>"
```

После logout этот access-токен больше не проходит проверку, потому что запись в `auth_sessions` помечается как завершенная.

### Мягкое удаление аккаунта

```bash
curl -X DELETE http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer <access_token>"
```

Результат:

- `accounts.is_active=false`;
- `accounts.is_deleted=true`;
- все активные сессии пользователя завершаются;
- повторный login невозможен;
- запись пользователя остается в БД.

---

## 7. Где в коде находится основная логика

| Файл | Назначение |
|---|---|
| `core/models.py` | Таблицы пользователей, сессий, ролей, ресурсов, действий и прав |
| `core/security.py` | Создание JWT, проверка JWT, проверка активной сессии, проверка доступа |
| `core/views.py` | API для регистрации, login, logout, профиля, прав и mock-ресурсов |
| `core/serializers.py` | Валидация входных данных |
| `core/management/commands/seed_demo_data.py` | Заполнение БД тестовыми данными |
| `core/migrations/0001_initial.py` | Миграция БД |

---

## 8. Почему это считается собственной системой доступа

В проекте не используется стандартная модель `User`, стандартные permissions и стандартный login/logout из Django. Вместо этого:

1. Пользователь хранится в собственной таблице `accounts`.
2. Сессии хранятся в собственной таблице `auth_sessions`.
3. JWT создается вручную через `PyJWT`.
4. При каждом защищенном запросе вручную проверяются:
   - наличие заголовка `Authorization`;
   - корректность JWT;
   - активность серверной сессии;
   - активность пользователя.
5. Авторизация выполняется через собственные таблицы:

```text
roles
resources
actions
role_permissions
user_roles
```

6. Ошибки разделены по смыслу:
   - **401** — пользователь не определен;
   - **403** — пользователь определен, но права нет.

---

## 9. Минимальный сценарий демонстрации

1. Запустить проект.
2. Войти как `user@example.com`.
3. Открыть `/api/business/documents/` — доступ есть.
4. Открыть `/api/business/reports/` — будет 403.
5. Войти как `admin@example.com`.
6. Через `/api/admin/access/permissions/` выдать роли `user` право `reports:read`.
7. Снова открыть `/api/business/reports/` токеном обычного пользователя — доступ появится.

Так демонстрируется работа собственной системы авторизации.
