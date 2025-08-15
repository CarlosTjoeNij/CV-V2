# app.py
import streamlit as st
import pandas as pd
import io
import datetime
from google.cloud import storage

# Titel & intro
st.set_page_config(page_title="CV Matcher", layout="wide")
st.title("💼 CV Matcher")
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

# Filters
col1, col2 = st.columns(2)
with col1:
    regio_filter = st.multiselect("Regio filter", sorted(df["Regio"].dropna().unique()))
with col2:
    opdrachtgever_filter = st.multiselect("Opdrachtgever filter", sorted(df["Opdrachtgever"].dropna().unique()))

# Filteren
filtered_df = df.copy()
if regio_filter:
    filtered_df = filtered_df[filtered_df["Regio"].isin(regio_filter)]
if opdrachtgever_filter:
    filtered_df = filtered_df[filtered_df["Opdrachtgever"].isin(opdrachtgever_filter)]

st.write(f"📄 {len(filtered_df)} vacatures na filteren")

# Data tonen
st.dataframe(filtered_df, use_container_width=True)

# Optioneel: Download knop
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download CSV",
    data=csv,
    file_name="vacatures.csv",
    mime="text/csv",
)
