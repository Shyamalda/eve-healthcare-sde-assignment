FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY README.md POSTMAN.md SUBMISSION_CHECKLIST.md pyproject.toml ./

EXPOSE 8000

CMD ["sh", "-c", "python scripts/seed.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
