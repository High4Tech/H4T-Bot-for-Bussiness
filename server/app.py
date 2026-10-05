"""Local product service backed by PostgreSQL, with a scoped SQLite test adapter."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from pydantic import BaseModel, Field
from server.database import Database, INTEGRITY_ERRORS
from server.product import install_product_routes
from starlette.middleware.trustedhost import TrustedHostMiddleware

CHANNELS = ("web", "whatsapp", "facebook", "wordpress", "shopify")
COOKIE = "h4t_session"
ORIGINS = {"http://127.0.0.1:5173", "http://localhost:5173"}

class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)

class Registration(Credentials):
    name: str = Field(min_length=2, max_length=80)
    company: str = Field(min_length=2, max_length=80)

class ChannelSettings(BaseModel):
    enabled: bool = False
    provider_id: str = Field(default="", max_length=80, pattern=r"^[a-zA-Z0-9_-]*$")

class Appearance(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    botName: str = Field(min_length=1, max_length=80)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    welcome: str = Field(min_length=1, max_length=180)
    description: str = Field(max_length=180)
    avatar: str = Field(max_length=750000)
    logo: str = Field(max_length=750000)
    questions: list[str] = Field(max_length=3)
    leadForm: bool
    position: str = Field(pattern=r"^(left|right)$")
    dark: bool

def default_appearance(company: str, bot_id: str):
    return dict(id=bot_id, name=company, botName=f"{company} Assistant", color="#F97328",
                welcome="Hello! How can we help you today?", description="A little help, right when you need it.",
                avatar="/assets/brand/mascots.svg", logo="/assets/brand/wordmark.png",
                questions=["Explore services", "How does this demo work?", "Talk to a person"],
                leadForm=False, position="right", dark=False)

def normalize_email(value):
    value = value.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise HTTPException(422, "Enter a valid email address.")
    return value

def password_hash(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f"scrypt:{salt}:{digest}"

def password_matches(password: str, stored: str):
    try:
        return hmac.compare_digest(password_hash(password, stored.split(":")[1]), stored)
    except (ValueError, IndexError):
        return False

def create_app(db_path: Path | str | None = None, db_config=None):
    app = FastAPI(title="H4T Bot local product API", docs_url=None, redoc_url=None, openapi_url=None)
    database = Database(db_path, config=db_config)
    db = database.connect
    app.state.db = db
    app.state.database = database
    attempts = defaultdict(deque)
    dummy_hash = password_hash("unused-local-auth-comparison")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def local_protection(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.url.path.startswith("/api/webhooks/"):
            if request.headers.get("origin") not in ORIGINS:
                return Response("Untrusted request origin", status_code=403)
        body_limit = 10*1024*1024 if request.url.path == "/api/company/sources/upload" else 1600000
        try:
            if int(request.headers.get("content-length", "0")) > body_limit:
                return Response("Request too large", status_code=413)
        except ValueError:
            return Response("Invalid content length", status_code=400)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            # Bound actual streamed bytes as well as Content-Length (chunked clients).
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > body_limit:
                    return Response("Request too large", status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def current_user(request: Request):
        token = request.cookies.get(COOKIE, "")
        with db() as conn:
            user = conn.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.hash=? AND s.expires>?",
                                (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not user:
            raise HTTPException(401, "Sign in to your workspace.")
        return dict(user)

    def company_user(user=Depends(current_user)):
        if user["role"] != "owner" or not user["company_id"]:
            raise HTTPException(403, "A customer workspace account is required.")
        return user

    def platform_user(user=Depends(current_user)):
        if user["role"] != "platform_admin":
            raise HTTPException(403, "Platform access is restricted.")
        return user

    def public_user(user):
        with db() as conn:
            company = conn.execute("SELECT name,bot_id FROM companies WHERE id=?", (user["company_id"],)).fetchone()
        return dict(id=user["id"], name=user["name"], email=user["email"], role=user["role"],
                    companyId=user["company_id"], companyName=company["name"] if company else None,
                    botId=company["bot_id"] if company else None)

    def create_session(user_id, response):
        token = secrets.token_urlsafe(32)
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE expires<=?", (time.time(),))
            conn.execute("INSERT INTO sessions VALUES(?,?,?)",
                         (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time() + 8 * 3600))
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=8 * 3600, path="/api", secure=False)

    def limit_auth(request, email):
        host = request.client.host if request.client else "local"
        keys = [(host, "all"), (host, hashlib.sha256(email.encode()).hexdigest())]
        now = time.time()
        for key, maximum in zip(keys, (60, 10)):
            q = attempts[key]
            while q and q[0] < now - 300:
                q.popleft()
            if len(q) >= maximum:
                raise HTTPException(429, "Too many attempts. Try again in five minutes.")
            q.append(now)
        if len(attempts) > 2000:
            for k in list(attempts):
                if not attempts[k] or attempts[k][-1] < now - 300:
                    attempts.pop(k, None)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "runtime": "local", "ai": "deferred", "database": database.health()}

    @app.post("/api/auth/register", status_code=201)
    def register(data: Registration, request: Request, response: Response):
        email = normalize_email(data.email)
        limit_auth(request, email)
        uid, cid, bot_id = secrets.token_hex(16), secrets.token_hex(16), secrets.token_hex(16)
        if not data.name.strip() or not data.company.strip():
            raise HTTPException(422, "Name and company are required.")
        appearance = default_appearance(data.company.strip(), bot_id)
        try:
            with db() as conn:
                conn.execute("INSERT INTO companies VALUES(?,?,?,?,?)", (cid, data.company.strip(), bot_id, json.dumps(appearance), time.time()))
                conn.execute("INSERT INTO users VALUES(?,?,?,?,?,?)", (uid, email, data.name.strip(), password_hash(data.password), cid, "owner"))
                conn.execute("INSERT INTO subscriptions VALUES(?,?,?)", (cid,"Starter",time.time()))
                for channel in CHANNELS:
                    conn.execute("INSERT INTO channels VALUES(?,?,?,?)", (cid, channel, 1 if channel == "web" else 0, ""))
        except INTEGRITY_ERRORS:
            raise HTTPException(409, "This email is already registered.")
        create_session(uid, response)
        return public_user(dict(id=uid, name=data.name.strip(), email=email, role="owner", company_id=cid))

    @app.post("/api/auth/login")
    def login(data: Credentials, request: Request, response: Response):
        email = normalize_email(data.email)
        limit_auth(request, email)
        with db() as conn:
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        stored = user["password_hash"] if user else dummy_hash
        if not password_matches(data.password, stored) or not user:
            raise HTTPException(401, "Email or password is incorrect.")
        create_session(user["id"], response)
        return public_user(dict(user))

    @app.get("/api/auth/me")
    def me(user=Depends(current_user)):
        return public_user(user)

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request, response: Response):
        token = request.cookies.get(COOKIE, "")
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
        response.delete_cookie(COOKIE, path="/api")

    @app.get("/api/company")
    def company(user=Depends(company_user)):
        with db(company=user["company_id"]) as conn:
            row = conn.execute("SELECT bot_id,appearance FROM companies WHERE id=?", (user["company_id"],)).fetchone()
        return {"botId": row["bot_id"], "appearance": json.loads(row["appearance"])}

    @app.put("/api/company/appearance")
    def appearance(data: Appearance, user=Depends(company_user)):
        for image in (data.avatar, data.logo):
            if image and not (image.startswith("/assets/brand/") or re.fullmatch(r"data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+", image)):
                raise HTTPException(422, "Choose a local PNG, JPEG or WebP asset.")
        if any(not q.strip() or len(q) > 100 for q in data.questions):
            raise HTTPException(422, "Questions must be 1–100 characters.")
        with db(company=user["company_id"]) as conn:
            bot_id = conn.execute("SELECT bot_id FROM companies WHERE id=?", (user["company_id"],)).fetchone()["bot_id"]
            value = {**data.model_dump(), "id": bot_id}
            conn.execute("UPDATE companies SET name=?,appearance=? WHERE id=?", (data.name, json.dumps(value), user["company_id"]))
        return value

    @app.get("/api/embed/{bot_id}")
    def embed(bot_id: str):
        with db() as conn:
            row = conn.execute("SELECT appearance FROM public_assistant_appearance WHERE bot_id=?", (bot_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Assistant not found.")
        return {"appearance": json.loads(row["appearance"]), "mode": "scripted-local-preview"}

    @app.get("/api/company/channels")
    def channels(user=Depends(company_user)):
        with db(company=user["company_id"]) as conn:
            rows = conn.execute("SELECT channel,enabled,provider_id FROM channels WHERE company_id=?", (user["company_id"],)).fetchall()
        return [{"channel": r["channel"], "enabled": bool(r["enabled"]), "providerId": r["provider_id"],
                 "status": "Setup saved" if r["enabled"] else "Not configured",
                 "credentialsReady": bool(os.environ.get("H4T_META_APP_SECRET") and os.environ.get("H4T_META_VERIFY_TOKEN")) if r["channel"] in ("whatsapp", "facebook") else True} for r in rows]

    @app.put("/api/company/channels/{channel}")
    def configure_channel(channel: str, data: ChannelSettings, user=Depends(company_user)):
        if channel not in CHANNELS:
            raise HTTPException(404, "Unknown channel.")
        if channel in ("whatsapp", "facebook") and data.enabled and not data.provider_id:
            raise HTTPException(422, "Enter your phone-number ID or Page ID.")
        try:
            with db(company=user["company_id"]) as conn:
                conn.execute("UPDATE channels SET enabled=?,provider_id=? WHERE company_id=? AND channel=?",
                             (int(data.enabled), data.provider_id, user["company_id"], channel))
        except INTEGRITY_ERRORS:
            raise HTTPException(409, "This provider account is already assigned to another workspace.")
        return {"status": "Setup saved; live delivery is not verified", "channel": channel}

    @app.get("/api/company/channel-events")
    def events(user=Depends(company_user)):
        with db(company=user["company_id"]) as conn:
            rows = conn.execute("SELECT id,channel,created FROM channel_events WHERE company_id=? ORDER BY created DESC LIMIT 30", (user["company_id"],)).fetchall()
        return [dict(r) for r in rows]

    @app.get("/api/webhooks/{channel}")
    def verify_webhook(channel: str, request: Request):
        expected = os.environ.get("H4T_META_VERIFY_TOKEN", "")
        q = request.query_params
        if channel not in ("whatsapp", "facebook") or not expected:
            raise HTTPException(503, "Meta webhook credentials are not configured.")
        if q.get("hub.mode") != "subscribe" or not hmac.compare_digest(q.get("hub.verify_token", ""), expected):
            raise HTTPException(403, "Webhook verification failed.")
        return Response(q.get("hub.challenge", ""), media_type="text/plain")

    @app.post("/api/webhooks/{channel}")
    async def receive_webhook(channel: str, request: Request):
        secret = os.environ.get("H4T_META_APP_SECRET", "")
        if channel not in ("whatsapp", "facebook") or not secret:
            raise HTTPException(503, "Meta webhook credentials are not configured.")
        body = await request.body()
        if len(body) > 262144:
            raise HTTPException(413, "Webhook payload too large.")
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(request.headers.get("x-hub-signature-256", ""), signature):
            raise HTTPException(403, "Invalid webhook signature.")
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, "Invalid JSON.")
        if not isinstance(payload, dict) or not isinstance(payload.get("entry"), list):
            raise HTTPException(422, "Invalid webhook envelope.")
        accepted = 0
        with db(plane="ingest") as conn:
            for entry in payload["entry"][:100]:
                if not isinstance(entry, dict):
                    continue
                parts = entry.get("changes", []) if channel == "whatsapp" else [entry]
                if not isinstance(parts, list):
                    continue
                for part in parts[:100]:
                    if not isinstance(part, dict):
                        continue
                    value = part.get("value", {}) if channel == "whatsapp" else part
                    if not isinstance(value, dict):
                        continue
                    metadata = value.get("metadata", {})
                    provider = str(metadata.get("phone_number_id", "")) if channel == "whatsapp" and isinstance(metadata, dict) else (str(entry.get("id", "")) if channel == "facebook" else "")
                    destination = conn.execute("SELECT company_id FROM channels WHERE channel=? AND provider_id=? AND provider_id!='' AND enabled=1", (channel, provider)).fetchone()
                    if destination:
                        event_id = hashlib.sha256((channel + provider + json.dumps(value, sort_keys=True)).encode()).hexdigest()
                        cursor = conn.execute("INSERT INTO channel_events VALUES(?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                                              (event_id, destination["company_id"], channel, json.dumps(value), time.time()))
                        accepted += cursor.rowcount
        return {"accepted": accepted, "replyDelivery": "deferred"}

    @app.get("/api/platform/companies")
    def platform_companies(user=Depends(platform_user)):
        with db(plane="platform") as conn:
            rows = conn.execute("SELECT id,name,bot_id,created,plan FROM platform_company_metadata ORDER BY created DESC").fetchall()
        # Deliberately exclude appearance, knowledge, profiles and event payloads.
        return [{"id": r["id"], "name": r["name"], "botId": r["bot_id"], "bots": 1,
                 "plan": r["plan"] + " · Demo", "status": "Local account", "answers": 0} for r in rows]

    install_product_routes(app, database, company_user)
    return app

app = create_app()
