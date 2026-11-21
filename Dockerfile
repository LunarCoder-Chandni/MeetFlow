FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && mkdir /data
COPY backend/app.py ./backend/app.py
COPY backend/auth.py ./backend/auth.py
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV DATABASE_PATH=/data/meetflow.db PORT=5001
WORKDIR /app/backend
EXPOSE 5001
CMD ["sh", "-c", "exec waitress-serve --listen=0.0.0.0:${PORT} --threads=8 app:app"]
