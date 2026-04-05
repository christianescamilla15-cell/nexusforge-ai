"""Post-workflow email notification — sends results to Gmail after any workflow completes."""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_RECIPIENT = "christianescamilla15@gmail.com"


async def notify_workflow_complete(
    workflow_name: str,
    status: str,
    summary: str,
    agents_used: list[str],
    total_tokens: int = 0,
    cost_usd: float = 0.0,
    processing_time_ms: float = 0,
    extra_details: Optional[dict] = None,
    recipient: Optional[str] = None,
) -> bool:
    """Send email notification after workflow completes.

    Returns True if email sent, False otherwise.
    Non-fatal — never raises exceptions.
    """
    try:
        from .client import send_email

        to = recipient or os.getenv("GMAIL_USER") or DEFAULT_RECIPIENT
        if not to:
            return False

        # Build HTML email
        agents_html = "".join(f"<li>{a}</li>" for a in agents_used)
        details_html = ""
        if extra_details:
            details_html = "<h3>Details</h3><ul>"
            for k, v in extra_details.items():
                details_html += f"<li><strong>{k}:</strong> {v}</li>"
            details_html += "</ul>"

        status_color = "#10B981" if status == "completed" else "#EF4444"

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1A1D23; color: #F3F4F6; padding: 24px; border-radius: 12px;">
                <h2 style="margin: 0 0 4px;">NexusForge AI</h2>
                <p style="color: #9CA3AF; margin: 0;">Workflow Execution Report</p>
            </div>

            <div style="padding: 24px; background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 0 0 12px 12px;">
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
                    <tr>
                        <td style="padding: 8px 0; color: #6B7280;">Workflow</td>
                        <td style="padding: 8px 0; font-weight: 600;">{workflow_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6B7280;">Status</td>
                        <td style="padding: 8px 0;">
                            <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 13px;">{status.upper()}</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6B7280;">Tokens</td>
                        <td style="padding: 8px 0; font-weight: 600;">{total_tokens:,} tokens — ${cost_usd:.4f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6B7280;">Latency</td>
                        <td style="padding: 8px 0;">{processing_time_ms:.0f}ms</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6B7280;">Agents</td>
                        <td style="padding: 8px 0;">{len(agents_used)} agents used</td>
                    </tr>
                </table>

                <h3 style="color: #111827; margin: 16px 0 8px;">Summary</h3>
                <p style="color: #374151; line-height: 1.6;">{summary}</p>

                <h3 style="color: #111827; margin: 16px 0 8px;">Agent Pipeline</h3>
                <ol style="color: #374151; padding-left: 20px;">{agents_html}</ol>

                {details_html}

                <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 20px 0;">
                <p style="color: #9CA3AF; font-size: 12px; margin: 0;">
                    NexusForge AI — Enterprise Agent Orchestration Platform
                </p>
            </div>
        </div>
        """

        result = await send_email(
            to=to,
            subject=f"[NexusForge] {workflow_name} — {status.upper()} ({total_tokens} tokens)",
            html_body=html,
        )

        sent = result.get("status") == "success"
        if sent:
            logger.info("Email sent to %s for workflow %s", to, workflow_name)
        else:
            logger.warning("Email failed for %s: %s", workflow_name, result.get("message"))
        email_ok = sent

    except Exception as e:
        logger.warning("Email notification failed (non-fatal): %s", e)
        email_ok = False

    # Also try Slack notification (best-effort, runs regardless of email)
    try:
        from app.integrations.slack.client import notify_slack
        await notify_slack(
            user_id=None,
            event_type="workflow.completed",
            workflow_name=workflow_name,
            status=status,
            details={"tokens": total_tokens, "cost": f"${cost_usd:.4f}", "agents": len(agents_used)},
        )
    except Exception:
        pass  # Slack is optional

    return email_ok
