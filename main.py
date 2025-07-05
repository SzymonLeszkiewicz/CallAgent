import streamlit as st
import requests
import json
from datetime import datetime

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="📞 CALL Dashboard",
    page_icon="📞",
    layout="wide"
)

# --- CSS (bez zmian, pominięto dla zwięzłości) ---
st.markdown("""
<style>
    .metric-card { background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin: 0.5rem 0; height: 150px; display: flex; flex-direction: column; justify-content: center; }
    .event-card { background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%); padding: 1rem; border-radius: 10px; color: white; margin: 0.5rem 0; }
    .quality-excellent { background: linear-gradient(45deg, #56ab2f 0%, #a8e6cf 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; height: 150px; display: flex; flex-direction: column; justify-content: center; }
    .quality-good { background: linear-gradient(45deg, #f7971e 0%, #ffd200 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; height: 150px; display: flex; flex-direction: column; justify-content: center; }
    .quality-poor { background: linear-gradient(45deg, #fc4a1a 0%, #f7b733 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; height: 150px; display: flex; flex-direction: column; justify-content: center; }
    .summary-box { background: #f8f9fa; border-left: 4px solid #007bff; padding: 1rem; border-radius: 5px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)


st.title("📞 CALL Dashboard")
st.markdown("---")

# --- Konfiguracja Webhook'a z sekretów ---
try:
    WEBHOOK_URL = st.secrets["n8n_webhook"]
except (FileNotFoundError, KeyError):
    st.error("Błąd: Brak pliku secrets.toml lub klucza 'n8n_webhook'.")
    WEBHOOK_URL = None

# --- Funkcje Pomocnicze ---

def get_google_drive_direct_download_link(sharing_url):
    """Przekształca link udostępniania z Dysku Google na link do bezpośredniego pobierania."""
    try:
        file_id = sharing_url.split('/d/')[1].split('/')[0]
        direct_download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
        return direct_download_url
    except IndexError:
        st.error("Nieprawidłowy format linku udostępniania z Dysku Google.")
        return None

def get_quality_class(score):
    if score is None: return "metric-card"
    if score >= 8: return "quality-excellent"
    elif score >= 6: return "quality-good"
    else: return "quality-poor"

def format_iso_datetime(iso_str):
    if not iso_str: return "Brak daty", "Brak godziny"
    try:
        date_obj = datetime.fromisoformat(iso_str)
        return date_obj.strftime("%d.%m.%Y"), date_obj.strftime("%H:%M")
    except (ValueError, TypeError): return "Błędna data", "Błędny czas"

# --- Funkcja do wyświetlania wyników (bez zmian) ---
def display_results(data):
    col1, col2, col3 = st.columns(3)
    quality_assessment = data.get('quality_assessment', {})
    quality_score = quality_assessment.get('score')
    with col1:
        quality_class = get_quality_class(quality_score)
        score_display = f"{quality_score}/10" if quality_score is not None else "Brak"
        st.markdown(f'<div class="{quality_class}"><h3>🏆 Ocena Jakości</h3><h1>{score_display}</h1></div>', unsafe_allow_html=True)
    with col2:
        event_status = "✅ JEST" if data.get('appointment_detected', False) else "❌ BRAK"
        st.markdown(f'<div class="metric-card"><h3>📅 Umówione Spotkanie</h3><h2>{event_status}</h2></div>', unsafe_allow_html=True)
    with col3:
        status_icon = "🟢" if quality_score and quality_score >= 8 else "🟡" if quality_score and quality_score >= 6 else "🔴" if quality_score else "⚪"
        status_text = "DOSKONAŁA" if quality_score and quality_score >= 8 else "DOBRA" if quality_score and quality_score >= 6 else "DO POPRAWY" if quality_score else "BRAK OCENY"
        st.markdown(f'<div class="metric-card"><h3>{status_icon} Status Rozmowy</h3><h2>{status_text}</h2></div>', unsafe_allow_html=True)
    st.markdown("---")
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("📋 Podsumowanie Rozmowy")
        st.markdown(f"<div class=\"summary-box\">{data.get('summary', 'Brak podsumowania')}</div>", unsafe_allow_html=True)
        st.subheader("📊 Uzasadnienie Oceny Jakości")
        st.write(quality_assessment.get('justification', 'Brak uzasadnienia.'))
    with col_right:
        st.subheader("📅 Szczegóły Wydarzenia")
        if data.get('appointment_detected', False) and data.get('final_appointment'):
            event = data['final_appointment']
            event_date, event_time = format_iso_datetime(event.get('final_iso_date'))
            st.markdown(f'<div class="event-card"><h4>📌 {event.get("title", "Brak tytułu")}</h4><p><strong>🗓️ Data:</strong> {event_date}</p><p><strong>🕒 Godzina:</strong> {event_time}</p></div>', unsafe_allow_html=True)
            with st.expander("📄 Uzasadnienie wyboru terminu"):
                st.write(event.get('justification_for_date', 'Brak uzasadnienia.'))
        else:
            st.info("❌ Nie zaplanowano żadnych wydarzeń podczas tej rozmowy.")

# --- Funkcja do analizy (bez zmian) ---
def analyze_audio(file_bytes, file_name, file_type):
    if not WEBHOOK_URL:
        st.error("URL Webhooka nie jest skonfigurowany. Sprawdź sekrety.")
        return
    try:
        with st.spinner("🔄 Transkrybuję i analizuję rozmowę... To może potrwać do minuty."):
            files = {'audio_file': (file_name, file_bytes, file_type)}
            response = requests.post(WEBHOOK_URL, files=files, timeout=300)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                content_data = result[0].get('choices', [{}])[0].get('message', {}).get('content', {})
                if content_data:
                    st.success("✅ Rozmowa została pomyślnie przeanalizowana!")
                    st.markdown("---")
                    display_results(content_data)
                else: st.error("❌ Otrzymano dane, ale w nieoczekiwanym formacie."); st.json(result)
            else: st.error("❌ Otrzymano pustą lub nieprawidłową odpowiedź z serwera."); st.json(result)
        else:
            st.error(f"❌ Błąd podczas przetwarzania: Status {response.status_code}")
            st.error(f"Szczegóły: {response.text}")
    except requests.exceptions.Timeout: st.error("⏰ Przekroczono limit czasu (300s).")
    except Exception as e: st.error(f"❌ Wystąpił nieoczekiwany błąd: {str(e)}")

# --- Logika Uploadu Pliku i Przykładowego Nagrania ---
st.subheader("🎵 Prześlij Nagranie Rozmowy")
uploaded_file = st.file_uploader("Wybierz plik audio", type=['mp3', 'm4a', 'wav', 'mp4'], label_visibility="collapsed")
use_example_button = st.button("▶️ Użyj Przykładowego Nagrania")

# Obsługa wgranego pliku
if uploaded_file is not None:
    analyze_audio(uploaded_file.getvalue(), uploaded_file.name, uploaded_file.type)

# Obsługa przycisku z przykładem
if use_example_button:
    try:
        sharing_url = st.secrets["example_rec"]
        direct_url = get_google_drive_direct_download_link(sharing_url)
        
        if direct_url:
            st.info("🎧 Pobieram i analizuję przykładowe nagranie z Dysku Google...")
            response = requests.get(direct_url, timeout=60)
            response.raise_for_status()
            audio_bytes = response.content
            content_type = response.headers.get('content-type', 'audio/mpeg')

            analyze_audio(audio_bytes, "example.m4a", content_type)

    except requests.exceptions.RequestException as e:
        st.error(f"Błąd podczas pobierania przykładowego nagrania: {e}")
    except KeyError:
        st.error("Błąd: Brak klucza 'PRZYKLADOWE_NAGRANIE_URL' w pliku z sekretami.")
    except Exception as e:
        st.error(f"Wystąpił nieoczekiwany błąd: {e}")