# daily_scraper.py
import datetime
import pandas as pd
import io
from google.cloud import storage
from scraper_core import scrape_all_jobs

def upload_df_to_gcs(df: pd.DataFrame, bucket_name: str, blob_name: str):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(df.to_parquet(index=False), 'application/octet-stream')
    print(f"✅ Upload compleet: gs://{bucket_name}/{blob_name}")

if __name__ == "__main__":
    print("🚀 Start daily scrape...")
    df = scrape_all_jobs()
    today_str = datetime.date.today().isoformat()
    filename = f"jobs_{today_str}.parquet"
    upload_df_to_gcs(df, "scrapes_cvmatcher", filename)
    print("🏁 Scraping klaar.")
