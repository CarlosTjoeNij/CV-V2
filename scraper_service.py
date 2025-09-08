# scraper_service.py
from flask import Flask
import daily_scraper

app = Flask(__name__)

@app.route("/scrape", methods=["GET"])
def scrape():
    try:
        daily_scraper.main()  # roept de scraper aan
        return "Daily scrape completed ✅", 200
    except Exception as e:
        # Foutafhandeling zodat Cloud Run een foutstatus teruggeeft
        return f"Scraper failed: {str(e)}", 500

if __name__ == "__main__":
    # Cloud Run gebruikt poort 8080
    app.run(host="0.0.0.0", port=8080)
