"""Base webhook endpoint without duplicate-delivery handling."""

from app.payments import record_payment  # type: ignore[import-not-found]
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class WebhookEvent(BaseModel):
    """Represent a payment webhook delivery."""

    event_id: str
    amount_cents: int


@app.post("/webhooks/payment")
def receive_payment_webhook(event: WebhookEvent) -> dict[str, str]:
    """Record the durable payment for every received delivery."""
    record_payment(event.event_id, event.amount_cents)
    return {"status": "accepted"}
