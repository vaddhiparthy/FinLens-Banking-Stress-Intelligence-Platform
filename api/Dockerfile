FROM python:3.13.18-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

WORKDIR /app

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser
COPY api/requirements.txt /app/requirements.txt
RUN python -c 'import urllib.request,hashlib,pathlib;files=[{'"'"'url'"'"': '"'"'https://apt.postgresql.org/pub/repos/apt/pool/main/p/postgresql-18/libpq5_18.6-1.pgdg13+2_amd64.deb'"'"', '"'"'sha256'"'"': '"'"'c6cc459bb499db4697686533e50bf5943f7e7d6929c04ef55eec184d5436859b'"'"', '"'"'path'"'"': '"'"'/tmp/libpq5.deb'"'"'}, {'"'"'url'"'"': '"'"'https://apt.postgresql.org/pub/repos/apt/pool/main/p/postgresql-18/libpq-dev_18.6-1.pgdg13+2_amd64.deb'"'"', '"'"'sha256'"'"': '"'"'b2add61e7fe0e9328140de456a85c96737b517f9cf62b44fd88e86aa2b765f29'"'"', '"'"'path'"'"': '"'"'/tmp/libpq-dev.deb'"'"'}];[(pathlib.Path(f["path"]).write_bytes(urllib.request.urlopen(f["url"],timeout=60).read())) for f in files];assert all(hashlib.sha256(pathlib.Path(f["path"]).read_bytes()).hexdigest()==f["sha256"] for f in files),"PostgreSQL package SHA256 mismatch"' \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gcc libc6-dev zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 /tmp/libpq5.deb /tmp/libpq-dev.deb \
    && apt-mark manual libpq5 \
    && pip install --no-cache-dir --no-deps -r /app/requirements.txt \
    && pip uninstall -y pip setuptools wheel \
    && apt-get purge -y --auto-remove gcc libc6-dev libpq-dev \
    && rm -f /tmp/libpq5.deb /tmp/libpq-dev.deb \
    && rm -rf /var/lib/apt/lists/*

COPY src /app/src
COPY api /app/api

ENV PYTHONPATH=/app/src:/app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

USER appuser
