"""
Stage 5 — Clerk Auth dependency.

Uses the official `clerk-backend-api` SDK with networkless PEM verification.
No per-request call to Clerk — the JWT is verified locally using the JWKS
public key stored in env (CLERK_JWKS_PUBLIC_KEY).

Usage:
    @router.get("/something")
    def my_route(user_id: str = Depends(require_auth)):
        ...
"""

from fastapi import HTTPException, Request
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

# Initialise SDK once at module level (reused across requests).
_clerk = Clerk(bearer_auth=settings.clerk_secret_key)


def require_auth(request: Request) -> str:
    """
    Verify the Clerk session token carried in the Authorization header
    and return the Clerk user_id (sub claim).

    Raises HTTP 401 if the token is missing, invalid, or expired.
    """
    try:
        jwt_key = settings.clerk_jwks_public_key.replace("\\n", "\n").strip()
        opts = AuthenticateRequestOptions(jwt_key=jwt_key)
        request_state = _clerk.authenticate_request(request, opts)
        if not request_state.is_signed_in and "TOKEN_INVALID_SIGNATURE" in str(getattr(request_state, "reason", "")):
            log.warning("Local PEM key signature failed, falling back to online Clerk JWKS verification...")
            request_state = _clerk.authenticate_request(request, AuthenticateRequestOptions())
    except Exception as exc:
        log.warning("Clerk authenticate_request raised: %s", exc)
        try:
            request_state = _clerk.authenticate_request(request, AuthenticateRequestOptions())
        except Exception as fallback_exc:
            raise HTTPException(status_code=401, detail="Unauthorized") from fallback_exc

    if not request_state.is_signed_in:
        reason = getattr(request_state, "reason", None) or "Unauthorized"
        log.warning("Request not signed in — reason: %s", reason)
        raise HTTPException(status_code=401, detail=str(reason))

    payload = getattr(request_state, "payload", None) or {}
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="No user ID in token")

    log.debug("Authenticated user_id=%s", user_id)
    return user_id
