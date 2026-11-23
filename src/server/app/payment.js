from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.templating import Jinja2Templates

import config
import constants
from models import ArrayAppend, Guild, PremiumPlan, PremiumTxn, User

router = APIRouter()
template = Jinja2Templates(directory="src/server/templates")


def create_hash(txnId: str, amount: str, productInfo: str, firstName: str, email: str):
    return hashlib.sha512(
        f"{config.PAYU_KEY}|{txnId}|{amount}|{productInfo}|{firstName}|{email}|||||||||||{config.PAYU_SALT}".encode(
            "utf-8"
        )
    ).hexdigest()


def verify_payu_response_hash(form) -> bool:
    received_hash = form.get("hash")
    if not received_hash:
        return False

    hash_string = (
        f"{config.PAYU_SALT}|{form.get('status', '')}|||||||||||"
        f"{form.get('email', '')}|{form.get('firstname', '')}|{form.get('productinfo', '')}|"
        f"{form.get('amount', '')}|{form.get('txnid', '')}|{config.PAYU_KEY}"
    )
    expected_hash = hashlib.sha512(hash_string.encode("utf-8")).hexdigest()
    return received_hash.lower() == expected_hash.lower()


def require_fastapi_key(x_api_key: str | None = Header(default=None)) -> None:
    if not config.FASTAPI_KEY:
        return
    if x_api_key != config.FASTAPI_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("/getpremium")
async def get_premium(request: Request, txnId: str, x_api_key: str | None = Header(default=None)):
    require_fastapi_key(x_api_key)

    record = await PremiumTxn.get_or_none(txnid=txnId)

    if not record:
        return {"error": "Invalid Transaction ID"}

    if record.completed_at:
        return {"error": "Transaction already completed"}

    plan = await PremiumPlan.get(pk=record.plan_id)

    payu_hash = create_hash(txnId, plan.price, "premium", record.user_id, "abcd@gmail.com")

    data = {
        "key": config.PAYU_KEY,
        "txnid": txnId,
        "amount": plan.price,
        "productinfo": "premium",
        "firstname": record.user_id,
        "email": "abcd@gmail.com",
        "surl": f"{config.SUCCESS_URL}{txnId}",
        "furl": f"{config.FAILED_URL}{txnId}",
        "phone": "9999999999",
        "action": config.PAYU_PAYMENT_LINK,
        "hash": payu_hash,
    }

    return template.TemplateResponse("payu.html", {"request": request, "posted": data})


@router.post("/premium_success")
async def premium_success(request: Request, txnId: str):
    from core import bot

    try:
        form = await request.form()
    except Exception:
        return {"error": "Invalid Request."}

    if not verify_payu_response_hash(form):
        return {"error": "Invalid payment signature."}

    if form.get("status") != "success":
        return {"error": f"Transaction Status: {form.get('status')}"}

    record = await PremiumTxn.get_or_none(txnid=txnId)
    if not record:
        return {"error": "Transaction Id is invalid."}

    if record.completed_at:
        return {"error": "Transaction is already complete."}

    await PremiumTxn.get(txnid=txnId).update(raw_data=dict(form), completed_at=datetime.now(constants.IST))
    u, b = await User.get_or_create(user_id=record.user_id)
    plan = await PremiumPlan.get(pk=record.plan_id)

    end_time = u.premium_expire_time + plan.duration if u.is_premium else datetime.now(constants.IST) + plan.duration

    await User.get(pk=u.pk).update(is_premium=True, premium_expire_time=end_time)
    await User.get(pk=u.user_id).update(made_premium=ArrayAppend("made_premium", u.user_id))

    bot.dispatch("premium_purchase", record.txnid)

    guild = await Guild.get(pk=record.guild_id)
    end_time = guild.premium_end_time + plan.duration if guild.is_premium else datetime.now(constants.IST) + plan.duration
    await Guild.get(pk=guild.pk).update(is_premium=True, premium_end_time=end_time, made_premium_by=u.user_id)

    return {"success": "Transaction was successful. Please return to discord App."}


@router.post("/premium_failed")
async def premium_failed(request: Request, txnId: str):
    try:
        form = await request.form()
    except Exception:
        return {"error": "Invalid Request."}

    if not verify_payu_response_hash(form):
        return {"error": "Invalid payment signature."}

    await PremiumTxn.get(txnid=txnId).update(completed_at=datetime.now(constants.IST), raw_data=dict(form))

    return {"error": "Transaction Cancelled."}
