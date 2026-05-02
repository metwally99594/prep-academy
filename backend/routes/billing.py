"""
Billing routes - Stripe Checkout for Premium passes.

Design: instead of subscriptions, we sell time-bound passes (1 month, 6 months,
1 year). On successful payment, we extend the user's `premium_until` date.
This is friendlier for exam-prep students who just need access until exam day.
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

logger = logging.getLogger("billing")

# Server-defined packages (NEVER trust the frontend on prices)
PACKAGES = {
    "premium_1m": {
        "label": "Premium — 1 Monat",
        "amount": 14.99,
        "currency": "eur",
        "duration_days": 30,
        "tier": "premium",
        "features": ["Unlimited Medical Analyzer", "Unlimited PDF Notebook AI", "Audio Podcast", "Premium Quizzes"],
    },
    "premium_6m": {
        "label": "Premium — 6 Monate (Best Value)",
        "amount": 69.00,
        "currency": "eur",
        "duration_days": 180,
        "tier": "premium",
        "features": ["Alles aus 1 Monat", "Sparen Sie 23%", "Prüfungs-Simulationen unbegrenzt"],
    },
    "premium_1y": {
        "label": "Premium — 1 Jahr",
        "amount": 119.00,
        "currency": "eur",
        "duration_days": 365,
        "tier": "premium",
        "features": ["Alles aus 6 Monaten", "Sparen Sie 35%", "Premium AI (GPT-5.2 + Claude)", "Priority Support"],
    },
}


def _get_stripe(http_request: Request) -> StripeCheckout:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Payment system not configured")
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


class CheckoutBody(BaseModel):
    package_id: str
    origin_url: str  # frontend window.location.origin


def make_router(db, get_current_user):
    router = APIRouter()

    @router.get("/billing/packages")
    async def list_packages():
        """Public list of premium packages."""
        return {
            "packages": [
                {"id": pid, **{k: v for k, v in pkg.items()}}
                for pid, pkg in PACKAGES.items()
            ]
        }

    @router.get("/billing/me")
    async def my_subscription(user: dict = Depends(get_current_user)):
        """Current user's subscription status."""
        u = await db.users.find_one(
            {"id": user["id"]},
            {"_id": 0, "subscription_tier": 1, "premium_until": 1, "stripe_customer_id": 1},
        ) or {}
        tier = u.get("subscription_tier", "free")
        premium_until = u.get("premium_until")
        is_active = False
        if premium_until:
            try:
                until_dt = datetime.fromisoformat(premium_until.replace("Z", "+00:00")) if isinstance(premium_until, str) else premium_until
                is_active = until_dt > datetime.now(timezone.utc)
            except Exception:
                is_active = False
        if not is_active:
            tier = "free"
        return {"tier": tier, "premium_until": premium_until, "is_active": is_active}

    @router.post("/billing/checkout")
    async def create_checkout(
        body: CheckoutBody,
        http_request: Request,
        user: dict = Depends(get_current_user),
    ):
        """Start a Stripe Checkout for one of the predefined packages."""
        if body.package_id not in PACKAGES:
            raise HTTPException(status_code=400, detail="Ungültiges Paket")

        pkg = PACKAGES[body.package_id]
        stripe = _get_stripe(http_request)

        success_url = f"{body.origin_url.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{body.origin_url.rstrip('/')}/billing"

        metadata = {
            "user_id": user["id"],
            "user_email": user.get("email", ""),
            "package_id": body.package_id,
            "tier": pkg["tier"],
            "duration_days": str(pkg["duration_days"]),
        }

        req = CheckoutSessionRequest(
            amount=float(pkg["amount"]),
            currency=pkg["currency"],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )
        session = await stripe.create_checkout_session(req)

        # Record the pending transaction immediately
        await db.payment_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "session_id": session.session_id,
            "user_id": user["id"],
            "user_email": user.get("email", ""),
            "package_id": body.package_id,
            "amount": pkg["amount"],
            "currency": pkg["currency"],
            "status": "initiated",
            "payment_status": "pending",
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        return {"url": session.url, "session_id": session.session_id}

    @router.get("/billing/status/{session_id}")
    async def checkout_status(
        session_id: str,
        http_request: Request,
        user: dict = Depends(get_current_user),
    ):
        """Poll the checkout status. On first 'paid' result, extend user's premium_until."""
        # Find the pending transaction (must belong to this user for security)
        tx = await db.payment_transactions.find_one(
            {"session_id": session_id, "user_id": user["id"]},
            {"_id": 0},
        )
        if not tx:
            raise HTTPException(status_code=404, detail="Transaktion nicht gefunden")

        # If we've already finalised, return cached state (idempotency)
        if tx.get("status") == "completed" and tx.get("payment_status") == "paid":
            return {
                "status": "complete",
                "payment_status": "paid",
                "amount": tx.get("amount"),
                "currency": tx.get("currency"),
            }

        stripe = _get_stripe(http_request)
        cs = await stripe.get_checkout_status(session_id)

        # Update transaction record
        new_status = cs.status
        new_payment = cs.payment_status

        update = {
            "status": new_status,
            "payment_status": new_payment,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # On first transition to paid, credit the user's premium_until
        already_credited = tx.get("status") == "completed" and tx.get("payment_status") == "paid"
        if cs.payment_status == "paid" and not already_credited:
            pkg = PACKAGES.get(tx.get("package_id"))
            if pkg:
                duration = timedelta(days=pkg["duration_days"])
                u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "premium_until": 1}) or {}
                now = datetime.now(timezone.utc)
                current = u.get("premium_until")
                base = now
                if current:
                    try:
                        cur_dt = datetime.fromisoformat(current.replace("Z", "+00:00")) if isinstance(current, str) else current
                        if cur_dt > now:
                            base = cur_dt  # stack on top of remaining time
                    except Exception:
                        pass
                new_until = (base + duration).isoformat()
                await db.users.update_one(
                    {"id": user["id"]},
                    {"$set": {
                        "subscription_tier": pkg["tier"],
                        "premium_until": new_until,
                        # Premium also unlocks the Analyzer feature
                        "analyzer_enabled": True,
                    }},
                )
                update["status"] = "completed"
                logger.info(f"User {user['id']} credited with {pkg['duration_days']}d via session {session_id}")

        await db.payment_transactions.update_one(
            {"session_id": session_id}, {"$set": update}
        )

        return {
            "status": new_status,
            "payment_status": new_payment,
            "amount": cs.amount_total / 100.0 if cs.amount_total else 0,
            "currency": cs.currency,
        }

    @router.post("/webhook/stripe")
    async def stripe_webhook(http_request: Request):
        """Stripe webhook endpoint — keeps payment_transactions in sync."""
        body = await http_request.body()
        sig = http_request.headers.get("Stripe-Signature", "")
        stripe = _get_stripe(http_request)
        try:
            evt = await stripe.handle_webhook(body, sig)
        except Exception as e:
            logger.warning(f"Webhook verify failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Update the transaction (idempotent)
        sid = getattr(evt, "session_id", None)
        if sid:
            tx = await db.payment_transactions.find_one({"session_id": sid}, {"_id": 0})
            if tx and not (tx.get("status") == "completed" and tx.get("payment_status") == "paid"):
                if getattr(evt, "payment_status", "") == "paid":
                    # Credit user (mirrors logic in checkout_status — idempotent via the flag)
                    pkg = PACKAGES.get(tx.get("package_id"))
                    if pkg:
                        u = await db.users.find_one({"id": tx["user_id"]}, {"_id": 0, "premium_until": 1}) or {}
                        now = datetime.now(timezone.utc)
                        current = u.get("premium_until")
                        base = now
                        if current:
                            try:
                                cur_dt = datetime.fromisoformat(current.replace("Z", "+00:00")) if isinstance(current, str) else current
                                if cur_dt > now:
                                    base = cur_dt
                            except Exception:
                                pass
                        new_until = (base + timedelta(days=pkg["duration_days"])).isoformat()
                        await db.users.update_one(
                            {"id": tx["user_id"]},
                            {"$set": {
                                "subscription_tier": pkg["tier"],
                                "premium_until": new_until,
                                "analyzer_enabled": True,
                            }},
                        )
                    await db.payment_transactions.update_one(
                        {"session_id": sid},
                        {"$set": {
                            "status": "completed",
                            "payment_status": "paid",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "webhook_event_id": getattr(evt, "event_id", None),
                        }},
                    )
        return {"received": True}

    return router
