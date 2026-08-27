from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import hashlib
import hmac


def verify_whatsapp_webhook(request):
    """GET - Verify WhatsApp Business API webhook."""
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "vetlink_kano_verify")

    if mode == "subscribe" and token == verify_token:
        return JsonResponse({"status": "ok"}, status=200)
    return JsonResponse({"error": "Forbidden"}, status=403)


@csrf_exempt
@require_POST
def handle_whatsapp_message(request):
    """POST - Receive and process incoming WhatsApp messages."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Verify signature if app secret is configured
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
    if app_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            app_secret.encode(), request.body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return JsonResponse({"error": "Invalid signature"}, status=403)

    # Extract message data
    entry = body.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])

    for msg in messages:
        from_number = msg.get("from", "")
        msg_type = msg.get("type", "")
        text = msg.get("text", {}).get("body", "") if msg_type == "text" else ""

        # Route message based on content
        response = process_message(text, from_number)

        # Send reply (stub - in production, use WhatsApp Business API)
        send_whatsapp_reply(from_number, response)

    return JsonResponse({"status": "ok"})


def process_message(text: str, from_number: str) -> str:
    """Process incoming WhatsApp message and generate response."""
    text_lower = text.lower().strip()

    # Command routing
    if text_lower in ["hi", "hello", "sannu", "start", "menu"]:
        return (
            "Welcome to VetLink Kano! 🐄\n\n"
            "Send a number to get started:\n"
            "1. Report disease\n"
            "2. Find vet\n"
            "3. Find medicine\n"
            "4. Vaccination reminder\n"
            "5. My livestock\n"
            "6. Health tips\n\n"
            "Reply with the number (1-6)"
        )

    if text_lower == "1" or text_lower.startswith("report"):
        return (
            "📋 Disease Report\n\n"
            "To report a disease, please send:\n"
            "DISEASE [animal type] [disease name] [LGA]\n\n"
            "Example:\n"
            "DISEASE cattle Foot-and-Mouth Kano Municipal"
        )

    if text_lower == "2" or text_lower.startswith("find vet"):
        return (
            "🔍 Find a Vet\n\n"
            "Send: VET [your LGA]\n"
            "Example: VET Gwale\n\n"
            "We'll show you available vets near you."
        )

    if text_lower == "3" or text_lower.startswith("medicine"):
        return (
            "💊 Medicine Finder\n\n"
            "Send: MEDICINE [drug name]\n"
            "Example: MEDICINE Oxytetracycline\n\n"
            "We'll show pharmacies with stock and prices."
        )

    if text_lower == "4" or text_lower.startswith("vaccination"):
        return (
            "💉 Vaccination Reminder\n\n"
            "Send: VACC [animal type] [age]\n"
            "Example: VACC chicken 6weeks\n\n"
            "We'll tell you which vaccines are due."
        )

    if text_lower == "5" or text_lower.startswith("my livestock"):
        return (
            "🐄 My Livestock\n\n"
            "To register an animal, send:\n"
            "REGISTER [name] [species] [breed] [age]\n"
            "Example: REGISTER Roma goat Sokoto 2years"
        )

    if text_lower == "6" or text_lower.startswith("health tip"):
        return (
            "💡 Daily Health Tip\n\n"
            "You'll receive daily health tips based on "
            "the current season and your livestock type.\n\n"
            "Send TIP ON to subscribe or TIP OFF to stop."
        )

    if text_lower.startswith("disease "):
        return (
            "✅ Thank you for your disease report!\n"
            "Our team will investigate and respond within 24 hours.\n"
            "Reference: DSR-" + from_number[-4:] + "\n\n"
            "For urgent outbreaks, call: 0800-VETLINK"
        )

    if text_lower.startswith("vet "):
        lga = text[4:].strip()
        return (
            f"🔍 Vets in {lga.title()}:\n\n"
            "1. Dr. Amina Bello - Large Animal\n"
            "2. Dr. Musa Abdullahi - Poultry\n"
            "3. Dr. Fatima Hussain - Small Ruminant\n\n"
            "Send BOOK [number] to schedule\n"
            "Example: BOOK 1"
        )

    if text_lower.startswith("medicine ") or text_lower.startswith("drug "):
        drug = text.split(" ", 1)[1].strip() if " " in text else ""
        return (
            f"💊 {drug.title()} availability:\n\n"
            "1. VetLink Pharmacy - ₦1,200\n"
            "2. Kano Vet Supplies - ₦1,100\n"
            "3. FarmMed Store - ₦1,350\n\n"
            "Send ORDER [number] to buy\n"
            "Example: ORDER 2"
        )

    # Default response
    return (
        "I didn't understand that. Send MENU to see options.\n\n"
        "Or try:\n"
        "- REPORT [disease info]\n"
        "- VET [your LGA]\n"
        "- MEDICINE [drug name]\n"
        "- TIP ON"
    )


def send_whatsapp_reply(to_number: str, message: str):
    """Send reply via WhatsApp Business API (stub)."""
    provider = getattr(settings, "WHATSAPP_PROVIDER", "console")

    if provider == "console":
        print(f"\n📱 WhatsApp → {to_number}:")
        print(message)
        print("-" * 40)

    # In production, integrate with:
    # - WhatsApp Business API (Meta Cloud API)
    # - Twilio WhatsApp
    # - Africa's Talking WhatsApp
    elif provider == "twilio":
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(from_='whatsapp:+14155238886', body=message, to=f'whatsapp:{to_number}')
        pass
    elif provider == "africastalking":
        # Africa's Talking WhatsApp integration
        pass
