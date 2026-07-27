# ============================================================
# EAKAP Enterprise Console — Dockerfile
# Step 10: Streamlit UI + Docker packaging
# ============================================================

FROM python:3.10-slim

# ---------- metadata ----------
LABEL maintainer="Kartheek Jagarlamudi"
LABEL description="Enterprise AI Knowledge & Analytics Platform — Streamlit Console"
LABEL version="1.1"

# ---------- environment ----------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ---------- working directory ----------
WORKDIR /app

# ---------- system dependencies ----------
# grpcio (chromadb) requires build tools on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---------- Python dependencies ----------
# Copy dependency manifests first to benefit from Docker layer caching
COPY requirements.txt        ./requirements.txt
COPY requirements-ui.txt     ./requirements-ui.txt

# Install UI requirements (which pull in base requirements via -r)
RUN pip install --no-cache-dir -r requirements-ui.txt

# ---------- application source ----------
COPY . .

# ---------- runtime directories & non-root user ----------
RUN mkdir -p data/raw_documents data/vector_store/chromadb logs \
    && useradd -m -u 1000 eakapuser \
    && chown -R eakapuser:eakapuser /app

# ---------- Streamlit configuration ----------
COPY .streamlit /app/.streamlit

# ---------- switch to non-root user ----------
USER eakapuser

# ---------- exposed port ----------
EXPOSE 8501

# ---------- health check ----------
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ---------- entrypoint ----------
CMD ["streamlit", "run", "src/app/ui/main_app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
