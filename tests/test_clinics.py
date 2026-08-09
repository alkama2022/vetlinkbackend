from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.pharmacy.models import DrugStock
from apps.clinical_notes.models import CaseNote
from apps.laboratory.models import LabSample

User = get_user_model()


class ClinicFlowBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="clinic@test.com", password="testpass123",
            user_type="CLINIC_ADMIN", full_name="Clinic Admin",
        )
        self.client.force_authenticate(self.user)


class PatientTests(ClinicFlowBase):
    def test_create_patient_generates_code_and_patch_by_code(self):
        res = self.client.post(
            "/api/v1/patients/",
            {"ownerName": "Aliyu", "ownerPhone": "0803", "lga": "Kano",
             "species": "Poultry", "animalName": "Chicken A", "animalAge": "6 months"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        code = res.data["id"]
        self.assertTrue(code.startswith("P"))
        self.assertTrue(Patient.objects.filter(patient_code=code).exists())

        res = self.client.patch(f"/api/v1/patients/{code}/", {"animalName": "Chicken B"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["animalName"], "Chicken B")


class AppointmentTests(ClinicFlowBase):
    def test_create_appointment_generates_code_and_patch_by_code(self):
        res = self.client.post(
            "/api/v1/appointments/",
            {"date": "2026-08-10", "time": "10:00", "ownerName": "Aliyu",
             "animal": "Chicken", "reason": "Checkup", "status": "Scheduled"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        code = res.data["id"]
        self.assertTrue(code.startswith("A"))
        self.assertTrue(Appointment.objects.filter(appointment_code=code).exists())

        res = self.client.patch(f"/api/v1/appointments/{code}/", {"status": "Completed"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "Completed")


class DrugStockTests(ClinicFlowBase):
    def test_create_drug_generates_code_and_patch_by_code(self):
        res = self.client.post(
            "/api/v1/drugs/",
            {"name": "Oxytetracycline", "category": "Antibiotic", "quantity": 50,
             "unit": "bottle", "reorderLevel": 10, "expiryDate": "2027-01-01", "unitCost": "12.50"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        code = res.data["id"]
        self.assertTrue(code.startswith("D"))
        self.assertTrue(DrugStock.objects.filter(drug_code=code).exists())

        res = self.client.patch(f"/api/v1/drugs/{code}/", {"quantity": 30}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["quantity"], 30)


class CaseNoteTests(ClinicFlowBase):
    def test_create_case_note_generates_code_and_patch_by_code(self):
        res = self.client.post(
            "/api/v1/case-notes/",
            {"ownerName": "Aliyu", "animal": "Chicken", "date": "2026-08-09",
             "vetName": "Dr X", "diagnosis": "Newcastle", "treatment": "Supportive"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        code = res.data["id"]
        self.assertTrue(code.startswith("N"))
        self.assertTrue(CaseNote.objects.filter(note_code=code).exists())

        res = self.client.patch(f"/api/v1/case-notes/{code}/", {"diagnosis": "IBD"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["diagnosis"], "IBD")


class LabSampleTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="lab@test.com", password="testpass123",
            user_type="LAB_STAFF", full_name="Lab Staff",
        )
        self.client.force_authenticate(self.user)

    def test_create_sample_generates_code_and_publish_by_code(self):
        res = self.client.post(
            "/api/v1/lab-samples/",
            {"species": "Poultry", "test": "Serology", "facility": "Kano Lab",
             "status": "Received", "priority": "Routine", "dateReceived": "2026-08-09"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        code = res.data["id"]
        self.assertTrue(code.startswith("LAB"))
        self.assertTrue(LabSample.objects.filter(sample_code=code).exists())

        res = self.client.patch(f"/api/v1/lab-samples/{code}/", {"status": "In analysis"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.post(
            f"/api/v1/lab-samples/{code}/publish/",
            {"findings": "Negative for AI", "positive": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "Published")
        self.assertIsNotNone(res.data["publishedAt"])
