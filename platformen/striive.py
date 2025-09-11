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

# Haal credentials op uit .streamlit/secrets.toml
STRIIVE_USER = st.secrets["striive"]["username"]
STRIIVE_PASS = st.secrets["striive"]["password"]
FLEX_USER = st.secrets["flextender"]["username"]
FLEX_PASS = st.secrets["flextender"]["password"]

# --- HELPER: Chrome driver voor Cloud Run ---
def get_chrome_driver(timeout=15):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")

    driver = webdriver.Chrome(options=chrome_options)  # Selenium Manager regelt driver
    driver.implicitly_wait(timeout)
    return driver


# --- SCRAPE STRIIVE ---
def scrape_striive():
    driver = get_chrome_driver()
    wait = WebDriverWait(driver, 15)
    try:
        driver.get("https://login.striive.com/")
        time.sleep(2)

        driver.find_element(By.ID, "email").send_keys(STRIIVE_USER)
        driver.find_element(By.ID, "password").send_keys(STRIIVE_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        opdrachten_link = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href, '/inbox')]//span[contains(text(), 'Opdrachten')]")
            )
        )
        opdrachten_link.click()
        print("✅ Inloggen op Striive gelukt")

        scroll_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.p-scroller")))
        vacature_links_dict = {}
        repeats = 0
        max_repeats = 5

        while repeats < max_repeats:
            job_elements = driver.find_elements(By.CSS_SELECTOR, "div.job-request-row")
            new_count = 0
            for div in job_elements:
                try:
                    title = div.find_element(By.CSS_SELECTOR, "[data-testid='listJobRequestTitle']").text.strip()
                    opdrachtgever = div.find_element(By.CSS_SELECTOR, "[data-testid='listClientName']").text.strip()
                    regio = div.find_element(By.CSS_SELECTOR, "[data-testid='listRegionName']").text.strip()
                    link = div.find_element(By.CSS_SELECTOR, "a[data-testid='jobRequestDetailLink']").get_attribute("href")
                    if link not in vacature_links_dict:
                        vacature_links_dict[link] = {
                            "Titel": title,
                            "Opdrachtgever": opdrachtgever,
                            "Regio": regio,
                            "Link": link,
                            "Bron": "Striive"
                        }
                        new_count += 1
                except:
                    continue

            repeats = repeats + 1 if new_count == 0 else 0
            driver.execute_script("arguments[0].scrollBy(0, 1000);", scroll_container)
            time.sleep(1.2)

        results = []
        for link, vacature in vacature_links_dict.items():
            try:
                driver.get(link)
                try:
                    desc_elem = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='jobRequestDescription']"))
                    )
                    beschrijving_html = desc_elem.get_attribute("innerHTML").strip()
                    soup = BeautifulSoup(beschrijving_html, "html.parser")
                    beschrijving_tekst = soup.get_text(separator="\n").strip()
                    vacature["Beschrijving"] = beschrijving_tekst
                except:
                    vacature["Beschrijving"] = ""
                results.append(vacature)
            except Exception as e:
                print(f"⚠️ Fout bij laden detailpagina: {link} - {e}")
                continue

        print(f"Striive - aantal vacatures gevonden: {len(results)}")
        return pd.DataFrame(results)

    except Exception as e:
        print(f"❌ Fout tijdens scraping Striive: {e}")
        return pd.DataFrame()
    finally:
        driver.quit()
