FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home appuser
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY YTL_TrackA_Udyam_Digital_Data/ ./YTL_TrackA_Udyam_Digital_Data/
COPY --from=frontend /web/dist ./frontend/dist/
RUN mkdir -p runtime && chown appuser:appuser runtime
USER appuser
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/api/ready',timeout=3)"
CMD ["python","-m","uvicorn","backend.main:app","--host","0.0.0.0","--port","8010","--workers","1","--no-access-log","--no-proxy-headers"]
