"""WhatsApp integration — send messages via WhatsApp API link or Twilio."""
import os
import urllib.parse
import httpx


async def send_whatsapp(phone: str, message: str) -> dict:
    """Send WhatsApp message. Uses Twilio if configured, otherwise generates API link."""
    twilio_sid = os.environ.get("TWILIO_SID", "").strip()
    twilio_token = os.environ.get("TWILIO_TOKEN", "").strip()
    twilio_from = os.environ.get("TWILIO_WHATSAPP_NUMBER", "").strip()

    # Option 1: Twilio (automatic send)
    if twilio_sid and twilio_token and twilio_from:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                    auth=(twilio_sid, twilio_token),
                    data={
                        "From": f"whatsapp:{twilio_from}",
                        "To": f"whatsapp:+{phone}",
                        "Body": message,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            return {"status": "success", "method": "twilio", "sid": data.get("sid"), "phone": phone}
        except Exception as e:
            return {"status": "error", "method": "twilio", "message": str(e)}

    # Option 2: WhatsApp API link (user clicks to send)
    encoded = urllib.parse.quote(message)
    link = f"https://wa.me/{phone}?text={encoded}"
    return {"status": "success", "method": "link", "whatsapp_link": link, "phone": phone}
