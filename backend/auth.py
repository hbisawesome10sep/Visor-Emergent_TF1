import bcrypt
import jwt
from datetime import datetime, timezone
from fastapi import Header, HTTPException, Depends
from database import db
from config import JWT_SECRET, USER_SENSITIVE_FIELDS
from encryption import decrypt_field


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Auto-decrypt PII fields so all downstream endpoints get plaintext
        dek = user.get("encryption_key", "")
        if dek:
            for field in USER_SENSITIVE_FIELDS:
                val = user.get(field, "")
                if val and isinstance(val, str) and val.startswith("ENC:"):
                    try:
                        user[field] = decrypt_field(val, dek)
                    except Exception:
                        # Decryption failed (key mismatch) — keep encrypted value
                        pass
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
