# ---------- 1. Build the React frontend ----------
    FROM node:22-alpine AS frontend
    WORKDIR /frontend
    COPY frontend/package.json frontend/package-lock.json* ./
    RUN npm install
    COPY frontend/ ./
    RUN npm run build
    
    # ---------- 2. Python backend that also serves the built frontend ----------
    FROM python:3.12-slim
    
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        HF_HOME=/models
    
    WORKDIR /app/backend
    
    # CPU-only torch keeps the image ~2 GB smaller than the default CUDA build.
    COPY backend/requirements.txt .
    RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
     && pip install --no-cache-dir -r requirements.txt
    
    # Download the embedding model at build time so the container starts without internet access to Hugging Face.
    RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
    
    COPY backend/ .
    COPY --from=frontend /frontend/dist /app/frontend/dist
    
    ENV FRONTEND_DIST=/app/frontend/dist \
        INDEX_DIR=/data/index \
        COVERS_CACHE_FILE=/data/index/covers_cache.json \
        DATABASE_PATH=/data/booktag.db
    
    EXPOSE 8000
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]