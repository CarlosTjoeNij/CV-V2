# app.py
import streamlit as st
import pandas as pd
import io
import datetime
from google.cloud import storage

# Titel & intro
st.set_page_config(page_title="CV Matcher", layout="wide")
st.title("CV-Vacature Matcher | Striive & Flextender")
st.write("Deze app gebruikt de laatste vacatures die dagelijks automatisch worden gescraped.")

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

st.success(f"Data geladen uit `{filename}` - {len(df)} vacatures gevonden.")



# --- Streamlit UI ---


nederlandse_provincies = [
    "",  # voor 'geen selectie'
    "Drenthe", "Flevoland", "Friesland", "Gelderland", "Groningen",
    "Limburg", "Noord-Brabant", "Noord-Holland", "Overijssel",
    "Utrecht", "Zeeland", "Zuid-Holland"
    ]

gekozen_provincie = st.selectbox("Filter op provincie (optioneel)", nederlandse_provincies)

uploaded_file = st.file_uploader("Upload CV als PDF", type="pdf")


if uploaded_file:
    with st.spinner("Vacatures scrapen en verwerken, dit kan een tijdje duren..."):
        
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



