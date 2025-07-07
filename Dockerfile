FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl unzip xvfb wget gnupg \
    libnss3 libgconf-2-4 libxi6 libgl1 libxrender1 libxtst6 fonts-liberation libappindicator3-1 \
    chromium chromium-driver

# Download juiste chromedriver versie
ENV CHROMEDRIVER_VERSION=138.0.7204.96
RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Set environment variables
ENV PORT 8080
ENV PYTHONUNBUFFERED True
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS false

# Install Python requirements
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . /app
WORKDIR /app

# Expose correct port
EXPOSE $PORT

# Streamlit configuration
ENV STREAMLIT_SERVER_HEADLESS true
ENV STREAMLIT_SERVER_PORT $PORT
ENV STREAMLIT_SERVER_ENABLECORS false
ENV STREAMLIT_SERVER_ENABLEXSRC false
ENV STREAMLIT_SERVER_BASE_URL_PATH ""

# Run Streamlit
CMD ["streamlit", "run", "app.py"]
