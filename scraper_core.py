# scraper_core.py
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Deze kun je in .env of secrets zetten
import os
STRIIVE_USER = os.environ.get("STRIIVE_USER")
STRIIVE_PASS = os.environ.get("STRIIVE_PASS")
FLEX_USER = os.environ.get("FLEX_USER")
FLEX_PASS = os.environ.get("FLEX_PASS")

def get_total_pages(driver, wait):
    max_page = 1
    seen_pages = set()
    while True:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.js-wd-paginatorbutton")))
        paginator_buttons = driver.find_elements(By.CSS_SELECTOR, "span.js-wd-paginatorbutton")

        for btn in paginator_buttons:
            text = btn.text.strip()
            if text.isdigit():
                p = int(text)
                seen_pages.add(p)
                if p > max_page:
                    max_page = p

        next_button = next((btn for btn in paginator_buttons if btn.text.strip() == "»"), None)
        if not next_button:
            break

        try:
            next_button.click()
            time.sleep(2)
        except Exception:
            break

        new_pages = {int(btn.text.strip()) for btn in driver.find_elements(By.CSS_SELECTOR, "span.js-wd-paginatorbutton") if btn.text.strip().isdigit()}
        if new_pages.issubset(seen_pages):
            break

    return max_page

def scrape_striive():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get("https://login.striive.com/")
        time.sleep(2)
        driver.find_element(By.ID, "email").send_keys(STRIIVE_USER)
        driver.find_element(By.ID, "password").send_keys(STRIIVE_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        opdrachten_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/inbox')]//span[contains(text(), 'Opdrachten')]")))
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

def scrape_flextender():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get("https://app.flextender.nl/")
        time.sleep(2)
        driver.find_element(By.NAME, "login[username]").send_keys(FLEX_USER)
        driver.find_element(By.NAME, "login[password]").send_keys(FLEX_PASS, Keys.ENTER)
        print("✅ Inloggen op Flextender gelukt")
    except Exception as e:
        print("❌ Inloggen mislukt op Flextender.")
        driver.quit()
        return pd.DataFrame()

    time.sleep(5)
    driver.get("https://app.flextender.nl/supplier/jobs/recommended")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-jobsummarywidget")))
    time.sleep(3)

    total_pages = get_total_pages(driver, wait)
    print(f"FlexTender vacatures aantal pagina’s: {total_pages}")

    data = []
    for page_num in range(1, total_pages + 1):
        try:
            paginator = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"span.target-jobsearchresults-page-{page_num}")))
            paginator.click()
            time.sleep(2)
        except:
            continue

        try:
            page_divs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"div.css-jobsummarywidget.target-jobsearchresults-page-{page_num}")))
        except:
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
                    vacature["Beschrijving"] = ""
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                data.append(vacature)

            except Exception as e:
                print(f"⚠️ Fout bij vacature verwerken: {e}")
                continue

    print(f"Flextender - aantal vacatures gevonden: {len(data)}")
    driver.quit()
    return pd.DataFrame(data)

def scrape_all_jobs():
    start_time = time.time()
    df_striive = scrape_striive()
    df_flex = scrape_flextender()
    df_combined = pd.concat([df_striive, df_flex], ignore_index=True)
    duration = time.time() - start_time
    print(f"Scraping voltooid in {duration/60:.1f} minuten")
    return df_combined
