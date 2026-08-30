"""Webhook endpoint with process-local duplicate-delivery handling."""

from app.payments import record_payment  # type: ignore[import-not-found]
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
processed_events: set[str] = set()


class WebhookEvent(BaseModel):
    """Represent a payment webhook delivery."""

    event_id: str
    amount_cents: int


@app.post("/webhooks/payment")
def receive_payment_webhook(event: WebhookEvent) -> dict[str, str]:
    """Record a payment only when this process has not observed the event."""
    if event.event_id in processed_events:
        return {"status": "duplicate"}
    record_payment(event.event_id, event.amount_cents)
    processed_events.add(event.event_id)
    return {"status": "accepted"}
