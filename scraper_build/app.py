# scraper_build/app.py
from flask import Flask
import threading
import daily_scraper  # gebruik de main van daily_scraper

app = Flask(__name__)

# Start scraper in background thread
def run_scraper():
    daily_scraper.main()  # ← hier de main van daily_scraper

threading.Thread(target=run_scraper).start()

@app.route("/")
def index():
    return "Scraper running", 200

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
