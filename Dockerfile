# ================================
# Stage 1: Frontend build
# ================================
FROM node:20-alpine AS frontend
WORKDIR /app

# Copy only frontend to leverage Docker layer caching
COPY frontend ./frontend
RUN cd frontend \
  && npm ci \
  && npm run build

# ================================
# Stage 2: Backend runtime
# ================================
FROM python:3.11-slim
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy backend code
COPY backend ./backend

# Copy built frontend into backend/frontend_dist
COPY --from=frontend /app/frontend/dist ./backend/frontend_dist

# Install Python dependencies
RUN pip install -r backend/requirements.txt

# Expose port (Render will use its own $PORT value)
ENV PORT=4000

# Start FastAPI app with Uvicorn in production mode
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "4000", "--workers", "1"]
