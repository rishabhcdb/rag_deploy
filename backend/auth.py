import jwt
from jwt import PyJWKClient
from functools import wraps
from flask import request, jsonify

SUPABASE_PROJECT_URL = "https://uvdgcajudjqizmkupzmr.supabase.co"
JWKS_URL = f"{SUPABASE_PROJECT_URL}/auth/v1/.well-known/jwks.json"
ISSUER = f"{SUPABASE_PROJECT_URL}/auth/v1"

jwks_client = PyJWKClient(JWKS_URL)

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401

        token = auth_header.split(" ", 1)[1]

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token).key

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["ES256"],
                audience="authenticated",
                issuer=ISSUER,
            )
        except Exception as e:
            print("JWT verification error:", repr(e))
            return jsonify({"error": "Invalid token"}), 401

        user = {
            "id": payload["sub"],
            "email": payload.get("email"),
        }

        return fn(user, *args, **kwargs)

    return wrapper
