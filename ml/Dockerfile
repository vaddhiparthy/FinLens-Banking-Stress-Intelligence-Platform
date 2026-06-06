# Capstone-2 ML serving image: containerizes finlens_ml.serve (FastAPI + SHAP), NOT the DE
# marts API in api/. Build from the repo root:
#   docker build -f ml/Dockerfile -t fulllens-ml-serve:latest .
#   docker run -p 8077:8077 fulllens-ml-serve:latest
# $0 / open-source base. NOTE: not built in the dev environment that authored this; it is a
# reproducible recipe verified by inspection, to be built where a Docker daemon is available.
FROM python:3.12-slim

WORKDIR /app

# system deps for lightgbm (libgomp)
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
COPY ml ./ml

RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" pydantic \
    lightgbm scikit-learn shap skops mlflow pandas numpy

ENV PYTHONPATH=/app:/app/src:/app/ml \
    OMP_NUM_THREADS=1

EXPOSE 8077

# readiness: GET /ready returns 503 until the model artifact is loaded
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8077/ready').status==200 else 1)"

CMD ["uvicorn", "finlens_ml.serve:app", "--host", "0.0.0.0", "--port", "8077"]
