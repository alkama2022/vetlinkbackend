from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user_id', models.UUIDField(blank=True, null=True)),
                ('username', models.CharField(blank=True, default='', max_length=255)),
                ('role', models.CharField(blank=True, default='', max_length=64)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete')], max_length=10)),
                ('resource_type', models.CharField(max_length=255, db_index=True)),
                ('resource_id', models.CharField(blank=True, default='', max_length=255)),
                ('summary', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
