from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.veterinarians.models import VeterinarianProfile
from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.pharmacy.models import DrugStock
from apps.laboratory.models import LabSample
from apps.surveillance.models import DiseaseReport
from apps.billing.models import Invoice, InvoiceItem
from apps.clinical_notes.models import CaseNote
from apps.notifications.models import Notification
from apps.farmers.models import FarmerHerd, FarmerReminder
from apps.consultations.models import ConsultationRequest, ChatMessage


class Command(BaseCommand):
    help = 'Seeds initial demonstration data for VetLink Kano backend'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting VetLink Kano demo data seeding...'))

        # 1. Users & Superadmin
        admin_user, _ = User.objects.get_or_create(
            email='admin@vetlinkkano.ng',
            defaults={
                'full_name': 'System Administrator',
                'user_type': User.UserType.SUPER_ADMIN,
                'lga': 'Kano Municipal',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('AdminPass123!')
        admin_user.save()

        # 2. Veterinarians (SEED_VETS)
        seed_vets = [
            {
                "vet_code": "VET001", "full_name": "Dr. Abdullahi Sani", "license_number": "VCN/2015/4521",
                "qualifications": "DVM, MSc Poultry Health Management",
                "specializations": ["Poultry / Avian", "Mixed Practice"],
                "species_treated": ["Poultry", "Cattle", "Goat / Sheep"],
                "diseases_expertise": ["Avian Influenza", "Newcastle Disease", "Gumboro Disease", "Marek's Disease"],
                "years_experience": 11, "languages": ["English", "Hausa"],
                "clinic_name": "Kano Veterinary Clinic", "clinic_address": "15 Zoo Road, Kano Municipal",
                "lga": "Kano Municipal", "service_area": ["Kano Municipal", "Dawakin Kudu", "Dawakin Tofa", "Ungogo"],
                "whatsapp_number": "+2348031234567", "phone": "0803-123-4567", "email": "a.sani@vetlinkkano.ng",
                "available": True, "available_online": True, "available_emergency": True,
                "consultation_fee": 3000, "rating": 4.8, "total_consultations": 312, "avatar_initials": "AS",
                "bio": "Specialist in poultry health and production diseases with over a decade of clinical experience in Kano State. Fluent in Hausa and English for effective farmer communication.",
            },
            {
                "vet_code": "VET002", "full_name": "Dr. Fatima Ibrahim", "license_number": "VCN/2018/6834",
                "qualifications": "DVM, PGD Ruminant Production",
                "specializations": ["Small Ruminants (Goat / Sheep)", "Large Animals (Cattle / Camel)"],
                "species_treated": ["Goat / Sheep", "Cattle", "Camel"],
                "diseases_expertise": ["PPR", "CBPP", "Foot and Mouth Disease", "Anthrax", "Brucellosis"],
                "years_experience": 6, "languages": ["English", "Hausa", "Fulfulde"],
                "clinic_name": "Dawakin Kudu Veterinary Centre", "clinic_address": "Dawakin Kudu, Off Zaria Road",
                "lga": "Dawakin Kudu", "service_area": ["Dawakin Kudu", "Bebeji", "Gwarzo", "Kabo", "Rano"],
                "whatsapp_number": "+2348059876543", "phone": "0805-987-6543", "email": "f.ibrahim@vetlinkkano.ng",
                "available": True, "available_online": True, "available_emergency": False,
                "consultation_fee": 2500, "rating": 4.7, "total_consultations": 198, "avatar_initials": "FI",
                "bio": "Large and small ruminant specialist serving rural Kano LGAs. Experienced in field outbreak investigation and herd health management. Speaks Fulfulde for Fulani pastoralists.",
            },
            {
                "vet_code": "VET003", "full_name": "Dr. Musa Abubakar", "license_number": "VCN/2012/2210",
                "qualifications": "DVM, PhD Veterinary Epidemiology",
                "specializations": ["Public Health / Epidemiology", "Large Animals (Cattle / Camel)"],
                "species_treated": ["Cattle", "Camel", "Poultry"],
                "diseases_expertise": ["Anthrax", "Rabies", "Avian Influenza", "Brucellosis", "Foot and Mouth Disease"],
                "years_experience": 14, "languages": ["English", "Hausa", "Arabic"],
                "clinic_name": "Kano State Veterinary Laboratory", "clinic_address": "Bompai Road, Nassarawa",
                "lga": "Nasarawa", "service_area": ["Nasarawa", "Kano Municipal", "Fagge", "Gwale", "Tarauni"],
                "whatsapp_number": "+2348072223344", "phone": "0807-222-3344", "email": "m.abubakar@vetlinkkano.ng",
                "available": True, "available_online": True, "available_emergency": True,
                "consultation_fee": 5000, "rating": 4.9, "total_consultations": 487, "avatar_initials": "MA",
                "bio": "Senior veterinary epidemiologist specialising in zoonotic and transboundary animal diseases. Extensive experience in outbreak investigation, laboratory diagnostics, and One Health programmes.",
            },
            {
                "vet_code": "VET004", "full_name": "Dr. Hauwa Garba", "license_number": "VCN/2020/9145",
                "qualifications": "DVM, Cert. Companion Animal Medicine",
                "specializations": ["Companion Animals (Dog / Cat)", "Mixed Practice"],
                "species_treated": ["Dog / Cat", "Rabbit", "Poultry"],
                "diseases_expertise": ["Rabies", "Parvovirus", "Distemper", "Feline Panleukopenia"],
                "years_experience": 4, "languages": ["English", "Hausa"],
                "clinic_name": "PetCare Kano", "clinic_address": "Sharada Phase 2, Kano",
                "lga": "Kumbotso", "service_area": ["Kumbotso", "Dawakin Tofa", "Kano Municipal", "Ungogo"],
                "whatsapp_number": "+2348061122334", "phone": "0806-112-2334", "email": "h.garba@vetlinkkano.ng",
                "available": True, "available_online": True, "available_emergency": False,
                "consultation_fee": 2000, "rating": 4.6, "total_consultations": 134, "avatar_initials": "HG",
                "bio": "Companion animal and exotic pet specialist. Passionate about preventive medicine, vaccination programmes, and responsible pet ownership in urban Kano.",
            },
            {
                "vet_code": "VET005", "full_name": "Dr. Yusuf Tukur", "license_number": "VCN/2016/5502",
                "qualifications": "DVM, MSc Veterinary Surgery",
                "specializations": ["Surgery", "Large Animals (Cattle / Camel)"],
                "species_treated": ["Cattle", "Goat / Sheep", "Camel"],
                "diseases_expertise": ["Fractures", "Wound Management", "Dystocia", "Castration"],
                "years_experience": 8, "languages": ["English", "Hausa"],
                "clinic_name": "Bichi Veterinary Outpost", "clinic_address": "Bichi Town, Kano-Katsina Road",
                "lga": "Bichi", "service_area": ["Bichi", "Dambatta", "Makoda", "Rimin Gado", "Bagwai"],
                "whatsapp_number": "+2348034455667", "phone": "0803-445-5667", "email": "y.tukur@vetlinkkano.ng",
                "available": False, "available_online": True, "available_emergency": True,
                "consultation_fee": 3500, "rating": 4.5, "total_consultations": 221, "avatar_initials": "YT",
                "bio": "Veterinary surgeon specialising in large animal field surgery, reproductive services, and emergency obstetrics. Serves the northern LGAs of Kano State.",
            },
        ]

        created_vets = {}
        for v in seed_vets:
            code = v["vet_code"]
            obj, _ = VeterinarianProfile.objects.update_or_create(vet_code=code, defaults=v)
            created_vets[code] = obj

        # 3. Patients (SEED_PATIENTS)
        seed_patients = [
            {"patient_code": "P001", "owner_name": "Aliyu Poultry Farm", "owner_phone": "0803-555-0101", "lga": "Dawakin Kudu", "species": "Poultry (Chicken)", "animal_name": "Flock A", "animal_age": "6 months"},
            {"patient_code": "P002", "owner_name": "Hauwa Musa", "owner_phone": "0803-555-0202", "lga": "Kano Municipal", "species": "Goat / Sheep", "animal_name": "Nanny", "animal_age": "3 years"},
            {"patient_code": "P003", "owner_name": "Dawakin Kudu Coop", "owner_phone": "0803-555-0303", "lga": "Dawakin Kudu", "species": "Cattle", "animal_name": "Herd B", "animal_age": "Mixed"},
            {"patient_code": "P004", "owner_name": "Sani Bello", "owner_phone": "0803-555-0404", "lga": "Kano Municipal", "species": "Dog / Cat", "animal_name": "Rex", "animal_age": "2 years"},
        ]
        created_patients = {}
        for p in seed_patients:
            code = p["patient_code"]
            obj, _ = Patient.objects.update_or_create(patient_code=code, defaults=p)
            created_patients[code] = obj

        # 4. Appointments (SEED_APPOINTMENTS)
        seed_appts = [
            {"appointment_code": "A001", "time": "09:00", "date": "2024-05-22", "patient_id_str": "P001", "patient": created_patients.get("P001"), "owner_name": "Aliyu Poultry Farm", "animal": "Poultry · 250 birds", "reason": "Flock health check", "notes": "", "status": "Completed"},
            {"appointment_code": "A002", "time": "10:30", "date": "2024-05-22", "patient_id_str": "P002", "patient": created_patients.get("P002"), "owner_name": "Hauwa Musa", "animal": "Goat · 3 yrs", "reason": "Deworming", "notes": "", "status": "In progress"},
            {"appointment_code": "A003", "time": "12:00", "date": "2024-05-22", "patient_id_str": "P003", "patient": created_patients.get("P003"), "owner_name": "Dawakin Kudu Coop", "animal": "Cattle · 8 heads", "reason": "Vaccination (CBPP)", "notes": "", "status": "Scheduled"},
            {"appointment_code": "A004", "time": "14:15", "date": "2024-05-22", "patient_id_str": "P004", "patient": created_patients.get("P004"), "owner_name": "Sani Bello", "animal": "Dog · 2 yrs", "reason": "Anti-rabies booster", "notes": "", "status": "Scheduled"},
        ]
        for a in seed_appts:
            code = a["appointment_code"]
            Appointment.objects.update_or_create(appointment_code=code, defaults=a)

        # 5. Drugs (SEED_DRUGS)
        seed_drugs = [
            {"drug_code": "D001", "name": "Ivermectin", "category": "Antiparasitic", "quantity": 6, "unit": "vials", "reorder_level": 15, "expiry_date": "2025-03-01", "unit_cost": 850},
            {"drug_code": "D002", "name": "Oxytetracycline", "category": "Antibiotic", "quantity": 45, "unit": "bottles", "reorder_level": 20, "expiry_date": "2025-08-01", "unit_cost": 1200},
            {"drug_code": "D003", "name": "Newcastle Vaccine", "category": "Vaccine", "quantity": 200, "unit": "doses", "reorder_level": 100, "expiry_date": "2024-12-01", "unit_cost": 150},
            {"drug_code": "D004", "name": "CBPP Vaccine", "category": "Vaccine", "quantity": 80, "unit": "doses", "reorder_level": 50, "expiry_date": "2025-01-01", "unit_cost": 280},
            {"drug_code": "D005", "name": "Albendazole", "category": "Antiparasitic", "quantity": 30, "unit": "tablets", "reorder_level": 40, "expiry_date": "2025-06-01", "unit_cost": 220},
        ]
        for d in seed_drugs:
            DrugStock.objects.update_or_create(drug_code=d["drug_code"], defaults=d)

        # 6. Lab Samples (SEED_LAB)
        seed_lab = [
            {"sample_code": "LAB-24-0912", "species": "Poultry", "test": "AI PCR panel", "facility": "Kano Vet Clinic", "status": "Result ready", "priority": "Urgent", "date_received": "2024-05-21", "result_findings": "H5N1 detected — positive", "result_positive": True},
            {"sample_code": "LAB-24-0913", "species": "Cattle", "test": "Brucella ELISA", "facility": "Dawakin Kudu VC", "status": "In analysis", "priority": "Routine", "date_received": "2024-05-22"},
            {"sample_code": "LAB-24-0914", "species": "Goat", "test": "PPR antigen", "facility": "Bebeji Outpost", "status": "Received", "priority": "Urgent", "date_received": "2024-05-22"},
            {"sample_code": "LAB-24-0915", "species": "Dog", "test": "Rabies FAT", "facility": "Kano Municipal", "status": "In analysis", "priority": "Urgent", "date_received": "2024-05-21"},
            {"sample_code": "LAB-24-0916", "species": "Poultry", "test": "Newcastle HI", "facility": "Rano Coop", "status": "Result ready", "priority": "Routine", "date_received": "2024-05-20", "result_findings": "HI titre 1:64 — positive", "result_positive": True},
        ]
        for l in seed_lab:
            LabSample.objects.update_or_create(sample_code=l["sample_code"], defaults=l)

        # 7. Disease Reports (SEED_REPORTS)
        seed_reports = [
            {"report_code": "VK100001", "species": "Poultry (Chicken)", "disease": "Avian Influenza (Bird Flu)", "affected": 120, "dead": 45, "signs": ["Sudden death", "Respiratory distress", "Swollen head"], "date": "2024-05-22", "location": "Dawakin Kudu, Kano State", "lga": "Dawakin Kudu", "farmer_name": "Aliyu Poultry Farm", "alert_status": "Suspected"},
            {"report_code": "VK100002", "species": "Cattle", "disease": "Anthrax", "affected": 5, "dead": 2, "signs": ["Sudden death", "Nasal discharge"], "date": "2024-05-21", "location": "Bebeji LGA, Kano State", "lga": "Bebeji", "farmer_name": "Bebeji Farmer Coop", "alert_status": "Under investigation"},
            {"report_code": "VK100003", "species": "Dog / Cat", "disease": "Rabies", "affected": 3, "dead": 1, "signs": ["Loss of appetite", "Skin lesions"], "date": "2024-05-21", "location": "Kano Municipal", "lga": "Kano Municipal", "farmer_name": "Sani Bello", "alert_status": "Confirmed"},
            {"report_code": "VK100004", "species": "Goat / Sheep", "disease": "PPR (Peste des Petits Ruminants)", "affected": 30, "dead": 8, "signs": ["Diarrhoea", "Coughing / sneezing", "Nasal discharge"], "date": "2024-05-20", "location": "Gwarzo LGA, Kano State", "lga": "Gwarzo", "farmer_name": "Gwarzo Herders Assoc.", "alert_status": "Confirmed"},
            {"report_code": "VK100005", "species": "Poultry (Chicken)", "disease": "Newcastle Disease", "affected": 80, "dead": 20, "signs": ["Sudden death", "Respiratory distress"], "date": "2024-05-20", "location": "Rano LGA, Kano State", "lga": "Rano", "farmer_name": "Rano Poultry Coop", "alert_status": "Suspected"},
        ]
        for r in seed_reports:
            DiseaseReport.objects.update_or_create(report_code=r["report_code"], defaults=r)

        # 8. Invoices (SEED_INVOICES)
        seed_invoices = [
            {
                "invoice_code": "INV-001", "patient_id_str": "P001", "patient": created_patients.get("P001"), "owner_name": "Aliyu Poultry Farm", "animal": "Poultry · 250 birds", "total": 30000, "status": "Paid",
                "items": [{"description": "Flock health check", "amount": 15000}, {"description": "Newcastle vaccine (100 doses)", "amount": 15000}]
            },
            {
                "invoice_code": "INV-002", "patient_id_str": "P002", "patient": created_patients.get("P002"), "owner_name": "Hauwa Musa", "animal": "Goat · 3 yrs", "total": 5500, "status": "Unpaid",
                "items": [{"description": "Deworming (Ivermectin)", "amount": 3500}, {"description": "Consultation fee", "amount": 2000}]
            },
            {
                "invoice_code": "INV-003", "patient_id_str": "P004", "patient": created_patients.get("P004"), "owner_name": "Sani Bello", "animal": "Dog · 2 yrs", "total": 6200, "status": "Unpaid",
                "items": [{"description": "Anti-rabies booster", "amount": 4200}, {"description": "Consultation fee", "amount": 2000}]
            },
        ]
        for inv in seed_invoices:
            items = inv.pop("items")
            inv_obj, _ = Invoice.objects.update_or_create(invoice_code=inv["invoice_code"], defaults=inv)
            inv_obj.services.all().delete()
            for it in items:
                InvoiceItem.objects.create(invoice=inv_obj, **it)

        # 9. Case Notes (SEED_NOTES)
        seed_notes = [
            {"note_code": "CN001", "patient_id_str": "P001", "patient": created_patients.get("P001"), "owner_name": "Aliyu Poultry Farm", "animal": "Poultry · 250 birds", "date": "2024-05-22", "vet_name": "Dr. Abdullahi Sani", "diagnosis": "Healthy flock; vaccination up-to-date", "treatment": "Newcastle vaccine administered (100 doses)", "follow_up_date": "2024-08-22", "notes": "Advise owner on biosecurity measures"},
            {"note_code": "CN002", "patient_id_str": "P002", "patient": created_patients.get("P002"), "owner_name": "Hauwa Musa", "animal": "Goat · 3 yrs", "date": "2024-05-22", "vet_name": "Dr. Abdullahi Sani", "diagnosis": "Nematode infestation", "treatment": "Ivermectin 1ml/50kg administered", "follow_up_date": "2024-06-05", "notes": "Re-check faecal egg count in 2 weeks"},
        ]
        for n in seed_notes:
            CaseNote.objects.update_or_create(note_code=n["note_code"], defaults=n)

        # 10. Notifications (SEED_NOTIFICATIONS)
        seed_notifs = [
            {"notif_code": "N001", "title": "Low drug stock: Ivermectin", "body": "Only 6 vials remaining. Reorder level is 15.", "tone": "warning", "read": False},
            {"notif_code": "N002", "title": "New disease report submitted", "body": "Avian Influenza suspected — Dawakin Kudu LGA", "tone": "danger", "read": False},
            {"notif_code": "N003", "title": "Lab result ready", "body": "LAB-24-0912: AI PCR panel — result ready for review.", "tone": "info", "read": False},
            {"notif_code": "N004", "title": "Appointment completed", "body": "Aliyu Poultry Farm flock health check completed.", "tone": "success", "read": True},
        ]
        for notif in seed_notifs:
            Notification.objects.update_or_create(notif_code=notif["notif_code"], defaults=notif)

        # 11. Farmer Herds & Reminders
        seed_herds = [
            {"herd_code": "H001", "type": "Poultry", "count": "250 birds", "healthy": 96},
            {"herd_code": "H002", "type": "Goats", "count": "15 livestock", "healthy": 100},
            {"herd_code": "H003", "type": "Cattle", "count": "8 animals", "healthy": 88},
        ]
        for h in seed_herds:
            FarmerHerd.objects.update_or_create(herd_code=h["herd_code"], defaults=h)

        seed_reminders = [
            {"reminder_code": "R001", "title": "Newcastle vaccine due", "date": "2024-05-25", "tone": "warning", "done": False},
            {"reminder_code": "R002", "title": "Deworming due", "date": "2024-05-20", "tone": "danger", "done": False},
            {"reminder_code": "R003", "title": "Follow-up: goat treatment", "date": "2024-05-28", "tone": "info", "done": False},
        ]
        for rem in seed_reminders:
            FarmerReminder.objects.update_or_create(reminder_code=rem["reminder_code"], defaults=rem)

        # 12. Consultations & Messages (SEED_CONSULTATIONS)
        vet1 = created_vets.get("VET001")
        con1, _ = ConsultationRequest.objects.update_or_create(
            consultation_code="CON001",
            defaults={
                "farmer_name": "Aliyu Poultry Farm",
                "farm_location": "Dawakin Kudu, Kano State",
                "vet": vet1,
                "vet_id_str": "VET001",
                "vet_name": "Dr. Abdullahi Sani",
                "channel": "in-app",
                "status": "Resolved",
                "disease_name": "Newcastle Disease",
                "symptoms_en": "Birds sneezing, loss of appetite, greenish droppings, sudden deaths",
                "symptoms_ha": "Tsuntsayen suna atishawa, rashin cin abinci, najasa mai kore-kore, mutuwa kwatsam",
                "species": "Poultry",
                "animal_age": "6 months",
                "animal_gender": "Mixed",
                "affected_count": 45,
                "duration_days": 3,
                "severity": "Severe",
                "additional_notes": "Approximately 8 birds already dead",
            }
        )

        messages_data = [
            {"message_code": "M001", "sender": "farmer", "sender_name": "Aliyu", "text": "Good morning doctor, my birds are sick. Many are dying.", "read": True},
            {"message_code": "M002", "sender": "vet", "sender_name": "Dr. Abdullahi Sani", "text": "Assalamu alaikum Aliyu. This looks like Newcastle Disease. Isolate the sick birds immediately and don't add new birds to the flock. I will visit tomorrow morning.", "read": True},
            {"message_code": "M003", "sender": "farmer", "sender_name": "Aliyu", "text": "Thank you doctor. I have separated them. Will you bring the vaccine?", "read": True},
            {"message_code": "M004", "sender": "vet", "sender_name": "Dr. Abdullahi Sani", "text": "Yes, I will bring Newcastle vaccine and antibiotics for secondary infections. Keep water and feed available. See you tomorrow at 9am.", "read": True},
        ]
        for m in messages_data:
            m_code = m.pop("message_code")
            ChatMessage.objects.update_or_create(message_code=m_code, defaults={"consultation": con1, **m})

        self.stdout.write(self.style.SUCCESS('Successfully seeded all VetLink Kano demonstration records!'))
