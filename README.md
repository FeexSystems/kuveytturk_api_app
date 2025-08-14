# 


## Setup

1. Update backend/.env with your credentials.

2. Add your private key to backend/keys/kt_private_key.pem.

3. Backend: cd backend && pip install -r requirements.txt && python app.py

4. Frontend: cd frontend && npm install && npm run dev

## Deploy to Render (single service)

1. Build frontend into backend
   - From project root:
     - `cd frontend && npm ci && npm run build`
     - This outputs to `backend/frontend_dist/`.

2. Configure environment variables (Render → Web Service → Environment)
   - SESSION_SECRET: random hex
   - KUVEYTTURK_AUTH_BASE: provider auth base URL
   - KUVEYTTURK_API_BASE: provider API base URL
   - CLIENT_ID, CLIENT_SECRET: issued by provider
   - SCOPES: space-separated scopes
   - REDIRECT_URI: https://<your-service>.onrender.com/auth/callback
   - PRIVATE_KEY_PEM: paste PEM content of your RSA private key (or use Secret File and set PRIVATE_KEY_PATH)
   - ALLOWED_ORIGINS: comma-separated origins (e.g., https://<your-site>.netlify.app, http://localhost:5173)

3. Create Render Web Service
   - Root directory: repository root
   - Build Command: `pip install -r backend/requirements.txt && cd frontend && npm ci && npm run build`
   - Start Command: `python backend/app.py`
   - Auto-detects `PORT`

4. Register redirect URI at the provider
   - https://<your-service>.onrender.com/auth/callback

5. Frontend configuration
   - For local dev: set `VITE_API_BASE=http://localhost:4000`
   - For production (single service): do not set `VITE_API_BASE` so calls use same-origin

Access at http://localhost:5173

Notes:
- Adjust API paths, signature logic, and scopes based on Kuveyt T�rk's latest Swagger/docs.
- This uses FastAPI for backend, which integrates seamlessly with OAuth flows and request signing in Python.
- For production, secure sessions, add token refresh, and deploy properly.
