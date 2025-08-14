import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import base64
import datetime
import secrets
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

app = FastAPI()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))

KUVEYTTURK_AUTH_BASE = os.getenv("KUVEYTTURK_AUTH_BASE")
KUVEYTTURK_API_BASE = os.getenv("KUVEYTTURK_API_BASE")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
PRIVATE_KEY_PEM = os.getenv("PRIVATE_KEY_PEM")

# Load private key (prefer path; fallback to PEM env)
if PRIVATE_KEY_PATH and os.path.exists(PRIVATE_KEY_PATH):
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )
elif PRIVATE_KEY_PEM:
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PEM.encode(),
        password=None,
    )
else:
    raise RuntimeError("Missing private key. Set PRIVATE_KEY_PATH or PRIVATE_KEY_PEM.")

# Helper: create required signature header (adapt to exact spec)
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

@app.get("/auth/login")
async def auth_login(request: Request):
    state = secrets.token_hex(16)
    request.session["oauth_state"] = state
    auth_url = f"{KUVEYTTURK_AUTH_BASE}/oauth/authorize?response_type=code" \
        f"&client_id={CLIENT_ID}" \
        f"&redirect_uri={REDIRECT_URI}" \
        f"&scope={SCOPES}" \
        f"&state={state}"
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

async def ensure_token(request: Request):
    tokens = request.session.get("tokens")
    if not tokens:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Add expiry check and refresh logic here if needed
    return tokens["access_token"]

@app.get("/api/accounts")
async def get_accounts(request: Request):
    access_token = await ensure_token(request)
    url_path = "/api/ais/v2/accounts"  # Adjust to actual path from Swagger
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
    body_str = str(body)  # Or json.dumps if needed
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 4000)))

# Serve built frontend when running under Uvicorn/ASGI servers
if os.path.isdir(os.path.join(os.path.dirname(__file__), "frontend_dist")):
    app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "frontend_dist"), html=True), name="frontend")
