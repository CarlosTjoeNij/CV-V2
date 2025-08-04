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

    return df_combined

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

def get_top_keywords_for_match(cv_text, job_desc, tfidf_vectorizer, top_n=8):
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
st.title("CV-Vacature Matcher | Striive & Flextender")

nederlandse_provincies = [
    "",  # voor 'geen selectie'
    "Drenthe", "Flevoland", "Friesland", "Gelderland", "Groningen",
    "Limburg", "Noord-Brabant", "Noord-Holland", "Overijssel",
    "Utrecht", "Zeeland", "Zuid-Holland"
    ]

gekozen_provincie = st.selectbox("Filter op provincie (optioneel)", nederlandse_provincies)

uploaded_file = st.file_uploader("Upload CV als PDF", type="pdf")

# Cache scrapingresultaat op schijf – blijft actief zolang de container leeft (en max 6 uur)
@st.cache_data(ttl=21600, persist="disk", show_spinner=False)
def cached_scrape():
    return scrape_all_jobs()

if uploaded_file:
    progress_bar = st.progress(0, text="Vacatures scrapen en verwerken... dit kan een paar minuten duren.")
    status_text = st.empty()

    # Simuleer voortgang tijdens cache call
    for i in range(100):
        time.sleep(0.05)  # totaal ~5 seconden
        progress_bar.progress(i + 1)
        if i == 20:
            status_text.text("🔍 Bezig met verzamelen van vacatures...")
        elif i == 50:
            status_text.text("📄 Bezig met verwerken van beschrijvingen...")
        elif i == 80:
            status_text.text("🧠 Bezig met voorbereiden op matching...")

    # Voer scrape uit terwijl de progressbar loopt
    df = cached_scrape()

    progress_bar.empty()
    status_text.empty()
    st.success(f"✅ In totaal {len(df)} vacatures verzameld. De beste matches zullen hieronder worden weergegeven.")

    cv_text = extract_text_from_pdf(uploaded_file)
    cv_text_clean = clean_text_nl(cv_text)

    matched_df, tfidf = match_jobs(cv_text_clean, df)
    matched_df['Regio'] = matched_df['Regio'].apply(lambda x: x.split(' - ')[1] if isinstance(x, str) and ' - ' in x else x)

    # Filter matched_df op basis van selectie
    if gekozen_provincie:
        matched_df = matched_df[matched_df["Regio"].str.contains(gekozen_provincie, case=False, na=False)]

    st.write("Top Matches:")
    st.dataframe(matched_df[["Titel", "Opdrachtgever", "score", "Regio", "Link"]].head(10))

    if not matched_df.empty:
        top_job = matched_df.iloc[0]
        st.subheader(f"Top match: {top_job['Titel']} bij {top_job['Opdrachtgever']}")
        keywords = get_top_keywords_for_match(cv_text_clean, top_job["clean_description"], tfidf)
        
        st.write("Belangrijkste overeenkomende woorden die bijdragen aan de score:")
        for word, score in keywords:
            st.write(f"- {word} (score: {score:.3f})")
else:
    st.info("Upload eerst een CV om de matching te starten.")

