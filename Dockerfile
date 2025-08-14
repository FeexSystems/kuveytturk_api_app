# Multi-stage build: build React frontend, then run FastAPI backend

#############
# Stage 1: Frontend build
#############
FROM node:20-alpine AS frontend
WORKDIR /app

# Copy only frontend to leverage Docker layer caching
COPY frontend ./frontend
RUN cd frontend \
  && npm ci \
  && npm run build

#############
# Stage 2: Backend runtime
#############
FROM python:3.11-slim
WORKDIR /app

# System packages (lightweight; cryptography has wheels, so no heavy build deps needed)
RUN pip install --upgrade pip

# Copy backend
COPY backend ./backend
# Copy built frontend into backend/frontend_dist
COPY --from=frontend /app/frontend/dist ./backend/frontend_dist

# Install Python deps
RUN pip install -r backend/requirements.txt

# Expose port (Render provides PORT env; we read it in app)
ENV PORT=4000

# Start the app
CMD ["python", "backend/app.py"]


