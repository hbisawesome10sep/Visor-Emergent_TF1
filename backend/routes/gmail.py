from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from database import db
from auth import get_current_user
from config import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GMAIL_REDIRECT_URI, 
    GMAIL_SCOPES, GMAIL_TOKEN_SENSITIVE_FIELDS
)
from encryption import encrypt_field, decrypt_field
from bank_parser import parse_transaction_text
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
import uuid
import base64
import logging
import re as _re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/gmail/auth-url")
async def get_gmail_auth_url(user=Depends(get_current_user)):
    """Generate OAuth URL for Gmail integration."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Gmail integration not configured")

    state = str(uuid.uuid4())
    await db.gmail_oauth_states.insert_one({
        "user_id": user["id"],
        "state": state,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GMAIL_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={'+'.join(GMAIL_SCOPES)}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return {"auth_url": auth_url}


@router.get("/gmail/callback")
async def gmail_oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Gmail OAuth callback."""
    if error:
        return RedirectResponse(url="/settings?gmail_error=access_denied")

    state_doc = await db.gmail_oauth_states.find_one({"state": state})
    if not state_doc:
        return RedirectResponse(url="/settings?gmail_error=invalid_state")

    user_id = state_doc["user_id"]
    await db.gmail_oauth_states.delete_one({"state": state})

    import requests
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GMAIL_REDIRECT_URI,
        },
    )
    if token_resp.status_code != 200:
        logger.error(f"Token exchange failed: {token_resp.text}")
        return RedirectResponse(url="/settings?gmail_error=token_exchange_failed")

    tokens = token_resp.json()

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    user_dek = user.get("encryption_key", "") if user else ""

    access_token_enc = encrypt_field(tokens["access_token"], user_dek) if user_dek else tokens["access_token"]
    refresh_token_enc = encrypt_field(tokens.get("refresh_token", ""), user_dek) if user_dek and tokens.get("refresh_token") else tokens.get("refresh_token", "")
    client_secret_enc = encrypt_field(GOOGLE_CLIENT_SECRET, user_dek) if user_dek else GOOGLE_CLIENT_SECRET

    token_doc = {
        "user_id": user_id,
        "access_token": access_token_enc,
        "refresh_token": refresh_token_enc,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": client_secret_enc,
        "scopes": GMAIL_SCOPES,
        "expires_at": datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + tokens.get("expires_in", 3600)
        ).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.gmail_tokens.update_one(
        {"user_id": user_id},
        {"$set": token_doc},
        upsert=True
    )

    return RedirectResponse(url="/settings?gmail_connected=true")


@router.get("/gmail/status")
async def get_gmail_status(user=Depends(get_current_user)):
    """Check if Gmail is connected."""
    token = await db.gmail_tokens.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"connected": token is not None}


