# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:18-alpine AS builder

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
RUN apk upgrade --no-cache

# Copy built static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: route all requests through index.html for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Bake the commit SHA into the image — guarantees a unique digest on every build
ARG BUILD_SHA=unknown
ENV BUILD_SHA=${BUILD_SHA}

CMD ["nginx", "-g", "daemon off;"]
