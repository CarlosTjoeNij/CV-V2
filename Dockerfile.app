# Gebruik een lichte Python image
FROM python:3.10-slim

# Zet werkdirectory
WORKDIR /app

# Vereiste system dependencies installeren
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Vereisten installeren
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# App code kopiëren
COPY . /app

# Zet environment variables voor Streamlit
ENV PORT 8080
ENV PYTHONUNBUFFERED true
ENV STREAMLIT_SERVER_HEADLESS true
ENV STREAMLIT_SERVER_PORT $PORT
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS false
ENV STREAMLIT_SERVER_ENABLECORS false
ENV STREAMLIT_SERVER_ENABLEXSRC false
ENV STREAMLIT_SERVER_BASE_URL_PATH ""

# Expose de juiste poort
EXPOSE $PORT

# Start Streamlit app
CMD ["streamlit", "run", "app.py"]
