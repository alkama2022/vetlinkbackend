"""
Management command to seed the database with realistic demo data.

Usage:
    python manage.py seed_data          # Create all seed data (idempotent)
    python manage.py seed_data --clear  # Clear all data first, then seed
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import uuid


class Command(BaseCommand):
    help = "Seed the database with realistic demo data for VetLink Kano"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true', help='Clear all existing data before seeding'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self._clear_data()

        self._create_users()
        self._create_patients()
        self._create_appointments()
        self._create_case_notes()
        self._create_drugs()
        self._create_lab_samples()
        self._create_disease_reports()
        self._create_invoices()
        self._create_notifications()
        self._create_herds()
        self._create_reminders()
        self._create_consultations()

        self.stdout.write(self.style.SUCCESS("[OK] Seed data created successfully!"))
        self.stdout.write(self.style.SUCCESS("\n--- Test Accounts ---"))
        self.stdout.write(self.style.SUCCESS("  Farmer:       farmer@vetlink.com / password123"))
        self.stdout.write(self.style.SUCCESS("  Veterinarian: vet@vetlink.com / password123"))
        self.stdout.write(self.style.SUCCESS("  Gov Officer:  gov@vetlink.com / password123"))
        self.stdout.write(self.style.SUCCESS("  Admin:        admin@vetlink.com / password123"))

    def _clear_data(self):
        from apps.accounts.models import User
        from apps.patients.models import Patient
        from apps.appointments.models import Appointment
        from apps.clinical_notes.models import CaseNote
        from apps.pharmacy.models import DrugStock
        from apps.laboratory.models import LabSample
        from apps.surveillance.models import DiseaseReport
        from apps.billing.models import Invoice, InvoiceItem
        from apps.notifications.models import Notification
        from apps.farmers.models import FarmerHerd, FarmerReminder
        from apps.consultations.models import ConsultationRequest, ChatMessage
        from apps.veterinarians.models import VeterinarianProfile

        self.stdout.write("Clearing existing data...")
        ChatMessage.objects.all().delete()
        ConsultationRequest.objects.all().delete()
        FarmerReminder.objects.all().delete()
        FarmerHerd.objects.all().delete()
        Notification.objects.all().delete()
        InvoiceItem.objects.all().delete()
        Invoice.objects.all().delete()
        DiseaseReport.objects.all().delete()
        LabSample.objects.all().delete()
        DrugStock.objects.all().delete()
        CaseNote.objects.all().delete()
        Appointment.objects.all().delete()
        Patient.objects.all().delete()
        VeterinarianProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING("  [!] All data cleared."))

    def _create_users(self):
        from apps.accounts.models import User

        users_data = [
            {
                'email': 'farmer@vetlink.com',
                'full_name': 'Abubakar Ibrahim',
                'password': 'password123',
                'user_type': 'FARMER',
                'phone_number': '+2348031234567',
                'lga': 'Dawakin Kudu',
                'is_email_verified': True,
            },
            {
                'email': 'vet@vetlink.com',
                'full_name': 'Dr. Abdullahi Sani',
                'password': 'password123',
                'user_type': 'VETERINARIAN',
                'phone_number': '+2348069876543',
                'lga': 'Kano Municipal',
                'is_email_verified': True,
            },
            {
                'email': 'gov@vetlink.com',
                'full_name': 'Fatima Bello',
                'password': 'password123',
                'user_type': 'GOVERNMENT_OFFICER',
                'phone_number': '+2348091112222',
                'lga': 'Kano Municipal',
                'is_email_verified': True,
            },
            {
                'email': 'admin@vetlink.com',
                'full_name': 'System Administrator',
                'password': 'password123',
                'user_type': 'SUPER_ADMIN',
                'phone_number': '+2348000000000',
                'lga': 'Kano Municipal',
                'is_email_verified': True,
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'pharmacist@vetlink.com',
                'full_name': 'Hauwa Musa',
                'password': 'password123',
                'user_type': 'PHARMACIST',
                'phone_number': '+2348045556666',
                'lga': 'Kano Municipal',
                'is_email_verified': True,
            },
            {
                'email': 'lab@vetlink.com',
                'full_name': 'Ibrahim Yusuf',
                'password': 'password123',
                'user_type': 'LAB_STAFF',
                'phone_number': '+2348077778888',
                'lga': 'Kano Municipal',
                'is_email_verified': True,
            },
            {
                'email': 'amina@vetlink.com',
                'full_name': 'Dr. Amina Yusuf',
                'password': 'password123',
                'user_type': 'VETERINARIAN',
                'phone_number': '+2348055554444',
                'lga': 'Kano Municipal',
                'is_email_verified': True,
            },
        ]

        created_users = {}
        for data in users_data:
            email = data['email']
            password = data.pop('password')
            is_staff = data.pop('is_staff', False)
            is_superuser = data.pop('is_superuser', False)
            is_email_verified = data.pop('is_email_verified', False)

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    **data,
                    'is_staff': is_staff,
                    'is_superuser': is_superuser,
                    'is_email_verified': is_email_verified,
                }
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"  [+] Created user: {email} ({data['user_type']})")
            else:
                self.stdout.write(f"  [=] User already exists: {email}")
            created_users[email] = user

        # Create veterinarian profile
        vet_user = created_users.get('vet@vetlink.com')
        if vet_user:
            from apps.veterinarians.models import VeterinarianProfile
            profile, created = VeterinarianProfile.objects.get_or_create(
                vet_code='VET001',
                defaults={
                    'user': vet_user,
                    'full_name': 'Dr. Abdullahi Sani',
                    'license_number': 'VCN/2015/4521',
                    'qualifications': 'DVM, MSc Poultry Health',
                    'specializations': ['Poultry / Avian', 'Large Animals (Cattle / Camel)', 'Mixed Practice'],
                    'species_treated': ['Poultry (Chicken)', 'Poultry (Turkey)', 'Cattle', 'Goat / Sheep'],
                    'diseases_expertise': ['Avian Influenza', 'Newcastle Disease', 'CBPP', 'Anthrax'],
                    'years_experience': 12,
                    'languages': ['English', 'Hausa'],
                    'clinic_name': 'Kano Veterinary Clinic',
                    'clinic_address': '123 Hospital Road, Kano Municipal',
                    'lga': 'Kano Municipal',
                    'service_area': ['Kano Municipal', 'Dawakin Kudu', 'Gwarzo', 'Rano'],
                    'whatsapp_number': '+2348069876543',
                    'phone': '+2348069876543',
                    'email': 'vet@vetlink.com',
                    'available': True,
                    'available_online': True,
                    'available_emergency': True,
                    'consultation_fee': 5000.00,
                    'rating': 4.80,
                    'total_consultations': 156,
                    'bio': 'Experienced veterinarian specializing in poultry and large animal health. 12+ years serving Kano State farming communities.',
                    'avatar_initials': 'AS',
                }
            )
            if created:
                self.stdout.write("  [+] Created vet profile: VET001")

        # Create a second vet profile (or fix orphan)
        vet2_user = created_users.get('amina@vetlink.com')
        if vet_user:
            profile2, created = VeterinarianProfile.objects.get_or_create(
                vet_code='VET002',
                defaults={
                    'user': vet2_user,
                    'full_name': 'Dr. Amina Yusuf',
                    'license_number': 'VCN/2018/7823',
                    'qualifications': 'DVM, Cert Veterinary Public Health',
                    'specializations': ['Companion Animals (Dog / Cat)', 'Public Health / Epidemiology'],
                    'species_treated': ['Dog / Cat', 'Goat / Sheep'],
                    'diseases_expertise': ['Rabies', 'Foot and Mouth Disease'],
                    'years_experience': 7,
                    'languages': ['English', 'Hausa'],
                    'clinic_name': 'Amina Animal Hospital',
                    'clinic_address': '45 Sabo Road, Kano Municipal',
                    'lga': 'Kano Municipal',
                    'service_area': ['Kano Municipal', 'Bebeji'],
                    'whatsapp_number': '+2348055554444',
                    'phone': '+2348055554444',
                    'email': 'amina@vetlink.com',
                    'available': True,
                    'available_online': True,
                    'available_emergency': False,
                    'consultation_fee': 3500.00,
                    'rating': 4.60,
                    'total_consultations': 89,
                    'bio': 'Veterinary public health specialist with focus on companion animals and disease surveillance.',
                    'avatar_initials': 'AY',
                }
            )
            if created:
                self.stdout.write("  [+] Created vet profile: VET002")
            elif profile2.user is None and vet2_user:
                profile2.user = vet2_user
                profile2.save(update_fields=['user'])
                self.stdout.write("  [~] Fixed orphan vet profile VET002 -> linked to amina@vetlink.com")

        self._users = created_users

    def _create_patients(self):
        from apps.patients.models import Patient

        vet_user = self._users.get('vet@vetlink.com')
        if not vet_user:
            return

        patients_data = [
            {
                'patient_code': f'P{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Aliyu Poultry Farm',
                'owner_phone': '+2348031111111',
                'lga': 'Dawakin Kudu',
                'species': 'Poultry (Chicken)',
                'animal_name': 'Flock A - Broilers',
                'animal_age': '6 weeks',
                'created_by': vet_user,
            },
            {
                'patient_code': f'P{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Hauwa Musa',
                'owner_phone': '+2348032222222',
                'lga': 'Gwarzo',
                'species': 'Goat / Sheep',
                'animal_name': 'Nanny - Sokoto Red',
                'animal_age': '3 years',
                'created_by': vet_user,
            },
            {
                'patient_code': f'P{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Sani Bello',
                'owner_phone': '+2348033333333',
                'lga': 'Kano Municipal',
                'species': 'Dog / Cat',
                'animal_name': 'Rex - German Shepherd',
                'animal_age': '2 years',
                'created_by': vet_user,
            },
            {
                'patient_code': f'P{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Dawakin Kudu Coop',
                'owner_phone': '+2348034444444',
                'lga': 'Dawakin Kudu',
                'species': 'Cattle',
                'animal_name': 'Herd B - Sokoto Gudali',
                'animal_age': '4 years',
                'created_by': vet_user,
            },
            {
                'patient_code': f'P{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Fatima Abubakar',
                'owner_phone': '+2348035555555',
                'lga': 'Bebeji',
                'species': 'Poultry (Turkey)',
                'animal_name': 'Turkey Flock',
                'animal_age': '10 weeks',
                'created_by': vet_user,
            },
        ]

        for data in patients_data:
            Patient.objects.get_or_create(
                patient_code=data['patient_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(patients_data)} patients")

    def _create_appointments(self):
        from apps.appointments.models import Appointment

        today = timezone.now().strftime('%Y-%m-%d')
        yesterday = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        appointments_data = [
            {
                'appointment_code': f'A{uuid.uuid4().hex[:6].upper()}',
                'time': '09:00',
                'date': today,
                'owner_name': 'Aliyu Poultry Farm',
                'animal': 'Poultry · 250 birds',
                'reason': 'Flock health check',
                'status': 'Completed',
            },
            {
                'appointment_code': f'A{uuid.uuid4().hex[:6].upper()}',
                'time': '10:30',
                'date': today,
                'owner_name': 'Hauwa Musa',
                'animal': 'Goat · Nanny',
                'reason': 'Deworming',
                'status': 'Scheduled',
            },
            {
                'appointment_code': f'A{uuid.uuid4().hex[:6].upper()}',
                'time': '12:00',
                'date': today,
                'owner_name': 'Dawakin Kudu Coop',
                'animal': 'Cattle · 8 heads',
                'reason': 'Vaccination (CBPP)',
                'status': 'Scheduled',
            },
            {
                'appointment_code': f'A{uuid.uuid4().hex[:6].upper()}',
                'time': '14:15',
                'date': today,
                'owner_name': 'Sani Bello',
                'animal': 'Dog · Rex',
                'reason': 'Anti-rabies booster',
                'status': 'Scheduled',
            },
            {
                'appointment_code': f'A{uuid.uuid4().hex[:6].upper()}',
                'time': '09:30',
                'date': yesterday,
                'owner_name': 'Fatima Abubakar',
                'animal': 'Turkey · Turkey Flock',
                'reason': 'Newcastle vaccination',
                'status': 'Completed',
            },
            {
                'appointment_code': f'A{uuid.uuid4().hex[:6].upper()}',
                'time': '11:00',
                'date': tomorrow,
                'owner_name': 'Aliyu Poultry Farm',
                'animal': 'Poultry · 250 birds',
                'reason': 'Follow-up treatment',
                'status': 'Scheduled',
            },
        ]

        for data in appointments_data:
            Appointment.objects.get_or_create(
                appointment_code=data['appointment_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(appointments_data)} appointments")

    def _create_case_notes(self):
        from apps.clinical_notes.models import CaseNote

        today = timezone.now().strftime('%Y-%m-%d')
        next_week = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')

        notes_data = [
            {
                'note_code': f'CN{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Aliyu Poultry Farm',
                'animal': 'Flock A - Broilers',
                'date': today,
                'vet_name': 'Dr. Abdullahi Sani',
                'diagnosis': 'Newcastle Disease - suspected based on respiratory symptoms and sudden deaths',
                'treatment': 'Vaccination with La Sota strain. Administered antibiotics for secondary infections.',
                'follow_up_date': next_week,
                'notes': 'Farmer advised to isolate sick birds. Biosecurity measures discussed.',
            },
            {
                'note_code': f'CN{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Sani Bello',
                'animal': 'Rex - German Shepherd',
                'date': today,
                'vet_name': 'Dr. Abdullahi Sani',
                'diagnosis': 'Routine anti-rabies booster - no clinical signs',
                'treatment': 'Rabies booster vaccine administered. Dog in good health.',
                'follow_up_date': '',
                'notes': 'Next booster due in 1 year. Owner educated on dog health management.',
            },
            {
                'note_code': f'CN{uuid.uuid4().hex[:6].upper()}',
                'owner_name': 'Hauwa Musa',
                'animal': 'Nanny - Sokoto Red',
                'date': (timezone.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'vet_name': 'Dr. Abdullahi Sani',
                'diagnosis': 'Gastrointestinal parasitism - high worm burden detected',
                'treatment': 'Albendazole 400mg oral. Repeat in 2 weeks.',
                'follow_up_date': next_week,
                'notes': 'Goat appears weak. Recommend improved nutrition and clean water.',
            },
        ]

        for data in notes_data:
            CaseNote.objects.get_or_create(
                note_code=data['note_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(notes_data)} case notes")

    def _create_drugs(self):
        from apps.pharmacy.models import DrugStock

        drugs_data = [
            {
                'drug_code': f'D{uuid.uuid4().hex[:6].upper()}',
                'name': 'Ivermectin',
                'category': 'Antiparasitic',
                'quantity': 6,
                'unit': 'vials',
                'reorder_level': 10,
                'expiry_date': '2027-06-30',
                'unit_cost': 850.00,
            },
            {
                'drug_code': f'D{uuid.uuid4().hex[:6].upper()}',
                'name': 'Oxytetracycline',
                'category': 'Antibiotic',
                'quantity': 45,
                'unit': 'bottles',
                'reorder_level': 15,
                'expiry_date': '2027-03-15',
                'unit_cost': 1200.00,
            },
            {
                'drug_code': f'D{uuid.uuid4().hex[:6].upper()}',
                'name': 'Newcastle Disease Vaccine (La Sota)',
                'category': 'Vaccine',
                'quantity': 120,
                'unit': 'doses',
                'reorder_level': 50,
                'expiry_date': '2026-12-31',
                'unit_cost': 200.00,
            },
            {
                'drug_code': f'D{uuid.uuid4().hex[:6].upper()}',
                'name': 'Albendazole',
                'category': 'Antiparasitic',
                'quantity': 30,
                'unit': 'tablets',
                'reorder_level': 20,
                'expiry_date': '2027-09-30',
                'unit_cost': 350.00,
            },
            {
                'drug_code': f'D{uuid.uuid4().hex[:6].upper()}',
                'name': 'Rabies Vaccine',
                'category': 'Vaccine',
                'quantity': 8,
                'unit': 'vials',
                'reorder_level': 10,
                'expiry_date': '2027-01-15',
                'unit_cost': 3500.00,
            },
            {
                'drug_code': f'D{uuid.uuid4().hex[:6].upper()}',
                'name': 'Amoxicillin',
                'category': 'Antibiotic',
                'quantity': 50,
                'unit': 'capsules',
                'reorder_level': 25,
                'expiry_date': '2027-08-20',
                'unit_cost': 150.00,
            },
            {
                'drug_code': f'D{uuid.uuid4().hex[:6].upper()}',
                'name': 'CBPP Vaccine',
                'category': 'Vaccine',
                'quantity': 40,
                'unit': 'doses',
                'reorder_level': 20,
                'expiry_date': '2026-11-30',
                'unit_cost': 1500.00,
            },
        ]

        for data in drugs_data:
            DrugStock.objects.get_or_create(
                drug_code=data['drug_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(drugs_data)} drugs")

    def _create_lab_samples(self):
        from apps.laboratory.models import LabSample

        today = timezone.now().strftime('%Y-%m-%d')
        yesterday = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        samples_data = [
            {
                'sample_code': f'LAB-{uuid.uuid4().hex[:6].upper()}',
                'species': 'Poultry',
                'test': 'AI PCR panel',
                'facility': 'Kano Vet Clinic',
                'status': 'Result ready',
                'priority': 'Urgent',
                'date_received': yesterday,
                'requested_by': 'Dr. Abdullahi Sani',
                'result_findings': 'H5N1 Avian Influenza detected. High viral load confirmed.',
                'result_positive': True,
            },
            {
                'sample_code': f'LAB-{uuid.uuid4().hex[:6].upper()}',
                'species': 'Cattle',
                'test': 'Brucella ELISA',
                'facility': 'Dawakin Kudu VC',
                'status': 'In analysis',
                'priority': 'Routine',
                'date_received': today,
                'requested_by': 'Dr. Abdullahi Sani',
            },
            {
                'sample_code': f'LAB-{uuid.uuid4().hex[:6].upper()}',
                'species': 'Goat',
                'test': 'PPR antigen',
                'facility': 'Bebeji Outpost',
                'status': 'Received',
                'priority': 'Urgent',
                'date_received': today,
                'requested_by': 'Dr. Abdullahi Sani',
            },
            {
                'sample_code': f'LAB-{uuid.uuid4().hex[:6].upper()}',
                'species': 'Dog',
                'test': 'Rabies FAT',
                'facility': 'Kano Municipal',
                'status': 'In analysis',
                'priority': 'Urgent',
                'date_received': today,
                'requested_by': 'Dr. Abdullahi Sani',
            },
            {
                'sample_code': f'LAB-{uuid.uuid4().hex[:6].upper()}',
                'species': 'Poultry',
                'test': 'Newcastle HI',
                'facility': 'Rano Coop',
                'status': 'Result ready',
                'priority': 'Routine',
                'date_received': (timezone.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'requested_by': 'Dr. Abdullahi Sani',
                'result_findings': 'Newcastle Disease antibody titre 1:64 - adequate immunity post-vaccination.',
                'result_positive': False,
            },
        ]

        for data in samples_data:
            LabSample.objects.get_or_create(
                sample_code=data['sample_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(samples_data)} lab samples")

    def _create_disease_reports(self):
        from apps.surveillance.models import DiseaseReport

        today = timezone.now().strftime('%Y-%m-%d')
        yesterday = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        farmer_user = self._users.get('farmer@vetlink.com')

        reports_data = [
            {
                'report_code': f'VK{uuid.uuid4().hex[:6].upper()}',
                'species': 'Poultry (Chicken)',
                'disease': 'Avian Influenza (Bird Flu)',
                'affected': 45,
                'dead': 12,
                'signs': ['Sudden death', 'Respiratory distress', 'Swollen head'],
                'date': yesterday,
                'location': 'Dawakin Kudu, Kano State',
                'lga': 'Dawakin Kudu',
                'coords': '11.8500, 8.6167',
                'notes': 'Sudden onset of deaths in poultry flock. Multiple birds found dead this morning.',
                'farmer': farmer_user,
                'farmer_name': 'Abubakar Ibrahim',
                'alert_status': 'Suspected',
            },
            {
                'report_code': f'VK{uuid.uuid4().hex[:6].upper()}',
                'species': 'Cattle',
                'disease': 'Anthrax',
                'affected': 3,
                'dead': 1,
                'signs': ['Sudden death', 'Nasal discharge'],
                'date': today,
                'location': 'Bebeji, Kano State',
                'lga': 'Bebeji',
                'coords': '11.7333, 8.4667',
                'notes': 'One cow found dead with bloody natural orifices. Under investigation.',
                'farmer': farmer_user,
                'farmer_name': 'Abubakar Ibrahim',
                'alert_status': 'Under investigation',
            },
            {
                'report_code': f'VK{uuid.uuid4().hex[:6].upper()}',
                'species': 'Goat / Sheep',
                'disease': 'PPR (Peste des Petits Ruminants)',
                'affected': 8,
                'dead': 0,
                'signs': ['Diarrhoea', 'Nasal discharge', 'Loss of appetite'],
                'date': today,
                'location': 'Gwarzo, Kano State',
                'lga': 'Gwarzo',
                'coords': '12.1833, 7.9333',
                'notes': 'Multiple goats showing PPR-like symptoms. Vaccination campaign needed.',
                'farmer': farmer_user,
                'farmer_name': 'Abubakar Ibrahim',
                'alert_status': 'Suspected',
            },
            {
                'report_code': f'VK{uuid.uuid4().hex[:6].upper()}',
                'species': 'Dog / Cat',
                'disease': 'Rabies',
                'affected': 1,
                'dead': 0,
                'signs': ['Aggression', 'Excessive salivation'],
                'date': (timezone.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'location': 'Kano Municipal, Kano State',
                'lga': 'Kano Municipal',
                'coords': '12.0000, 8.5167',
                'notes': 'Dog showing aggressive behavior. Quarantine in place.',
                'farmer': farmer_user,
                'farmer_name': 'Sani Bello',
                'alert_status': 'Confirmed',
            },
            {
                'report_code': f'VK{uuid.uuid4().hex[:6].upper()}',
                'species': 'Poultry (Chicken)',
                'disease': 'Newcastle Disease',
                'affected': 120,
                'dead': 28,
                'signs': ['Respiratory distress', 'Diarrhoea', 'Nervous signs'],
                'date': (timezone.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'location': 'Rano, Kano State',
                'lga': 'Rano',
                'coords': '11.5500, 8.0833',
                'notes': 'Large-scale Newcastle outbreak. Vaccination campaign initiated.',
                'farmer': farmer_user,
                'farmer_name': 'Abubakar Ibrahim',
                'alert_status': 'Confirmed',
            },
        ]

        for data in reports_data:
            DiseaseReport.objects.get_or_create(
                report_code=data['report_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(reports_data)} disease reports")

    def _create_invoices(self):
        from apps.billing.models import Invoice, InvoiceItem
        from apps.patients.models import Patient

        today = timezone.now().strftime('%Y-%m-%d')
        patients = list(Patient.objects.all()[:3])

        if len(patients) < 1:
            return

        inv1, created = Invoice.objects.get_or_create(
            invoice_code=f'INV-{uuid.uuid4().hex[:6].upper()}',
            defaults={
                'patient': patients[0] if len(patients) > 0 else None,
                'patient_id_str': str(patients[0].id) if len(patients) > 0 else '',
                'owner_name': 'Aliyu Poultry Farm',
                'animal': 'Flock A - Broilers',
                'total': 15000.00,
                'status': 'Paid',
                'paid_at': timezone.now(),
            }
        )
        if created:
            InvoiceItem.objects.create(invoice=inv1, description='Newcastle vaccination (250 doses)', amount=10000.00)
            InvoiceItem.objects.create(invoice=inv1, description='Antibiotic treatment', amount=5000.00)

        inv2, created = Invoice.objects.get_or_create(
            invoice_code=f'INV-{uuid.uuid4().hex[:6].upper()}',
            defaults={
                'patient': patients[2] if len(patients) > 2 else None,
                'patient_id_str': str(patients[2].id) if len(patients) > 2 else '',
                'owner_name': 'Sani Bello',
                'animal': 'Rex - German Shepherd',
                'total': 5000.00,
                'status': 'Unpaid',
            }
        )
        if created:
            InvoiceItem.objects.create(invoice=inv2, description='Anti-rabies booster vaccine', amount=3500.00)
            InvoiceItem.objects.create(invoice=inv2, description='General health check', amount=1500.00)

        inv3, created = Invoice.objects.get_or_create(
            invoice_code=f'INV-{uuid.uuid4().hex[:6].upper()}',
            defaults={
                'patient': patients[1] if len(patients) > 1 else None,
                'patient_id_str': str(patients[1].id) if len(patients) > 1 else '',
                'owner_name': 'Hauwa Musa',
                'animal': 'Nanny - Sokoto Red',
                'total': 3500.00,
                'status': 'Paid',
                'paid_at': timezone.now() - timedelta(days=1),
            }
        )
        if created:
            InvoiceItem.objects.create(invoice=inv3, description='Deworming treatment (Albendazole)', amount=2000.00)
            InvoiceItem.objects.create(invoice=inv3, description='Follow-up consultation', amount=1500.00)

        self.stdout.write(f"  Created 3 invoices")

    def _create_notifications(self):
        from apps.notifications.models import Notification
        from apps.accounts.models import User

        vet_user = self._users.get('vet@vetlink.com')
        if not vet_user:
            return

        notifications_data = [
            {
                'notif_code': f'N{uuid.uuid4().hex[:6].upper()}',
                'title': 'New disease report submitted',
                'body': 'A new suspected Avian Influenza case has been reported in Dawakin Kudu LGA.',
                'tone': 'danger',
                'recipient': vet_user,
            },
            {
                'notif_code': f'N{uuid.uuid4().hex[:6].upper()}',
                'title': 'Lab result ready',
                'body': 'AI PCR panel result for sample LAB-001 is ready for review.',
                'tone': 'info',
                'recipient': vet_user,
            },
            {
                'notif_code': f'N{uuid.uuid4().hex[:6].upper()}',
                'title': 'Appointment reminder',
                'body': 'You have 3 appointments scheduled for today.',
                'tone': 'warning',
                'recipient': vet_user,
            },
            {
                'notif_code': f'N{uuid.uuid4().hex[:6].upper()}',
                'title': 'Drug stock low',
                'body': 'Ivermectin stock is below reorder level (6 vials remaining).',
                'tone': 'warning',
                'recipient': vet_user,
            },
            {
                'notif_code': f'N{uuid.uuid4().hex[:6].upper()}',
                'title': 'Welcome to VetLink Kano',
                'body': 'Your account is set up and ready to use. Start by creating a patient record.',
                'tone': 'success',
                'recipient': vet_user,
            },
        ]

        for data in notifications_data:
            Notification.objects.get_or_create(
                notif_code=data['notif_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(notifications_data)} notifications")

    def _create_herds(self):
        from apps.farmers.models import FarmerHerd
        from apps.accounts.models import User

        farmer_user = self._users.get('farmer@vetlink.com')
        if not farmer_user:
            return

        herds_data = [
            {
                'herd_code': f'H{uuid.uuid4().hex[:6].upper()}',
                'type': 'Poultry',
                'count': '250 birds',
                'healthy': 96,
                'farmer': farmer_user,
            },
            {
                'herd_code': f'H{uuid.uuid4().hex[:6].upper()}',
                'type': 'Goats',
                'count': '15 livestock',
                'healthy': 100,
                'farmer': farmer_user,
            },
            {
                'herd_code': f'H{uuid.uuid4().hex[:6].upper()}',
                'type': 'Cattle',
                'count': '8 animals',
                'healthy': 88,
                'farmer': farmer_user,
            },
        ]

        for data in herds_data:
            FarmerHerd.objects.get_or_create(
                herd_code=data['herd_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(herds_data)} herds")

    def _create_reminders(self):
        from apps.farmers.models import FarmerReminder
        from apps.accounts.models import User

        farmer_user = self._users.get('farmer@vetlink.com')
        if not farmer_user:
            return

        today = timezone.now().strftime('%Y-%m-%d')
        next_week = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        tomorrow = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        reminders_data = [
            {
                'reminder_code': f'R{uuid.uuid4().hex[:6].upper()}',
                'title': 'Newcastle vaccine due',
                'date': tomorrow,
                'tone': 'warning',
                'done': False,
                'farmer': farmer_user,
            },
            {
                'reminder_code': f'R{uuid.uuid4().hex[:6].upper()}',
                'title': 'Deworming due for goats',
                'date': next_week,
                'tone': 'info',
                'done': False,
                'farmer': farmer_user,
            },
            {
                'reminder_code': f'R{uuid.uuid4().hex[:6].upper()}',
                'title': 'Follow-up: goat treatment',
                'date': next_week,
                'tone': 'info',
                'done': False,
                'farmer': farmer_user,
            },
        ]

        for data in reminders_data:
            FarmerReminder.objects.get_or_create(
                reminder_code=data['reminder_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(reminders_data)} reminders")

    def _create_consultations(self):
        from apps.consultations.models import ConsultationRequest
        from apps.accounts.models import User

        farmer_user = self._users.get('farmer@vetlink.com')
        if not farmer_user:
            return

        consultations_data = [
            {
                'consultation_code': f'CON{uuid.uuid4().hex[:6].upper()}',
                'farmer': farmer_user,
                'farmer_name': 'Abubakar Ibrahim',
                'farm_location': 'Dawakin Kudu',
                'vet_name': 'Dr. Abdullahi Sani',
                'channel': 'in-app',
                'status': 'Accepted',
                'disease_name': 'Newcastle Disease',
                'symptoms_en': 'Sudden deaths in poultry, respiratory distress, green droppings',
                'species': 'Poultry (Chicken)',
                'animal_age': '6 weeks',
                'affected_count': 25,
                'severity': 'Severe',
            },
        ]

        for data in consultations_data:
            ConsultationRequest.objects.get_or_create(
                consultation_code=data['consultation_code'],
                defaults=data
            )
        self.stdout.write(f"  Created {len(consultations_data)} consultations")
