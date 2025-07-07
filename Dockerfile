# Gebruik officiële Python image
FROM python:3.11-slim

# Voorkom interactiviteit
ENV DEBIAN_FRONTEND=noninteractive

# Installatie van dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxrandr2 \
    libgtk-3-0 \
    libu2f-udev \
    libdrm2 \
    fonts-liberation \
    xdg-utils \
    chromium \
    chromium-driver \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Zet Chromium en chromedriver in PATH
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Installeer pip packages
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# SpaCy Nederlands model downloaden
RUN python -m spacy download nl_core_news_sm

# Voeg alles toe
COPY . /app
WORKDIR /app

# Streamlit config (maakt het openbaar voor Cloud Run)
ENV PORT 8080
EXPOSE 8080

CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
