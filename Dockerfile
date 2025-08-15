# Gebruik een lichte Python image
FROM python:3.11-slim

# Zet werkdirectory
WORKDIR /app

# Vereiste systeempakketten installeren
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Requirements installeren
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Code kopiëren
COPY . .

# Omgevingsvariabelen voor Streamlit
ENV PORT 8080
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=$PORT
ENV STREAMLIT_SERVER_ENABLECORS=false
ENV STREAMLIT_SERVER_ENABLEXSRC=false

# Poort openen
EXPOSE $PORT

# Start de Streamlit-app
CMD ["streamlit", "run", "app.py"]
