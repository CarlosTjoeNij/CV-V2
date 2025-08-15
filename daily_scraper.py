# daily_scraper.py
import io
import datetime
import pandas as pd
from google.cloud import storage
from scraper_core import scrape_all_jobs  # <- jouw bestaande functie

BUCKET_NAME = "scrapes_cvmatcher"

def upload_to_gcs(df: pd.DataFrame):
    """Upload DataFrame naar GCS als Parquet-bestand."""
    today_str = datetime.date.today().isoformat()
    filename = f"jobs_{today_str}.parquet"

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)

    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    blob.upload_from_file(buffer, content_type="application/octet-stream")
    print(f"✅ Uploaded {len(df)} rows to gs://{BUCKET_NAME}/{filename}")

def main():
    print("🚀 Start scraping job...")
    df = scrape_all_jobs()  # Komt uit scraper_core

    if df.empty:
        print("⚠️ Geen vacatures gevonden. Upload wordt overgeslagen.")
        return

    upload_to_gcs(df)
    print("🎉 Daily scrape completed!")

if __name__ == "__main__":
    main()
