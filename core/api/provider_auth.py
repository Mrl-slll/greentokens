"""Provider-only accounts. Passwords and bearer tokens are never stored in plain text."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from ipaddress import ip_address
from threading import BoundedSemaphore

from fastapi import HTTPException, Request, Response
from pydantic import Field, SecretStr, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from core.api.schemas import StrictModel
from core.database.models import AuthThrottle, Organization, ProviderLogin, ProviderSession, User, now, uid

# The app keeps the session in the OS keychain and swaps it for a fresh one on every launch
# (POST /refresh), so a computer that is used at least monthly stays signed in.
SESSION_LIFETIME = timedelta(days=30)
DEVICE_ID = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
HASH_SLOTS = BoundedSemaphore(2)


class Credentials(StrictModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9][a-z0-9_-]{2,31}$")
    password: SecretStr
    device_id: str = DEVICE_ID

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        # No length or style rules (owner's choice). Only: not empty, and a high technical ceiling so a
        # huge password can't tie up the server's password hashing.
        if not 1 <= len(value.get_secret_value()) <= 1024:
            raise ValueError("Enter a password")
        return value


class RefreshBody(StrictModel):
    device_id: str = DEVICE_ID


def password_digest(password, salt):
    # scrypt from Python's standard library: a random salt and ~32 MiB per hash.
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=3,
                          maxmem=64 * 1024 * 1024, dklen=32).hex()


def hash_password(password):
    salt = secrets.token_hex(16)
    return f"scrypt-v1${salt}${password_digest(password, salt)}"


def verify_password(password, encoded):
    scheme, salt, expected = encoded.split("$")
    return scheme == "scrypt-v1" and hmac.compare_digest(password_digest(password, salt), expected)


def session_user(db, digest):
    session = db.get(ProviderSession, digest)
    if session is None or session.expires_at <= now():
        return None
    user = db.get(User, session.user_id)
    if user is None or user.role != "provider":
        return None
    user.auth_device_id = session.device_id
    return user


def throttle(sessions, scope, limit, seconds=60):
    """Database counters also work across restarts and multiple API workers."""
    digest = hashlib.sha256(scope.encode()).hexdigest()
    for retry in range(2):
        try:
            with sessions.begin() as db:
                row = db.scalar(select(AuthThrottle).where(AuthThrottle.scope_hash == digest).with_for_update())
                if row is None:
                    db.add(AuthThrottle(scope_hash=digest, window_start=now(), attempts=1))
                elif row.window_start <= now() - timedelta(seconds=seconds):
                    row.window_start, row.attempts = now(), 1
                elif row.attempts >= limit:
                    raise HTTPException(429, "Too many attempts. Please wait and try again.", headers={"Retry-After": str(seconds)})
                else:
                    row.attempts += 1
            return
        except IntegrityError:
            if retry:
                raise HTTPException(429, "Please wait and try again.") from None


def client_address(request):
    # The API is loopback-only behind cloudflared. Only that proxy supplies this header.
    address = request.headers.get("cf-connecting-ip", request.client.host if request.client else "unknown")
    try:
        return str(ip_address(address))
    except ValueError:
        return "local"


def new_session(db, user_id, device_id):
    token = "gt_" + secrets.token_urlsafe(32)
    expires = now() + SESSION_LIFETIME
    db.add(ProviderSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                           device_id=device_id, expires_at=expires))
    return token, expires


def session_reply(response, token, expires, username, device_id):
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat() + "Z",
            "account": {"displayName": username, "deviceId": device_id}}


def add_auth_routes(app, sessions):
    def authenticate(body, request, response, signup):
        address = client_address(request)
        throttle(sessions, "auth:global", 120)
        throttle(sessions, "auth:ip:" + address, 20)
        throttle(sessions, "auth:user:" + body.username, 10)
        if signup:
            throttle(sessions, "signup:ip:" + address, 5, 3600)
        if not HASH_SLOTS.acquire(blocking=False):
            raise HTTPException(429, "Sign-in is busy. Please try again shortly.", headers={"Retry-After": "2"})
        try:
            password = body.password.get_secret_value()
            with sessions.begin() as db:
                login = db.get(ProviderLogin, body.username)
                if signup:
                    if login is not None:
                        raise HTTPException(409, "That username is unavailable. Choose another or sign in.")
                    org_id, user_id = uid(), uid()
                    db.add(Organization(id=org_id, name=body.username))
                    db.flush()
                    db.add(User(id=user_id, organization_id=org_id, role="provider"))
                    db.flush()
                    login = ProviderLogin(username=body.username, user_id=user_id, password_hash=hash_password(password))
                    db.add(login)
                else:
                    # Missing accounts take the same expensive hash path as a wrong password.
                    encoded = login.password_hash if login else "scrypt-v1$" + "00" * 16 + "$" + "00" * 32
                    valid = verify_password(password, encoded)
                    if not valid or login is None or db.get(User, login.user_id).role != "provider":
                        raise HTTPException(401, "Incorrect username or password.")
                db.execute(delete(ProviderSession).where(ProviderSession.expires_at <= now()))
                # Re-signing in on a device replaces its old session; other computers stay signed in.
                db.execute(delete(ProviderSession).where(ProviderSession.user_id == login.user_id,
                                                         ProviderSession.device_id == body.device_id))
                token, expires = new_session(db, login.user_id, body.device_id)
            return session_reply(response, token, expires, body.username, body.device_id)
        except IntegrityError:
            raise HTTPException(409, "Account changed during sign-in. Please try again.") from None
        finally:
            HASH_SLOTS.release()

    @app.post("/v1/provider/auth/signup", status_code=201)
    def signup(body: Credentials, request: Request, response: Response):
        return authenticate(body, request, response, True)

    @app.post("/v1/provider/auth/login")
    def login(body: Credentials, request: Request, response: Response):
        return authenticate(body, request, response, False)

    @app.post("/v1/provider/auth/refresh")
    def refresh(body: RefreshBody, request: Request, response: Response):
        """Swap a valid session for a new one on the same device; the old token stops working."""
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(401, "Sign in first.")
        throttle(sessions, "refresh:ip:" + client_address(request), 30)
        digest = hashlib.sha256(auth[7:].encode()).hexdigest()
        with sessions.begin() as db:
            session = db.get(ProviderSession, digest)
            if session is None or session.expires_at <= now() or session.device_id != body.device_id:
                raise HTTPException(401, "Sign in again.")
            user = db.get(User, session.user_id)
            login = db.scalar(select(ProviderLogin).where(ProviderLogin.user_id == session.user_id))
            if user is None or user.role != "provider" or login is None:
                raise HTTPException(401, "Sign in again.")
            db.delete(session)
            token, expires = new_session(db, user.id, body.device_id)
        return session_reply(response, token, expires, login.username, body.device_id)

    @app.post("/v1/provider/auth/logout", status_code=204)
    def logout(request: Request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(401, "Sign in first.")
        with sessions.begin() as db:
            db.execute(delete(ProviderSession).where(ProviderSession.token_hash == hashlib.sha256(auth[7:].encode()).hexdigest()))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})
