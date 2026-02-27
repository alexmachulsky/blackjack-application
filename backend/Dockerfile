FROM python:3.11-slim

# Create a non-root user to run the application — never run as root in production
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Prevent Python from writing .pyc files — keeps read-only filesystems clean
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies before copying source — layer cached unless requirements change
COPY requirements.txt .
RUN pip install --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY ./app ./app

# Copy Alembic config + migration scripts (required by K8s init container)
COPY alembic.ini .
COPY migrations/ ./migrations/

# Hand ownership to the non-root user
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Bake the commit SHA into the image — guarantees a unique digest on every build
ARG BUILD_SHA=unknown
ENV BUILD_SHA=${BUILD_SHA}

# Production entrypoint — omit --reload (handled by docker-compose dev override)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
