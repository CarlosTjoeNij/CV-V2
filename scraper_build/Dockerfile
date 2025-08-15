# Basis image
FROM python:3.11-slim

# Omgevingsvariabelen voor non-interactive apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PORT=8080
ENV CHROME_BIN=/usr/bin/chromium

# System dependencies + Chromium
RUN apt-get update && apt-get install -y \
    chromium \
    wget \
    curl \
    unzip \
    git \
    build-essential \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Werkomgeving
WORKDIR /app

# Kopieer requirements en installeer Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de scraper code en Flask app
COPY scraper_core.py .
COPY app.py .

# Start Flask server (Cloud Run healthcheck)
CMD ["python", "app.py"]
