import os
import time
import pandas as pd
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
import time
import numpy as np

import fitz
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import streamlit as st
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

import spacy

nltk.download('stopwords')

# --- Functie om paginanummers te verzamelen ---
def get_total_pages(driver, wait):
    max_page = 1
    seen_pages = set()

    while True:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.js-wd-paginatorbutton")))
        paginator_buttons = driver.find_elements(By.CSS_SELECTOR, "span.js-wd-paginatorbutton")

        current_pages = set()
        for btn in paginator_buttons:
            text = btn.text.strip()
            if text.isdigit():
                p = int(text)
                current_pages.add(p)
                seen_pages.add(p)
                if p > max_page:
                    max_page = p

        # Zoek » knop
        next_button = None
        for btn in paginator_buttons:
            if btn.text.strip() == "»":
                next_button = btn
                break

        # Als » niet gevonden of geen nieuwe pagina’s zichtbaar, stop
        if not next_button:
            break

        try:
            next_button.click()
            time.sleep(2)  # Even wachten tot paginanummers laden
        except Exception:
            break

        # Check of er nieuwe pagina's zijn
        new_paginator_buttons = driver.find_elements(By.CSS_SELECTOR, "span.js-wd-paginatorbutton")
        new_pages = set()
        for btn in new_paginator_buttons:
            text = btn.text.strip()
            if text.isdigit():
                new_pages.add(int(text))
        if new_pages.issubset(seen_pages):
            break

    return max_page

def scrape_all_jobs():
    start_time = time.time()
    def scrape_striive():
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15)

        try:
            driver.get("https://login.striive.com/")
            driver.set_window_size(1920, 1080)
            time.sleep(2)

            driver.find_element(By.ID, "email").send_keys(st.secrets["striive"]["username"])
            driver.find_element(By.ID, "password").send_keys(st.secrets["striive"]["password"])
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

            try:
                opdrachten_link = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//a[contains(@href, '/inbox')]//span[contains(text(), 'Opdrachten')]"
                )))
                opdrachten_link.click()
                st.success("✅ Inloggen op Striive gelukt")
            except Exception:
                st.error("❌ Inloggen op Striive mislukt. Controleer je inloggegevens.")
                return pd.DataFrame()

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

                if new_count == 0:
                    repeats += 1
                else:
                    repeats = 0

                driver.execute_script("arguments[0].scrollBy(0, 1000);", scroll_container)
                time.sleep(1.2)

            results = []
            for link, vacature in vacature_links_dict.items():
                try:
                    driver.get(link)

                    # Beschrijving ophalen met timeout
                    try:
                        desc_elem = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='jobRequestDescription']"))
                        )
                        beschrijving_html = desc_elem.get_attribute("innerHTML").strip()
                        soup = BeautifulSoup(beschrijving_html, "html.parser")
                        beschrijving_tekst = soup.get_text(separator="\n").strip()
                        vacature["Beschrijving"] = beschrijving_tekst

                    except Exception as inner_e:
                        vacature["Beschrijving"] = ""

                    results.append(vacature)

                except Exception as outer_e:
                    st.warning(f"⚠️ Fout bij laden detailpagina: {link} - {outer_e}")
                    continue

            st.write(f"Striive - aantal vacatures gevonden: {len(results)}")
            return pd.DataFrame(results)

        except Exception as e:
            st.error(f"❌ Fout tijdens scraping Striive: {e}")
            return pd.DataFrame()

        finally:
            driver.quit()


    def scrape_flextender():
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 10)

        driver.get("https://app.flextender.nl/")
        time.sleep(2)
        try:
            driver.find_element(By.NAME, "login[username]").send_keys(st.secrets["flextender"]["username"])
            driver.find_element(By.NAME, "login[password]").send_keys(st.secrets["flextender"]["password"], Keys.ENTER)
            st.success("✅ Inloggen op Flextender gelukt")
        except Exception as e:
            st.error("❌ Inloggen mislukt op Flextender. Check credentials of browserconfig.")
            st.stop()

        time.sleep(5)

        driver.get("https://app.flextender.nl/supplier/jobs/recommended")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-jobsummarywidget")))
        time.sleep(3)

        total_pages = get_total_pages(driver, wait)
        st.write(f"FlexTender vacatures aantal pagina’s: {total_pages}")

        try:
            paginator = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.target-jobsearchresults-page-1")))
            paginator.click()
            time.sleep(2)
        except Exception as e:
            st.warning(f"⚠️ Kon niet terug naar pagina 1: {e}")

        data = []

        for page_num in range(1, total_pages + 1):
            try:
                paginator = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"span.target-jobsearchresults-page-{page_num}")))
                paginator.click()
                time.sleep(2)
            except Exception as e:
                st.warning(f"⚠️ Kan pagina {page_num} niet openen: {e}")
                continue

            try:
                page_divs = wait.until(EC.presence_of_all_elements_located((
                    By.CSS_SELECTOR, f"div.css-jobsummarywidget.target-jobsearchresults-page-{page_num}"
                )))
            except Exception as e:
                st.warning(f"❌ Geen vacatures gevonden op pagina {page_num}: {e}")
                continue

            for div in page_divs:
                try:
                    card = div.find_element(By.CSS_SELECTOR, ".js-widget-content")
                    link_elem = card.find_element(By.CSS_SELECTOR, "a.job-summary-clickable")
                    link = link_elem.get_attribute("href")

                    titel = card.find_element(By.CSS_SELECTOR, ".flx-jobsummary-title div").text.strip()
                    opdrachtgever = card.find_element(By.CSS_SELECTOR, ".flx-jobsummary-client").text.strip()

                    vacature = {
                        "pagina": page_num,
                        "Titel": titel,
                        "Opdrachtgever": opdrachtgever,
                        "Link": link
                    }

                    caption_fields = card.find_elements(By.CSS_SELECTOR, ".caption-field")
                    for field in caption_fields:
                        try:
                            label = field.find_element(By.CSS_SELECTOR, ".caption").text.strip()
                            value = field.find_element(By.CSS_SELECTOR, ".field").text.strip()
                            vacature[label] = value
                        except:
                            continue

                    driver.execute_script("window.open('');")
                    driver.switch_to.window(driver.window_handles[1])
                    driver.get(link)
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-formattedjobdescription")))
                        desc_html = driver.find_element(By.CSS_SELECTOR, "div.css-formattedjobdescription").get_attribute("innerHTML")
                        vacature["Beschrijving"] = desc_html
                    except:
                        vacature["Beschrijving"] = "Geen beschrijving gevonden"
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                    data.append(vacature)

                except Exception as e:
                    st.warning(f"⚠️ Fout bij vacature verwerken: {e}")
                    continue

        st.write(f"Flextender - aantal vacatures gevonden: {len(data)}")
        driver.quit()
        return pd.DataFrame(data)

    # Start scraping
    df_striive = scrape_striive()
    df_flex = scrape_flextender()
    df_combined = pd.concat([df_striive, df_flex], ignore_index=True)
    duration = time.time() - start_time
    st.write(f"Scraping voltooid in {duration / 60:.1f} minuten")

    return df_combined
