import pandas as pd
import streamlit as st
from datetime import datetime
from dateutil.parser import parse as parse_date

from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==========================
# CONFIGURACIÓN GOOGLE SHEETS
# ==========================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

client = gspread.authorize(creds)

# Nombre del archivo en Google Sheets
SHEET_NAME = "TandaDB"  # <-- cámbialo si tu archivo se llama diferente
spreadsheet = client.open(SHEET_NAME)

# Hojas
sheet_participantes = spreadsheet.worksheet("participantes")
sheet_calendario = spreadsheet.worksheet("calendario")

COLS_PARTICIPANTES = ["id", "nombre", "fecha_cumple", "telefono", "email", "notas"]
COLS_CALENDARIO = [
    "id",
    "anio",
    "id_participante",
    "nombre_participante",
    "fecha_pago",
    "monto_por_persona",
    "total_a_recibir",
    "estatus",
    "fecha_pago_real",
    "notas",
]


# ==========================
# FUNCIONES BASE DE DATOS
# ==========================

def ensure_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Asegura que el DF tenga todas las columnas indicadas."""
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df[columns]


def load_participants() -> pd.DataFrame:
    """Lee participantes desde la hoja de Google Sheets."""
    df = get_as_dataframe(sheet_participantes, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

    if df.empty:
        df = pd.DataFrame(columns=COLS_PARTICIPANTES)
    else:
        df = ensure_columns(df, COLS_PARTICIPANTES)
        df = df.fillna("")

    # Asegurar ID numérico
    if df.empty:
        df["id"] = pd.Series(dtype="int64")
    else:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)

    return df


def save_participants(df: pd.DataFrame):
    """Escribe participantes a la hoja de Google Sheets."""
    df_to_save = ensure_columns(df.copy(), COLS_PARTICIPANTES)
    df_to_save = df_to_save.fillna("")

    sheet_participantes.clear()
    set_with_dataframe(
        sheet_participantes,
        df_to_save,
        include_index=False,
        include_column_header=True,
    )


def load_calendar() -> pd.DataFrame:
    """Lee calendario desde la hoja de Google Sheets."""
    df = get_as_dataframe(sheet_calendario, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

    if df.empty:
        df = pd.DataFrame(columns=COLS_CALENDARIO)
    else:
        df = ensure_columns(df, COLS_CALENDARIO)
        df = df.fillna("")

    # Asegurar tipos básicos
    if df.empty:
        df["id"] = pd.Series(dtype="int64")
        df["anio"] = pd.Series(dtype="int64")
    else:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(
            datetime.today().year
        ).astype(int)

    return df


def save_calendar(df: pd.DataFrame):
    """Escribe calendario a la hoja de Google Sheets."""
    df_to_save = ensure_columns(df.copy(), COLS_CALENDARIO)
    df_to_save = df_to_save.fillna("")

    sheet_calendario.clear()
    set_with_dataframe(
        sheet_calendario,
        df_to_save,
        include_index=False,
        include_column_header=True,
    )


def generate_new_id(df: pd.DataFrame) -> int:
    """Genera un nuevo ID incremental para un DF con columna 'id'."""
    if df.empty or "id" not in df.columns:
