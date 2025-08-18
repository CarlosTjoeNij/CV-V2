FROM python:3.10-slim

# Install dependencies voor headless browser
RUN apt-get update && apt-get install -y \
    curl unzip wget gnupg xvfb \
    libnss3 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxtst6 \
    libxrandr2 libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libgbm1 libgtk-3-0 libxshmfence1 \
    fonts-liberation xdg-utils \
    && rm -rf /var/lib/apt/lists/*
    

# Install Chrome voor testing (versie 138+) inclusief driver
RUN CHROME_VERSION=138.0.7258.127 && \
    wget -O /tmp/chrome-for-testing.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chrome-linux64.zip && \
    unzip /tmp/chrome-for-testing.zip -d /opt/ && \
    mv /opt/chrome-linux64 /opt/chrome && \
    rm /tmp/chrome-for-testing.zip

# Chromedriver
RUN wget -O /tmp/chromedriver_linux64.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver_linux64.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver_linux64.zip /usr/local/bin/chromedriver-linux64

# Python en app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . /app
WORKDIR /app

ENV PORT 8080
EXPOSE $PORT
CMD ["streamlit", "run", "app.py"]
