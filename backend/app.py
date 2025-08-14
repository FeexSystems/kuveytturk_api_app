import os
import datetime
import base64
import secrets
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import uvicorn

load_dotenv()

app = FastAPI()

# ===== CORS CONFIG =====
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))

# ===== CONFIG VARIABLES =====
KUVEYTTURK_AUTH_BASE = os.getenv("KUVEYTTURK_AUTH_BASE")
KUVEYTTURK_API_BASE = os.getenv("KUVEYTTURK_API_BASE")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
PRIVATE_KEY_PEM = os.getenv("PRIVATE_KEY_PEM")

# ===== LOAD PRIVATE KEY =====
if PRIVATE_KEY_PATH and os.path.exists(PRIVATE_KEY_PATH):
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)
elif PRIVATE_KEY_PEM:
    private_key = serialization.load_pem_private_key(PRIVATE_KEY_PEM.encode(), password=None)
else:
    raise RuntimeError("Missing private key. Set PRIVATE_KEY_PATH or PRIVATE_KEY_PEM.")

# ===== SIGN PAYLOAD =====
def sign_payload(method, url_path, body=""):
    timestamp = datetime.datetime.utcnow().isoformat()
    canonical = "\n".join([method.upper(), url_path, timestamp, body])
    signature = private_key.sign(
        canonical.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_b64 = base64.b64encode(signature).decode()
    return timestamp, signature_b64

# ===== HEALTH CHECK & ROOT =====
@app.get("/")
def root():
    return {"status": "ok", "message": "API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ===== AUTH ROUTES =====
@app.get("/auth/login")
async def auth_login(request: Request):
    state = secrets.token_hex(16)
    request.session["oauth_state"] = state
    auth_url = (
        f"{KUVEYTTURK_AUTH_BASE}/oauth/authorize?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&state={state}"
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state/code")

    token_response = requests.post(
        f"{KUVEYTTURK_AUTH_BASE}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if not token_response.ok:
        return JSONResponse(status_code=400, content=token_response.json())

    tokens = token_response.json()
    request.session["tokens"] = tokens
    return RedirectResponse("http://localhost:5173/app")

# ===== TOKEN VALIDATION =====
async def ensure_token(request: Request):
    tokens = request.session.get("tokens")
    if not tokens:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tokens["access_token"]

# ===== API ROUTES =====
@app.get("/api/accounts")
async def get_accounts(request: Request):
    access_token = await ensure_token(request)
    url_path = "/api/ais/v2/accounts"
    timestamp, signature = sign_payload("GET", url_path)
    response = requests.get(
        f"{KUVEYTTURK_API_BASE}{url_path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Signature": signature,
            "X-Timestamp": timestamp,
        },
    )
    return JSONResponse(status_code=response.status_code, content=response.json())

@app.get("/api/accounts/{account_id}/transactions")
async def get_transactions(account_id: str, request: Request):
    access_token = await ensure_token(request)
    url_path = f"/api/ais/v2/accounts/{account_id}/transactions"
    timestamp, signature = sign_payload("GET", url_path)
    response = requests.get(
        f"{KUVEYTTURK_API_BASE}{url_path}?size=50",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Signature": signature,
            "X-Timestamp": timestamp,
        },
    )
    return JSONResponse(status_code=response.status_code, content=response.json())

@app.post("/api/payments/transfer")
async def post_transfer(request: Request):
    body = await request.json()
    access_token = await ensure_token(request)
    url_path = "/api/payments/v1/transfers"
    body_str = str(body)
    timestamp, signature = sign_payload("POST", url_path, body_str)
    response = requests.post(
        f"{KUVEYTTURK_API_BASE}{url_path}",
        json=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Signature": signature,
            "X-Timestamp": timestamp,
        },
    )
    return JSONResponse(status_code=response.status_code, content=response.json())

# ===== FRONTEND STATIC FILES =====
frontend_dist_path = os.path.join(os.path.dirname(__file__), "frontend_dist")
if os.path.isdir(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")

# ===== LOCAL DEV MODE =====
# This block runs only when you do: python backend/app.py
if __name__ == "__main__":
    port = int(os.getenv("PORT", 4000))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=True)
