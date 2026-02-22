FROM python:3.11-slim

# Create a non-root user to run the application — never run as root in production
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Install dependencies before copying source — layer cached unless requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY ./app ./app

# Hand ownership to the non-root user
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Production entrypoint — omit --reload (handled by docker-compose dev override)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
