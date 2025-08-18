# 1. Basis image
FROM python:3.11-slim

# 2. Werkdirectory
WORKDIR /app

# 3. Systeemafhankelijkheden (optioneel, voor pandas/parquet)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements en installeer Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy app code
COPY . .

# 6. Streamlit configureren voor Cloud Run
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV PORT=8080

# 7. Container command
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
