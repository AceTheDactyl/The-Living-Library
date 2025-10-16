FROM python:3.11-slim

WORKDIR /app

COPY library_core /app/library_core
COPY scripts/bootstrap_living_library.sh /app/scripts/

RUN pip install --no-cache-dir fastapi uvicorn[standard] redis asyncpg

CMD ["uvicorn", "library_core.collab.server:app", "--host", "0.0.0.0", "--port", "8080"]
