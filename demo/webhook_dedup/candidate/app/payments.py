"""Durable payment recording after process-local webhook deduplication."""

import sqlite3

DATABASE_PATH = "payments.db"


def record_payment(event_id: str, amount_cents: int) -> None:
    """Persist one payment record for a received webhook event."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS payments (event_id TEXT NOT NULL, amount_cents INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT INTO payments (event_id, amount_cents) VALUES (?, ?)",
            (event_id, amount_cents),
        )