async def _get_gmail_creds(user_id: str) -> Credentials:
    """Get valid Gmail credentials for a user."""
    token = await db.gmail_tokens.find_one({"user_id": user_id}, {"_id": 0})
    if not token:
        raise HTTPException(401, "Gmail not connected")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    user_dek = user.get("encryption_key", "") if user else ""

    access_token = token.get("access_token", "")
    if user_dek and access_token.startswith("ENC:"):
        access_token = decrypt_field(access_token, user_dek)

    refresh_token = token.get("refresh_token", "")
    if user_dek and refresh_token and refresh_token.startswith("ENC:"):
        refresh_token = decrypt_field(refresh_token, user_dek)

    client_secret = token.get("client_secret", "")
    if user_dek and client_secret and client_secret.startswith("ENC:"):
        client_secret = decrypt_field(client_secret, user_dek)

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=token["token_uri"],
        client_id=token["client_id"],
        client_secret=client_secret,
    )

    if token.get("expires_at"):
        from dateutil.parser import parse as parse_date
        expires = parse_date(token["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expires:
            creds.refresh(GoogleRequest())
            new_access = encrypt_field(creds.token, user_dek) if user_dek else creds.token
            await db.gmail_tokens.update_one(
                {"user_id": user_id},
                {"$set": {"access_token": new_access, "expires_at": creds.expiry.isoformat() if creds.expiry else None}},
            )

    return creds


@router.post("/gmail/sync")
async def gmail_sync(user=Depends(get_current_user)):
    """Fetch and parse bank transaction emails from Gmail."""
    creds = await _get_gmail_creds(user["id"])
    service = build("gmail", "v1", credentials=creds)

    bank_queries = [
        "from:(alerts@hdfcbank.net OR alert@icicibank.com OR sbi OR axisbank OR kotak) subject:(transaction OR debit OR credit OR spent)",
        "subject:(bank transaction alert) newer_than:30d",
        "(debit OR credit) (INR OR Rs) newer_than:30d",
    ]

    parsed_transactions = []
    seen_msg_ids = set()

    existing = await db.gmail_synced_msgs.find(
        {"user_id": user["id"]}, {"msg_id": 1, "_id": 0}
    ).to_list(10000)
    seen_msg_ids = {d["msg_id"] for d in existing}

    for query in bank_queries:
        try:
            result = service.users().messages().list(
                userId="me", q=query, maxResults=50
            ).execute()
            messages = result.get("messages", [])

            for msg_meta in messages:
                msg_id = msg_meta["id"]
                if msg_id in seen_msg_ids:
                    continue
                seen_msg_ids.add(msg_id)

                try:
                    msg = service.users().messages().get(
                        userId="me", id=msg_id, format="full"
                    ).execute()

                    body_text = _extract_email_body(msg)
                    sender = _get_header(msg, "From")

                    if body_text:
                        txn = parse_transaction_text(body_text, sender)
                        if txn:
                            txn["gmail_msg_id"] = msg_id
                            txn["email_subject"] = _get_header(msg, "Subject")
                            parsed_transactions.append(txn)

                except Exception as e:
                    logger.warning(f"Failed to parse email {msg_id}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Gmail search failed for query: {e}")
            continue

    new_count = 0
    for txn in parsed_transactions:
        txn_id = str(uuid.uuid4())
        txn_doc = {
            "id": txn_id,
            "user_id": user["id"],
            "type": txn["type"],
            "amount": txn["amount"],
            "category": txn["category"],
            "description": txn["description"],
            "date": txn["date"],
            "is_recurring": False,
            "source": "gmail",
            "bank": txn.get("bank", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.transactions.insert_one(txn_doc)
        await db.gmail_synced_msgs.insert_one({
            "user_id": user["id"],
            "msg_id": txn["gmail_msg_id"],
            "txn_id": txn_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        })
        new_count += 1

    await db.gmail_sync_log.insert_one({
        "user_id": user["id"],
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "emails_scanned": len(seen_msg_ids),
        "total_parsed": new_count,
    })

    return {
        "success": True,
        "new_transactions": new_count,
        "emails_scanned": len(seen_msg_ids),
    }


@router.delete("/gmail/disconnect")
async def gmail_disconnect(user=Depends(get_current_user)):
    """Remove Gmail connection."""
    await db.gmail_tokens.delete_many({"user_id": user["id"]})
    await db.gmail_oauth_states.delete_many({"user_id": user["id"]})
    return {"success": True}


def _extract_email_body(msg: dict) -> str:
    """Extract plain text body from Gmail message."""
    payload = msg.get("payload", {})

    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")

    for part in parts:
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
            return _re.sub(r"<[^>]+>", " ", html)

    return msg.get("snippet", "")


def _get_header(msg: dict, name: str) -> str:
    """Get email header value."""
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


@router.post("/sms/parse")
async def parse_sms_batch(messages: list, user=Depends(get_current_user)):
    """Parse a batch of SMS messages sent from Android client."""
    parsed = []
    for sms in messages:
        body = sms.get("body", "")
        sender = sms.get("sender", "")
        txn = parse_transaction_text(body, sender)
        if txn:
            txn_id = str(uuid.uuid4())
            txn_doc = {
                "id": txn_id,
                "user_id": user["id"],
                "type": txn["type"],
                "amount": txn["amount"],
                "category": txn["category"],
                "description": txn["description"],
                "date": txn["date"],
                "is_recurring": False,
                "source": "sms",
                "bank": txn.get("bank", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.transactions.insert_one(txn_doc)
            parsed.append({"id": txn_id, "description": txn["description"], "amount": txn["amount"], "type": txn["type"]})

    return {"success": True, "parsed_count": len(parsed), "transactions": parsed}
