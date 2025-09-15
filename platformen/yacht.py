import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

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
import requests

provincies = [
    "Groningen",
    "Friesland",
    "Drenthe",
    "Overijssel",
    "Flevoland",
    "Gelderland",
    "Utrecht",
    "Noord-Holland",
    "Zuid-Holland",
    "Zeeland",
    "Noord-Brabant",
    "Limburg"
]

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

def scrape_yacht():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    
    driver = get_chrome_driver()
    wait = WebDriverWait(driver, 15)
    
    try:
        driver.get("https://www.yacht.nl/mijn-yacht/")
        driver.set_window_size(1920, 1080)
        time.sleep(2)
    
        # Inloggen
        driver.find_element(By.ID, "input-username").send_keys("informatiemanagement@breinstein.nl")
        driver.find_element(By.ID, "input-password").send_keys("Breinstein123!")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
        vacatures_link = wait.until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/vacatures')]"))
        )
        driver.execute_script("arguments[0].click();", vacatures_link)
        st.success("✅ Inloggen op Yacht gelukt")
    
        # >>> Nieuw stuk: laad alle vacatures
        while True:
            try:
                load_more = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button__load-more"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                time.sleep(1)
                load_more.click()
                time.sleep(2)
            except TimeoutException:
                break  # geen knop meer aanwezig
    
        # Nu alle vacatures ophalen
        vacatures = driver.find_elements(By.CSS_SELECTOR, "a.search-card--vacancy")
        st.write(f"Yacht - aantal vacatures gevonden: {len(vacatures)}")
    
        results = []
        for vac in vacatures:
            try:
                titel = vac.find_element(By.TAG_NAME, "h4").text.strip()
            except:
                titel = None
            
            try:
                regio = vac.find_element(
                    By.CSS_SELECTOR, "ul.vacancy-meta__list li:nth-child(1) span:last-child"
                ).text.strip()
            except:
                regio = None
    
            link = vac.get_attribute("href")
    
            # Detailpagina openen
            driver.execute_script("window.open(arguments[0], '_blank');", link)
            driver.switch_to.window(driver.window_handles[1])
    
            try:
                beschrijving_el = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article.rich-text--vacancy"))
                )
                beschrijving = beschrijving_el.text.strip()
            except:
                beschrijving = None
    
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
    
            results.append({
                "Titel": titel,
                "Opdrachtgever": None,
                "Regio": regio,
                "Link": link,
                "Bron": "Yacht",
                "Beschrijving": beschrijving
            })
    
        df = pd.DataFrame(results)

        # >>> Data merge stuk
        plek1 = pd.read_csv('WoonplaatsenCodes.csv', sep=';')
        plek2 = pd.read_csv('Observations.csv', sep=';')
        gem = pd.read_csv('gemeentes.csv', sep=';', encoding='latin1')

        plek_merged = pd.merge(
            plek2,
            plek1[['Identifier', 'Title']],
            left_on='Woonplaatsen', 
            right_on='Identifier',
            how='left'
        ).drop(columns=['Identifier'])

        provincies_clean = {p.lower().strip(): p for p in provincies}
        plek_merged['StringValue'] = plek_merged['StringValue'].replace("Fryslân", "Friesland")
        plek_merged['StringValue_clean'] = plek_merged['StringValue'].str.lower().str.strip()

        plek_merged_filtered = plek_merged[
            plek_merged['StringValue_clean'].isin(provincies_clean.keys())
        ].copy()
        plek_merged_filtered['Provincie'] = plek_merged_filtered['StringValue_clean'].map(provincies_clean)

        df['Plaats_clean'] = df['Regio'].str.split(',').str[0].str.strip().str.lower()
        plek_merged_filtered['Title_clean'] = plek_merged_filtered['Title'].str.strip().str.lower()

        df_alles = df.merge(
            plek_merged_filtered[['Title_clean', 'Provincie']],
            how='left',
            left_on='Plaats_clean',
            right_on='Title_clean'
        ).drop(columns=['Title_clean'])

        df_alles['Provincie'] = df_alles['Provincie'].fillna(df_alles['Regio'])

        return df_alles

    finally:
        driver.quit()
