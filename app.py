# app.py
import datetime
from google.cloud import storage
import os
import io
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

# Titel & intro
st.set_page_config(page_title="CV Matcher", layout="wide")
st.title("CV-Vacature Matcher")
st.write("Deze app gebruikt de laatste vacatures die dagelijks automatisch worden gescraped.")
st.write("Gebruikte platformen: Striive, Flextender en Yacht")

# Functie om data te laden vanuit GCS
@st.cache_data(ttl=3600)  # Cache 1 uur
def load_today_jobs():
    today_str = datetime.date.today().isoformat()
    filename = f"jobs_{today_str}.parquet"

    storage_client = storage.Client()
    bucket = storage_client.bucket("scrapes_cvmatcher")
    blob = bucket.blob(filename)

    if not blob.exists():
        return None, filename

    data = blob.download_as_bytes()
    df = pd.read_parquet(io.BytesIO(data))
    return df, filename

# Data laden
df, filename = load_today_jobs()

if df is None:
    st.error(f"Geen data gevonden voor vandaag. Verwacht bestand: `{filename}` in bucket `scrapes_cvmatcher`.")
    st.stop()

st.success(f"{len(df)} vacatures gevonden | Data geladen uit `{filename}`")

# --- PDF extractie ---
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

nederlandse_provincies = [
    "",  # voor 'geen selectie'
    "Drenthe", "Flevoland", "Friesland", "Gelderland", "Groningen",
    "Limburg", "Noord-Brabant", "Noord-Holland", "Overijssel",
    "Utrecht", "Zeeland", "Zuid-Holland"]

gekozen_provincie = st.selectbox("Filter op provincie (optioneel)", nederlandse_provincies)

uploaded_file = st.file_uploader("Upload CV als PDF", type="pdf")

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
    'verder', 'werkervaring', 'opdrachtgever', 'jaar', 'nederlands', 'overige', 'universiteit',
    'tijdens', 'uitdagingen'
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
    if not isinstance(text, str):
        return ""  # Lege string als input geen tekst is
    text = re.sub(r"[^a-zA-ZÀ-ÿ\s]", "", text)  
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
if uploaded_file:
    with st.spinner("Beste matches zoeken"):
        
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
















