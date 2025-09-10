# --- Base image ---
FROM python:3.11-slim

# --- Werkdirectory ---
WORKDIR /app

# --- Systeemafhankelijkheden + Chrome dependencies ---
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg fonts-liberation libappindicator3-1 libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 lsb-release \
    xdg-utils build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Google Chrome installeren ---
RUN wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt install -y /tmp/google-chrome.deb \
    && rm /tmp/google-chrome.deb

# --- ChromeDriver installeren passend bij Chrome ---
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') && \
    echo "Chrome versie: $CHROME_VERSION" && \
    wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /usr/bin/ && \
    rm /tmp/chromedriver.zip && \
    chmod +x /usr/bin/chromedriver

# --- Python dependencies installeren ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- App code kopiëren ---
COPY . .

# --- Environment variables voor Cloud Run ---
ENV PORT=8080

# --- Run scraper ---
CMD ["python", "daily_scraper.py"]
