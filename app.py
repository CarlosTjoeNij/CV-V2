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

# --- Scrape functie, draait pas als PDF geupload is ---
def scrape_jobs():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Als chromium en chromedriver standaard in PATH staan via nix, hoef je geen pad aan te geven.
    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)

    # Inloggen
    driver.get("https://app.flextender.nl/")
    time.sleep(2)
    driver.find_element(By.NAME, "login[username]").send_keys(st.secrets["username"])
    driver.find_element(By.NAME, "login[password]").send_keys(st.secrets["password"], Keys.ENTER)
    time.sleep(5)

    # Naar aanbevolen vacatures
    driver.get("https://app.flextender.nl/supplier/jobs/recommended")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-jobsummarywidget")))
    time.sleep(3)

    # Haal totaal aantal pagina's dynamisch
    total_pages = get_total_pages(driver, wait)
    st.write(f"🔢 Totale aantal pagina’s: {total_pages}")

    # Ga terug naar pagina 1
    try:
        paginator = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.target-jobsearchresults-page-1")))
        paginator.click()
        time.sleep(2)
    except Exception as e:
        st.warning(f"⚠️ Kon niet terug naar pagina 1: {e}")

    data = []

    for page_num in range(1, total_pages + 1):
        st.write(f"🔄 Verwerk pagina {page_num}")

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

        st.write(f"🔎 {len(page_divs)} vacatures gevonden op pagina {page_num}")

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

                # Beschrijving ophalen via nieuwe tab
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

    driver.quit()
    return pd.DataFrame(data)

# --- PDF extractie ---
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# --- Stopwoorden ---
extra_stopwoorden = [
    "bedrijf", "organisatie", "functie", "vacature", "collega", "collega’s", "team",
    "medewerker", "werkplek", "dienstverband", "parttime", "fulltime", "uur", "per week",
    "standplaats", "standplaats:", "locatie", "werken", "werkzaamheden", "rol",
    "wij", "ons", "onze", "je", "jij", "jou", "jouw", "we", "bij", "ben", "gaat", "gaat om",
    "moet", "dient", "gezocht", "zoeken", "bieden", "vragen", "contact", "solliciteer",
    "acquisitie", "vinden", "vinden wij", "past", "kom", "kom jij", "komt", "komt bij", "sollicitatie",
    "salaris", "reiskostenvergoeding", "pensioen", "arbeidsvoorwaarden", "contract",
    "bonus", "secundaire", "verlof", "feest", "feestdagen", "kerstpakket", "borrel",
    "vrijdagmiddagborrel", "flexibiliteit", "overleg", "ontwikkeling", "ontwikkelen",
    "persoonlijk", "persoonlijke", "coaching", "opleiding", "training",
    "sfeer", "leuk", "uitdagend", "afwisselend", "gezellig", "gezelligheid", "laagdrempelig",
    "samen", "samenwerken", "teamwork", "passie", "motivatie", "impact", "doen", "koffie",
    "tijdelijk", "vast", "vast dienstverband", "interim", "freelance", "detavast", "detachering",
    "wat breng jij mee", "dit krijg je van ons", "bij wie kom je in dienst", "klaar om impact te maken",
    "solliciteer", "upload je cv", "kom langs voor een kop koffie",
    'volgende', 'gemaakt', 'gebruik', 'alle', 'maken', 'kunnen', 'dienen', 'zoals',
    'onder', 'over', 'ook', 'zowel', 'middels', 'met', 'tegen', 'voor', 'naar', 'door',
    'tussen', 'tot', 'binnen', 'buiten', 'hierbij', 'hiervoor', 'hierin', 'hiermee',
    'waarbij', 'waarin', 'waardoor', 'daardoor', 'zodat', 'terwijl', 'toen', 'nadat',
    'omdat', 'voordat', 'nadien', 'dan', 'danwel', 'enkel', 'en', 'of', 'maar', 'dus',
    'nog', 'eens', 'reeds', 'welke', 'ieder', 'elke', 'iemand', 'niemand', 'iets',
    'niets', 'veel', 'weinig', 'andere', 'eigen', 'zelfde', 'bijvoorbeeld', 'etc',
    'etcetera', 'teneinde', 'richting', 'zichzelf', 'zelf', 'aanwezig', 'beschikbaar',
    'passend', 'relevant', 'geschikt', 'verantwoordelijk', 'bijdragen', 'uitvoeren',
    'betreft', 'bevindt', 'beschrijft', 'betrokken', 'gerichte', 'gerichte', 'gedaan',
    'bezig', 'functie', 'rol', 'taak', 'doel', 'doelen', 'belangrijk', 'nodig',
    'nodige', 'goede', 'voldoende', 'eisen', 'vragen', 'vereisten', 'ervaring',
    'vaardigheden', 'competenties', 'vaardig', 'kennis', 'opleiding', 'opleiding(en)',
    'aanvullend', 'specifiek', 'mogelijkheid', 'mogelijkheden', 'werken', 'gewerkt',
    'werkzaamheden', 'werk', 'project', 'projecten', 'uitdaging', 'uitdagend',
    'samenwerken', 'team', 'teams', 'organisatie', 'organisaties', 'onderdeel',
    'onderdelen', 'aanpak', 'aanpakken', 'proces', 'processen', 'gericht', 'resultaat',
    'resultaten', 'kwaliteit', 'continue', 'optimaliseren', 'verbeteren', 'bewaken',
    'coördineren', 'implementeren', 'monitoren', 'brengt', 'brengen', 'zorgt',
    'zorgen', 'uitvoeren', 'uitvoering', 'uitgevoerd', 'toe', 'toevoegen', 'toegevoegd',
    'krijgt', 'krijgen', 'lager', 'omtrent', 'betreffende', 'aangaande','zich', 'zichzelf',
    'werkt', 'relevante', 'casus', 'bestaande', 'bestaand', 'komende', 'kom', 'komen','werkveld',
    'staat', 'dagen', 'mindere', 'meer', 'bachelor', 'master', 'hbo', 'wo', 'gerelateerde',
    'houdt', 'vakgebied', 'vakgebieden', 'sector', 'sectoren', 'branche', 'branches',
    'bevindingen', 'inzicht', 'nieuwe', 'daarnaast', 'daarbij', 'daarom', 'daaromheen',
    'minder', 'waarde', 'intern', 'aantal', 'professional', 'omgeving', 'gebied', 'niveau',
    'verder', 'werkervaring', 'opdrachtgever', 'jaar', 'nederlands', 'overige'
]

