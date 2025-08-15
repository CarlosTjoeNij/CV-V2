from flask import Flask
import threading
import scraper_core  # je bestaande scraper

app = Flask(__name__)

# Start scraper in background thread
def run_scraper():
    scraper_core.main()  # zorg dat scraper_core een main() functie heeft

threading.Thread(target=run_scraper).start()

# Healthcheck endpoint
@app.route("/")
def index():
    return "Scraper running", 200

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)