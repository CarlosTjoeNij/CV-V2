FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl unzip xvfb wget gnupg \
    libnss3 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxtst6 \
    libnss3 libxrandr2 libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libgbm1 libgtk-3-0 libxshmfence1

# Install Chromium v138
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Install matching ChromeDriver v138
RUN CHROMEDRIVER_VERSION=138.0.7204.92 && \
    wget -O /tmp/chromedriver_linux64.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver_linux64.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver_linux64.zip /usr/local/bin/chromedriver-linux64

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
