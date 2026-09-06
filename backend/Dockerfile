FROM python:3.11-slim

WORKDIR /app/backend

# Install dependencies first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install frontend deps separately (builder, not runtime)
# Copy source
COPY app/ ./app/
COPY extraction/ ./extraction/

# Create data dirs
RUN mkdir -p /app/data /app/data/images && chmod 755 /app/data

ENV PYTHONPATH=/app/backend
ENV DATABASE_URL=sqlite+aiosqlite:///data/ccna.db

EXPOSE 8000

# gunicorn with 1 worker for 1GB RAM
CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--access-logfile", "-", "--error-logfile", "-"]
