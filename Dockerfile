# --- deps: compila as wheels (inclui sqlcipher3, que precisa de libsqlcipher-dev) ---
FROM python:3.11-slim-bookworm AS deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libsqlcipher-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt \
    && mkdir /staging && cp /usr/lib/*-linux-gnu/libsqlcipher.so.0* /staging/

# --- runtime: só o necessário para executar ---
FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
# runtime da lib sqlcipher (o -dev fica só no stage de deps)
COPY --from=deps /staging/ /usr/lib/
COPY --from=deps /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /data/documents \
    && chown -R app:app /data
WORKDIR /app
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["python", "manage.py", "runsecure", "0.0.0.0:8000"]
