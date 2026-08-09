from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.reverse import reverse

from apps.community.models import CommunityPost, CommunityCategory, CommunityBookmark

User = get_user_model()


class CommunityBookmarkTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="farmer@test.com", password="testpass123", user_type="FARMER", full_name="Test Farmer"
        )
        self.other = User.objects.create_user(
            email="other@test.com", password="testpass123", user_type="VETERINARIAN", full_name="Other Vet"
        )
        self.category = CommunityCategory.objects.create(name="General", slug="general")
        self.post = CommunityPost.objects.create(
            title="Post one", content="Content", author=self.user,
            author_name="Test Farmer", author_role="FARMER", category=self.category,
        )
        self.post2 = CommunityPost.objects.create(
            title="Post two", content="Content", author=self.other,
            author_name="Other Vet", author_role="VETERINARIAN",
        )
        self.list_url = reverse("community-bookmark-list")
        self.client.force_authenticate(self.user)

    def test_list_requires_auth(self):
        self.client.force_authenticate(None)
        res = self.client.get(self.list_url)
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_bookmarks_post(self):
        res = self.client.post(self.list_url, {"post": str(self.post.id)}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CommunityBookmark.objects.filter(user=self.user, post=self.post).exists())

    def test_second_create_toggles_off(self):
        CommunityBookmark.objects.create(user=self.user, post=self.post)
        res = self.client.post(self.list_url, {"post": str(self.post.id)}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["bookmarked"], False)
        self.assertFalse(CommunityBookmark.objects.filter(user=self.user, post=self.post).exists())

    def test_create_unknown_post_404(self):
        res = self.client.post(self.list_url, {"post": "00000000-0000-0000-0000-000000000000"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_missing_post_400(self):
        res = self.client.post(self.list_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_returns_own_bookmarks_only(self):
        CommunityBookmark.objects.create(user=self.user, post=self.post)
        CommunityBookmark.objects.create(user=self.other, post=self.post2)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(str(res.data["results"][0]["post"]), str(self.post.id))

    def test_destroy_removes_bookmark(self):
        bookmark = CommunityBookmark.objects.create(user=self.user, post=self.post)
        url = reverse("community-bookmark-detail", args=[str(bookmark.id)])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CommunityBookmark.objects.filter(id=bookmark.id).exists())

    def test_cannot_bookmark_others(self):
        bookmark = CommunityBookmark.objects.create(user=self.other, post=self.post2)
        url = reverse("community-bookmark-detail", args=[str(bookmark.id)])
        self.client.force_authenticate(self.user)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
