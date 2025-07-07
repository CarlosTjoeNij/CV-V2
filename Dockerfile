# Gebruik een lichte Python base image
FROM python:3.11-slim

RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/117.0.5938.92/chromedriver_linux64.zip || (echo "Download failed" && ls -la /tmp && exit 1)

# Install systeemtools en Chrome (headless)
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    xdg-utils \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libxshmfence-dev \
    libgbm1 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Installeer benodigde tools
RUN apt-get update && apt-get install -y wget unzip curl

# Chrome installeren (versie 117)
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# ChromeDriver installeren (passend bij Chrome 117)
RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/117.0.5938.92/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip

# Werkomgeving instellen
WORKDIR /app

# Bestanden kopiëren
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Streamlit poort voor Railway
ENV PORT 8000

# Start de app
CMD ["streamlit", "run", "app.py", "--server.port=8000", "--server.enableCORS=false"]
