# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir uv
RUN uv pip install --no-cache-dir -r requirements.txt --system

# Copy application code
COPY server.py .
COPY ai_client.py .

# Expose port
EXPOSE 5000

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:3030", "--workers", "4", "--timeout", "120", "server:app"]