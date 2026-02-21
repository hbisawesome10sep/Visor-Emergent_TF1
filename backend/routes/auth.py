from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import hash_password, verify_password, create_token, get_current_user
from models import UserCreate, UserLogin
from config import USER_SENSITIVE_FIELDS
from encryption import generate_user_dek, encrypt_field, decrypt_field
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/api")


@router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(user_data.pan) != 10:
        raise HTTPException(status_code=400, detail="PAN must be 10 characters")
    if len(user_data.aadhaar.replace(" ", "").replace("-", "")) != 12:
        raise HTTPException(status_code=400, detail="Aadhaar must be 12 digits")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    aadhaar_clean = user_data.aadhaar.replace(" ", "").replace("-", "")

    user_dek = generate_user_dek()

    user_doc = {
        "id": user_id,
        "email": user_data.email.lower(),
        "password": hash_password(user_data.password),
        "full_name": encrypt_field(user_data.full_name, user_dek),
        "dob": encrypt_field(user_data.dob, user_dek),
        "pan": encrypt_field(user_data.pan.upper(), user_dek),
        "aadhaar": encrypt_field(aadhaar_clean, user_dek),
        "encryption_key": user_dek,
        "created_at": now,
    }
    await db.users.insert_one(user_doc)

    token = create_token(user_id, user_data.email.lower())
    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": user_data.email.lower(),
            "full_name": user_data.full_name,
            "dob": user_data.dob,
            "pan": user_data.pan.upper(),
            "aadhaar_last4": aadhaar_clean[-4:],
            "created_at": now,
        }
    }


@router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email.lower()}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["email"])

    dek = user.get("encryption_key", "")
    decrypted = {}
    for field in USER_SENSITIVE_FIELDS:
        val = user.get(field, "")
        if dek and val and isinstance(val, str) and val.startswith("ENC:"):
            decrypted[field] = decrypt_field(val, dek)
        else:
            decrypted[field] = val

    aadhaar = decrypted.get("aadhaar", "")
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": decrypted.get("full_name", ""),
            "dob": decrypted.get("dob", ""),
            "pan": decrypted.get("pan", ""),
            "aadhaar_last4": aadhaar[-4:] if len(aadhaar) >= 4 else "",
            "created_at": user.get("created_at", ""),
        }
    }


@router.get("/auth/profile")
async def get_profile(user=Depends(get_current_user)):
    aadhaar = user.get("aadhaar", "")
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name", ""),
        "dob": user.get("dob", ""),
        "pan": user.get("pan", ""),
        "aadhaar_last4": aadhaar[-4:] if len(aadhaar) >= 4 else "",
        "created_at": user.get("created_at", ""),
        "is_encrypted": bool(user.get("encryption_key", "")),
    }
