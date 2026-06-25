from django.urls import path

from core.views import (
    AdminActionsView,
    AdminAccessRulesView,
    AdminDashboardView,
    AdminPermissionsView,
    AdminResourcesView,
    AdminRolesView,
    AdminUserRolesView,
    DocumentsView,
    HealthView,
    LoginView,
    LogoutView,
    RefreshTokenView,
    MeView,
    RegisterView,
    ReportsView,
)

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),

    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('users/me/', MeView.as_view(), name='me'),

    path('admin/access/rules/', AdminAccessRulesView.as_view(), name='admin-access-rules'),
    path('admin/access/roles/', AdminRolesView.as_view(), name='admin-roles'),
    path('admin/access/resources/', AdminResourcesView.as_view(), name='admin-resources'),
    path('admin/access/actions/', AdminActionsView.as_view(), name='admin-actions'),
    path('admin/access/permissions/', AdminPermissionsView.as_view(), name='admin-permissions'),
    path('admin/access/user-roles/', AdminUserRolesView.as_view(), name='admin-user-roles'),

    path('business/documents/', DocumentsView.as_view(), name='documents'),
    path('business/reports/', ReportsView.as_view(), name='reports'),
    path('business/admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
]
