FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

EXPOSE 8080

# Use shell form so $PORT env var is expanded at runtime
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
