# scraper_core.py
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import streamlit as st  # Voor secrets

from platformen.striive import scrape_striive
from platformen.flextender import scrape_flextender
from platformen.yacht import scrape_yacht

# --- COMBINED SCRAPE ---
def scrape_all_jobs():
    start_time = time.time()
    all_dfs = []

    # Striive
    try:
        df_striive = scrape_striive()
        all_dfs.append(df_striive)
    except Exception as e:
        print(f"❌ Fout tijdens scraping Striive: {e}")

    # Flextender
    try:
        df_flex = scrape_flextender()
        all_dfs.append(df_flex)
    except Exception as e:
        print(f"❌ Fout tijdens scraping Flextender: {e}")

    # Yacht
    try:
        df_yacht = scrape_yacht()
        all_dfs.append(df_yacht)
    except Exception as e:
        print(f"❌ Fout tijdens scraping Yacht: {e}")

    if all_dfs:
        df_combined = pd.concat(all_dfs, ignore_index=True)
    else:
        df_combined = pd.DataFrame()

    duration = time.time() - start_time
    print(f"Scraping voltooid in {duration/60:.1f} minuten")
    return df_combined
