import io
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.reverse import reverse

from apps.surveillance.models import DiseaseReport

User = get_user_model()


class DiseaseReportPhotoTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reporter@test.com", password="testpass123",
            user_type="FARMER", full_name="Test Reporter",
        )
        self.url = reverse("disease-report-list")
        self.client.force_authenticate(self.user)
        self.payload = {
            "species": "Poultry (Chicken)",
            "disease": "Avian Influenza (Bird Flu)",
            "affected": 25,
            "dead": 10,
            "signs": '["Fever", "Sudden death"]',
            "date": "2026-08-01",
            "location": "Dawakin Kudu, Kano State",
        }

    def _photo(self, name="evidence.jpg", content=b"fake-jpeg-bytes", content_type="image/jpeg"):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_create_without_photos(self):
        res = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        report = DiseaseReport.objects.get(report_code=res.data["id"])
        self.assertEqual(report.photos, [])

    def test_create_with_photo(self):
        res = self.client.post(
            self.url,
            {**self.payload, "photos": [self._photo()]},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        report = DiseaseReport.objects.get(report_code=res.data["id"])
        self.assertEqual(len(report.photos), 1)
        self.assertIn("uploads/disease_reports/", report.photos[0])
        self.assertIn("http", res.data["photos"][0])
        self.assertIn(report.photos[0], res.data["photos"][0])

    def test_create_with_multiple_photos(self):
        res = self.client.post(
            self.url,
            {**self.payload, "photos": [self._photo(), self._photo("clip.mp4", b"video", "video/mp4")]},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        report = DiseaseReport.objects.get(report_code=res.data["id"])
        self.assertEqual(len(report.photos), 2)

    def test_rejects_non_media_type(self):
        res = self.client.post(
            self.url,
            {**self.payload, "photos": [self._photo("notes.txt", b"text", "text/plain")]},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_oversized_upload(self):
        big = self._photo("huge.jpg", b"x" * (8 * 1024 * 1024 + 1))
        res = self.client.post(
            self.url,
            {**self.payload, "photos": [big]},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieval_returns_absolute_photo_urls(self):
        res = self.client.post(
            self.url,
            {**self.payload, "photos": [self._photo()]},
            format="multipart",
        )
        detail = self.client.get(f"{self.url}{res.data['id']}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertTrue(detail.data["photos"][0].startswith("http"))

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        res = self.client.post(self.url, self.payload, format="json")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
