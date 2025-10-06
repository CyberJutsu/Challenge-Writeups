FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for healthchecks and SSL
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Make launcher executable
RUN chmod +x /app/start.sh

# Data directory for SQLite volume
RUN mkdir -p /data

EXPOSE 8000

CMD ["/app/start.sh"]
