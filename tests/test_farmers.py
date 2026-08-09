from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.farmers.models import FarmerHerd, FarmerReminder
from apps.consultations.models import ConsultationRequest, ChatMessage
from apps.veterinarians.models import VeterinarianProfile

User = get_user_model()


class FarmerHerdTests(APITestCase):
    def setUp(self):
        self.farmer = User.objects.create_user(
            email="herdfarmer@test.com", password="testpass123",
            user_type="FARMER", full_name="Herds Farmer",
        )
        self.other = User.objects.create_user(
            email="otherfarmer@test.com", password="testpass123",
            user_type="FARMER", full_name="Other Farmer",
        )
        self.client.force_authenticate(self.farmer)

    def test_create_herd_generates_code_and_owner(self):
        res = self.client.post(
            "/api/v1/farmers/herds/",
            {"type": "Poultry", "count": "100 birds", "healthy": 95},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("herd_code", res.data)
        self.assertTrue(res.data["herd_code"].startswith("H"))
        herd = FarmerHerd.objects.get(herd_code=res.data["herd_code"])
        self.assertEqual(herd.farmer, self.farmer)

    def test_herds_are_scoped_to_owner(self):
        FarmerHerd.objects.create(
            herd_code="HOWN1", type="Cattle", count="5", farmer=self.farmer,
        )
        FarmerHerd.objects.create(
            herd_code="HOTH1", type="Goats", count="9", farmer=self.other,
        )
        res = self.client.get("/api/v1/farmers/herds/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        codes = [r["herd_code"] for r in res.data["results"]]
        self.assertIn("HOWN1", codes)
        self.assertNotIn("HOTH1", codes)

    def test_update_and_delete_by_code(self):
        herd = FarmerHerd.objects.create(
            herd_code="HUPD1", type="Poultry", count="20", farmer=self.farmer,
        )
        res = self.client.patch(f"/api/v1/farmers/herds/{herd.herd_code}/", {"healthy": 80}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["healthy"], 80)

        res = self.client.delete(f"/api/v1/farmers/herds/{herd.herd_code}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        herd.refresh_from_db()
        self.assertTrue(herd.is_deleted)

    def test_cannot_modify_other_farmers_herd(self):
        herd = FarmerHerd.objects.create(
            herd_code="HOTH2", type="Goats", count="9", farmer=self.other,
        )
        res = self.client.patch(f"/api/v1/farmers/herds/{herd.herd_code}/", {"healthy": 10}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class FarmerReminderTests(APITestCase):
    def setUp(self):
        self.farmer = User.objects.create_user(
            email="reminderfarmer@test.com", password="testpass123",
            user_type="FARMER", full_name="Reminder Farmer",
        )
        self.client.force_authenticate(self.farmer)

    def test_reminder_crud_by_code(self):
        res = self.client.post(
            "/api/v1/farmers/reminders/",
            {"title": "Vaccine", "date": "2026-08-10", "tone": "warning"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["reminder_code"].startswith("R"))

        res = self.client.patch(
            f"/api/v1/farmers/reminders/{res.data['reminder_code']}/",
            {"done": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["done"])

        res = self.client.delete(f"/api/v1/farmers/reminders/{res.data['reminder_code']}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class FarmerConsultationTests(APITestCase):
    def setUp(self):
        self.farmer = User.objects.create_user(
            email="consultfarmer@test.com", password="testpass123",
            user_type="FARMER", full_name="Consult Farmer",
        )
        self.other = User.objects.create_user(
            email="consultother@test.com", password="testpass123",
            user_type="FARMER", full_name="Other Farmer",
        )
        self.vet = VeterinarianProfile.objects.create(
            vet_code="VETTEST1", full_name="Dr Test", license_number="LN12345",
        )
        self.client.force_authenticate(self.farmer)

    def test_create_consultation_generates_code_and_owner(self):
        res = self.client.post(
            "/api/v1/consultations/",
            {
                "farmerName": "Consult Farmer",
                "farmLocation": "Kano, Kano State",
                "vetId": "VETTEST1",
                "vetName": "Dr Test",
                "channel": "in-app",
                "status": "Pending",
                "species": "Poultry",
                "animalAge": "6 months",
                "animalGender": "Mixed",
                "affectedCount": 5,
                "durationDays": 2,
                "severity": "Moderate",
                "symptomsEn": "Sneezing",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        consult = ConsultationRequest.objects.get(consultation_code=res.data["id"])
        self.assertEqual(consult.farmer, self.farmer)

    def test_consultations_are_scoped_to_owner(self):
        ConsultationRequest.objects.create(
            consultation_code="CONOWN1", farmer=self.farmer,
            farmer_name="Consult Farmer", farm_location="Kano",
            vet_name="Dr Test", species="Poultry", animal_age="1y",
        )
        ConsultationRequest.objects.create(
            consultation_code="CONOTH1", farmer=self.other,
            farmer_name="Other Farmer", farm_location="Kano",
            vet_name="Dr Test", species="Cattle", animal_age="2y",
        )
        res = self.client.get("/api/v1/consultations/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        codes = [r["id"] for r in res.data["results"]]
        self.assertIn("CONOWN1", codes)
        self.assertNotIn("CONOTH1", codes)

    def test_send_message_and_mark_read_by_code(self):
        consult = ConsultationRequest.objects.create(
            consultation_code="CONMSG1", farmer=self.farmer,
            farmer_name="Consult Farmer", farm_location="Kano",
            vet_name="Dr Test", species="Poultry", animal_age="1y",
        )
        res = self.client.post(
            f"/api/v1/consultations/{consult.consultation_code}/messages/",
            {"sender": "farmer", "senderName": "Consult Farmer", "text": "hello"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ChatMessage.objects.filter(consultation=consult).exists())

        res = self.client.post(f"/api/v1/consultations/{consult.consultation_code}/mark-read/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(consult.messages.filter(read=False).exists())

    def test_cannot_message_other_farmers_consultation(self):
        consult = ConsultationRequest.objects.create(
            consultation_code="CONOTH2", farmer=self.other,
            farmer_name="Other Farmer", farm_location="Kano",
            vet_name="Dr Test", species="Cattle", animal_age="2y",
        )
        res = self.client.post(
            f"/api/v1/consultations/{consult.consultation_code}/messages/",
            {"sender": "farmer", "senderName": "Consult Farmer", "text": "hello"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
