# Multi-stage build: use a Python builder to generate the static site using uv,
# then serve the resulting `dist` with nginx.

FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder
WORKDIR /app

# Copy project metadata and sources
COPY pyproject.toml uv.lock ./
COPY README.md README.md
COPY src/ ./src
COPY templates/ ./templates
COPY pages/ ./pages

# Sync dependencies (install dev deps) and build the static site into `dist`
RUN uv sync --dev
RUN uv run rabbithole build -p pages -d dist


FROM nginx:stable-alpine

# Copy built static files into nginx document root
COPY --from=builder /app/dist /usr/share/nginx/html

# Use our nginx config which ensures index handling and directory listing is on
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
