FROM python:3.11-slim

RUN useradd -m -u 1000 user

WORKDIR /app

COPY --chown=user backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user backend/app/ ./backend/app/
COPY --chown=user backend/extraction/ ./backend/extraction/
COPY --chown=user data/ ./data/

RUN mkdir -p /app/data /app/data/images && chown -R user:user /app/data

USER user

ENV HOME=/home/user
ENV PYTHONPATH=/app/backend
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/ccna.db

EXPOSE 7860

CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--access-logfile", "-", "--error-logfile", "-"]