dutch_stopwords = set(stopwords.words('dutch') + extra_stopwoorden + stopwords.words('english'))

nlp = spacy.load("nl_core_news_sm")

def filter_relevant_pos_nl(text):
    doc = nlp(text)
    # Keep nouns, adjectives, adverbs
    relevant_pos = {"NOUN", "PROPN", "ADJ", "ADV"}
    filtered_tokens = [token.text for token in doc if token.pos_ in relevant_pos]
    return " ".join(filtered_tokens)

def clean_text_nl(text):
    text = re.sub(r"[^a-zA-ZÀ-ÿ\s]", "", text)  # Alleen letters en accenten
    words = text.lower().split()
    words = [word for word in words if word not in dutch_stopwords]
    words_all = [word for word in words if word not in ENGLISH_STOP_WORDS]
    return " ".join(words_all)

def match_jobs(cv_text, df):
    df["clean_description"] = df["Beschrijving"].apply(clean_text_nl)
    df["cleaner_description"] = df["clean_description"].apply(filter_relevant_pos_nl)
    all_texts = [cv_text] + df["cleaner_description"].tolist()
  
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(all_texts)
    
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    
    df["score"] = similarities
    return df.sort_values(by="score", ascending=False), tfidf

def get_top_keywords_for_match(cv_text, job_desc, tfidf_vectorizer, top_n=15):
    # Vectoriseer CV en job description
    tfidf_matrix = tfidf_vectorizer.transform([cv_text, job_desc])
    
    # Haal feature namen (woorden)
    feature_names = tfidf_vectorizer.get_feature_names_out()
    
    # Haal vectoren
    cv_vec = tfidf_matrix[0].toarray().flatten()
    job_vec = tfidf_matrix[1].toarray().flatten()
    
    # Woorden die in zowel CV als job voorkomen (beide > 0)
    common_indices = [i for i in range(len(feature_names)) if cv_vec[i] > 0 and job_vec[i] > 0]
    
    # Score per woord (min of cv en job TF-IDF waarde, want beide moeten aanwezig zijn)
    word_scores = [(feature_names[i], min(cv_vec[i], job_vec[i])) for i in common_indices]
    
    # Sorteer op score aflopend
    word_scores = sorted(word_scores, key=lambda x: x[1], reverse=True)
    
    return word_scores[:top_n]

# --- Streamlit UI ---
st.title("CV-Vacature Matcher")

uploaded_file = st.file_uploader("Upload je CV als PDF", type="pdf")

if uploaded_file:
    with st.spinner("Vacatures ophalen en verwerken, even geduld..."):
        df = scrape_jobs()
    st.success(f"✅ {len(df)} vacatures verzameld.")

    cv_text = extract_text_from_pdf(uploaded_file)
    cv_text_clean = clean_text_nl(cv_text)

    matched_df, tfidf = match_jobs(cv_text_clean, df)

    st.write("Top Matches:")
    st.dataframe(matched_df[["Titel", "Opdrachtgever", "score", "Link"]].head(10))

    if not matched_df.empty:
        top_job = matched_df.iloc[0]
        st.subheader(f"Top match: {top_job['Titel']} bij {top_job['Opdrachtgever']}")
        keywords = get_top_keywords_for_match(cv_text_clean, top_job["clean_description"], tfidf)
        
        st.write("Belangrijkste overeenkomende woorden die bijdragen aan de score:")
        for word, score in keywords:
            st.write(f"- {word} (score: {score:.3f})")
else:
    st.info("Upload eerst een CV om de matching te starten.")
