FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY extraction/ ./extraction/

RUN mkdir -p /app/data /app/data/images

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:///data/ccna.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
