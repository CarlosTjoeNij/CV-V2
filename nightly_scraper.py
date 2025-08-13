# nightly_scraper.py
from flask import Flask, request
import pandas as pd
from datetime import datetime
from io import BytesIO
from google.cloud import storage
from scraper_module import scrape_all_jobs

BUCKET_NAME = "scrapes_cvmatcher"
FILENAME_TEMPLATE = "vacatures/vacatures_{date}.parquet"

app = Flask(__name__)

def upload_to_gcs(df, bucket_name, destination_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    buffer = BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    blob.upload_from_file(buffer, content_type='application/octet-stream')
    print(f"✅ Bestand geüpload naar gs://{bucket_name}/{destination_blob_name}")

@app.route("/", methods=["POST"])
def run_scraper():
    print("🚀 Start scraping...")
    df = scrape_all_jobs()

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = FILENAME_TEMPLATE.format(date=today_str)

    upload_to_gcs(df, BUCKET_NAME, filename)
    return {"status": "success", "rows": len(df)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
