FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build && npm prune --omit=dev

FROM node:20-bookworm-slim AS node-runtime

FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/include/node /usr/local/include/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY market_analyst ./market_analyst
COPY main.py backend.py README.md specs.md ./
COPY frontend ./frontend
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/start-container.sh /start-container.sh
RUN chmod +x /start-container.sh

EXPOSE 8080

CMD ["/start-container.sh"]
