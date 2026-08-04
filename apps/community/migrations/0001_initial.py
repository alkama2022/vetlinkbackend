from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityCategory',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('name', models.CharField(max_length=120, unique=True)),
                ('slug', models.SlugField(max_length=140, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='CommunityTag',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('name', models.CharField(max_length=80, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='CommunityPost',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('deleted_at', models.DateTimeField(null=True, blank=True)),
                ('title', models.CharField(max_length=300)),
                ('content', models.TextField()),
                ('author_name', models.CharField(max_length=255)),
                ('author_role', models.CharField(max_length=64, blank=True, default='')),
                ('author_avatar', models.URLField(blank=True, default='')),
                ('species', models.CharField(max_length=120, blank=True, default='')),
                ('disease_category', models.CharField(max_length=120, blank=True, default='')),
                ('location', models.CharField(max_length=255, blank=True, default='')),
                ('visibility', models.CharField(default='public', max_length=20, db_index=True, choices=[('public', 'Public'), ('private', 'Private'), ('hidden', 'Hidden')])),
                ('is_edited', models.BooleanField(default=False, db_index=True)),
                ('author', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='community_posts', to='accounts.user')),
                ('category', models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, related_name='posts', blank=True, to='community.communitycategory')),
            ],
        ),
        migrations.CreateModel(
            name='CommunityComment',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('deleted_at', models.DateTimeField(null=True, blank=True)),
                ('content', models.TextField()),
                ('is_deleted', models.BooleanField(default=False)),
                ('author', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='community_comments', to='accounts.user')),
                ('post', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='comments', to='community.communitypost')),
                ('parent', models.ForeignKey(null=True, blank=True, on_delete=models.deletion.CASCADE, related_name='replies', to='community.communitycomment')),
            ],
        ),
        migrations.CreateModel(
            name='CommunityReaction',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('reaction', models.CharField(max_length=20, choices=[('like', 'Like'), ('helpful', 'Helpful'), ('thanks', 'Thanks'), ('insightful', 'Insightful')])),
                ('post', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='reactions', to='community.communitypost')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='community_reactions', to='accounts.user')),
            ],
            options={'unique_together': {('post', 'user', 'reaction')}},
        ),
        migrations.CreateModel(
            name='CommunityBookmark',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='community_bookmarks', to='accounts.user')),
                ('post', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='bookmarks', to='community.communitypost')),
            ],
            options={'unique_together': {('user', 'post')}},
        ),
        migrations.CreateModel(
            name='CommunityReport',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('reason', models.TextField()),
                ('status', models.CharField(default='open', max_length=20, choices=[('open', 'Open'), ('reviewed', 'Reviewed'), ('dismissed', 'Dismissed')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='reports', to='community.communitypost')),
                ('reporter', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='community_reports', to='accounts.user')),
                ('reviewed_by', models.ForeignKey(null=True, blank=True, on_delete=models.deletion.SET_NULL, related_name='community_reports_reviewed', to='accounts.user')),
            ],
        ),
        migrations.AddField(
            model_name='communitypost',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='posts', to='community.communitytag'),
        ),
    ]
