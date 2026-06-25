# Generated manually for the educational custom auth project.
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=100)),
                ('first_name', models.CharField(max_length=100)),
                ('middle_name', models.CharField(blank=True, default='', max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'db_table': 'accounts', 'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=50, unique=True)),
                ('title', models.CharField(max_length=100)),
            ],
            options={'db_table': 'actions', 'ordering': ['code']},
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=80, unique=True)),
                ('title', models.CharField(max_length=150)),
                ('description', models.TextField(blank=True, default='')),
            ],
            options={'db_table': 'resources', 'ordering': ['code']},
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=50, unique=True)),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, default='')),
            ],
            options={'db_table': 'roles', 'ordering': ['code']},
        ),
        migrations.CreateModel(
            name='AuthSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jti', models.CharField(max_length=64, unique=True)),
                ('refresh_token_hash', models.CharField(max_length=128, unique=True)),
                ('user_agent', models.CharField(blank=True, default='', max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField()),
                ('logged_out_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='core.account')),
            ],
            options={'db_table': 'auth_sessions', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to='core.role')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to='core.account')),
            ],
            options={'db_table': 'user_roles', 'unique_together': {('user', 'role')}},
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_allowed', models.BooleanField(default=True)),
                ('action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to='core.action')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to='core.resource')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to='core.role')),
            ],
            options={'db_table': 'role_permissions', 'ordering': ['role__code', 'resource__code', 'action__code'], 'unique_together': {('role', 'resource', 'action')}},
        ),
    ]
