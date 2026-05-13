"""
config.py — Carga variables de entorno y define constantes globales.
Único punto de verdad para IDs, rutas y parámetros del proyecto.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Gmail OAuth2 (cuenta cgi@tutrastero.com) ─────────────────────────────────
GMAIL_CLIENT_ID     = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN", "")
GMAIL_ACCOUNT       = "cgi@tutrastero.com"

# ─── Airtable ─────────────────────────────────────────────────────────────────
AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appMNiPmgPOBdXZxt")

# Tablas
AT_TBL_CLASIFICACION      = "tblKSSUdMWhL1n2Sw"   # Clasificación
AT_TBL_DATOS_EXTRAIDOS    = "tblFsUGpeqIvAnEVh"   # Datos extraídos
AT_TBL_DEFINICIONES       = "tblcU03Ozh0QzuRGe"   # BC_Definiciones
AT_TBL_EJEMPLOS_BOT_HUMANO = "tbl7KdLEUJsSyWVD1"  # BC_Ejemplos Bot_Humano
AT_TBL_EJEMPLOS_CLASIF    = "tblFs49ab5AFo4x4r"   # BC_Ejemplos Clasificación
AT_TBL_EJEMPLOS_TIPO      = "tblUJTvQ8FWoYxkx5"   # BC_Ejemplos Tipo (tabla separada: campos Fragmento de Correo, Tipo de correo)
AT_TBL_CENTROS            = "tbl2vbsg29v94Qjgf"   # BC_Centros

# ─── Bitrix24 ──────────────────────────────────────────────────────────────────
BITRIX_URL = os.getenv("BITRIX_URL", "")   # https://tutrastero.bitrix24.eu/rest/ID/TOKEN

# ─── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_KEY   = os.getenv("OPENAI_KEY", "")
OPENAI_MODEL = "gpt-4.1"

# ─── Correo de clasificación (escenario 1.0) ──────────────────────────────────
CLASIFICACION_TO   = ["iacgi@tutrastero.com", "sistemas@tutrastero.com"]
CLASIFICACION_FROM = "cgi@tutrastero.com"

# ─── Poller Gmail ─────────────────────────────────────────────────────────────
POLL_INTERVAL = 60   # segundos entre cada ciclo de lectura

# ─── Filtro de remitentes — correos que nunca se procesan ─────────────────────
EMAIL_BLACKLIST_CONTAINS = [
    "@telefacil.com",
    "noreply@",
    "no-reply@",
    "@e.fundacionmapfre.org",
    "@alcobendas.org",
    "@hyperionup.com",
    "newsletter",
    "info@necesitasrespirar.com",
    "@norauto.es",
    "noreply.",
]
