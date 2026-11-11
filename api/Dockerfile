FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip uninstall -y pip setuptools wheel

COPY src /app/src
COPY api /app/api

ENV PYTHONPATH=/app/src:/app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

USER appuser
