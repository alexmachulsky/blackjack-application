# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Cache npm install layer separately from source code
COPY package*.json ./
RUN npm ci --prefer-offline

# Copy source and build for production
COPY . .
RUN npm run build

# ── Stage 2: serve ────────────────────────────────────────────────────────────
# Final image is a lean Nginx image — no Node.js in production
FROM nginx:1.27-alpine AS production

# Upgrade all Alpine packages to pick up latest security patches.
# Keeps the image clean of known CVEs at build time.
# Configure nginx to run as non-root (pid + temp dirs writable by nginx user).
RUN apk upgrade --no-cache && \
    mkdir -p /tmp/nginx && \
    chown -R nginx:nginx /tmp/nginx /var/cache/nginx /usr/share/nginx/html && \
    sed -i 's|/var/run/nginx.pid|/tmp/nginx/nginx.pid|' /etc/nginx/nginx.conf

# Copy built static assets from builder stage
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Nginx config: route all requests through index.html for SPA routing
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

USER nginx
EXPOSE 8080

# Bake the commit SHA into the image — guarantees a unique digest on every build
ARG BUILD_SHA=unknown
ENV BUILD_SHA=${BUILD_SHA}

CMD ["nginx", "-g", "daemon off;"]
