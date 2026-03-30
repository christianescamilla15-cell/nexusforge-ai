"""Email integration via Resend API — send structured results by email."""
import os
import httpx

RESEND_URL = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, body: str, from_name: str = "NexusForge AI") -> dict:
    """Send an email via Resend API."""
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        return {"status": "not_configured", "message": "Set RESEND_API_KEY env var"}

    try:
        # Resend free tier uses onboarding@resend.dev as sender
        payload = {
            "from": f"{from_name} <onboarding@resend.dev>",
            "to": [to],
            "subject": subject,
            "html": body.replace("\n", "<br>"),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                RESEND_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return {"status": "success", "email_id": data.get("id"), "to": to}
    except Exception as e:
        return {"status": "error", "message": str(e)}
