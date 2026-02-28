import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Category, Trace


def seed_if_empty(db: Session):
    if db.query(Trace).count() > 0:
        return

    now = datetime.utcnow()
    samples = [
        ("Why was I charged twice this month?", "Sorry about that—can you share the invoice ID so I can check duplicate charges?", Category.Billing),
        ("I want a refund for last week’s charge.", "I can help—what’s the invoice ID and reason for the refund request?", Category.Refund),
        ("I can’t log in, it says my account is locked.", "I can help unlock it—did you recently change your password or fail MFA attempts?", Category.AccountAccess),
        ("Please cancel my subscription effective today.", "I can cancel it—do you want it to end immediately or at the end of the billing period?", Category.Cancellation),
        ("Does your product support SSO?", "Yes—SSO is supported on our Business plan. Want setup steps for Okta/Azure AD?", Category.GeneralInquiry),
        # add more to reach 20+
    ]

    # Expand to >= 20 by repeating with small variations
    while len(samples) < 20:
        base = samples[len(samples) % 5]
        samples.append((base[0] + " (follow-up)", base[1], base[2]))

    for i, (um, br, cat) in enumerate(samples):
        db.add(
            Trace(
                id=str(uuid.uuid4()),
                user_message=um,
                bot_response=br,
                category=cat,
                timestamp=now - timedelta(minutes=i * 7),
                response_time_ms=250 + (i % 5) * 80,
            )
        )
    db.commit()
