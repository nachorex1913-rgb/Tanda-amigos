import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.parser import parse as parse_date

from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe


# ============================================================
# CONFIG: GOOGLE SHEETS
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

client = gspread.authorize(creds)

SHEET_NAME = "TandaDB"   # <-- Nombre del documento en Google Sheets
spreadsheet = client.open(SHEET_NAME)

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


# ============================================================
# FUNCIONES BASE DE DATOS
# ============================================================

def ensure_columns(df, columns):
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df[columns]


def load_participants():
    df = get_as_dataframe(sheet_participantes, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

    if df.empty:
        return pd.DataFrame(columns=COLS_PARTICIPANTES)

    df = ensure_columns(df.fillna(""), COLS_PARTICIPANTES)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    return df


def load_calendar():
    df = get_as_dataframe(sheet_calendario, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

    if df.empty:
        return pd.DataFrame(columns=COLS_CALENDARIO)

    df = ensure_columns(df.fillna(""), COLS_CALENDARIO)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(
        datetime.today().year
    ).astype(int)

    return df


# ============================================================
# DASHBOARD LECTURA
# ============================================================

st.set_page_config(page_title="Tanda Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard de la Tanda entre Amigos")
st.caption("Esta es una vista pública (solo lectura).")


# Cargar datos
participants_df = load_participants()
calendar_df = load_calendar()


tab_cal, tab_hist, tab_part = st.tabs(["Calendario", "Historial", "Participantes"])


# ============================================================
# TAB: CALENDARIO (SOLO LECTURA)
# ============================================================

with tab_cal:
    st.header("Calendario de Pagos")

    if calendar_df.empty:
        st.info("No hay datos de calendario todavía.")
    else:
        anios = sorted(calendar_df["anio"].unique())
        anio_sel = st.selectbox("Selecciona el año", anios)

        df_year = calendar_df[calendar_df["anio"] == anio_sel].copy()

        df_year["fecha_pago"] = pd.to_datetime(
            df_year["fecha_pago"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        st.write("### Calendario del Año")
        st.dataframe(
            df_year[
                [
                    "nombre_participante",
                    "fecha_pago",
                    "monto_por_persona",
                    "total_a_recibir",
                    "estatus",
                    "fecha_pago_real",
                    "notas",
                ]
            ].sort_values("fecha_pago"),
            use_container_width=True,
        )


# ============================================================
# TAB: HISTORIAL GENERAL
# ============================================================

with tab_hist:
    st.header("Historial General")

    if calendar_df.empty:
        st.info("Aún no hay historial registrado.")
    else:
        anios = sorted(calendar_df["anio"].unique())
        anio_sel = st.selectbox("Selecciona un año", anios)

        df_year = calendar_df[calendar_df["anio"] == anio_sel].copy()

        completados = (df_year["estatus"] == "Completado").sum()
        pendientes = (df_year["estatus"] == "Pendiente").sum()
        dinero_total = df_year["total_a_recibir"].sum()

        st.subheader("Resumen del Año")
        st.write(f"Turnos en total: **{len(df_year)}**")
        st.write(f"Completados: **{completados}**")
        st.write(f"Pendientes: **{pendientes}**")
        st.write(f"Total dinero acumulado: **${dinero_total:,.2f} USD**")

        st.subheader("Por Participante")
        resumen = (
            df_year.groupby("nombre_participante")
            .agg(
                turnos=("id", "count"),
                completados=("estatus", lambda x: (x == "Completado").sum()),
                pendientes=("estatus", lambda x: (x == "Pendiente").sum()),
                total_recibir=("total_a_recibir", "sum"),
            )
            .reset_index()
        )

        st.dataframe(resumen, use_container_width=True)

        st.subheader("Detalle Completo")
        st.dataframe(
            df_year[
                [
                    "nombre_participante",
                    "fecha_pago",
                    "fecha_pago_real",
                    "estatus",
                    "total_a_recibir",
                    "notas",
                ]
            ].sort_values("fecha_pago"),
            use_container_width=True,
        )


# ============================================================
# TAB: PARTICIPANTES
# ============================================================

with tab_part:
    st.header("Lista de Participantes")

    if participants_df.empty:
        st.info("Todavía no hay participantes registrados.")
    else:
        st.dataframe(
            participants_df[
                ["nombre", "fecha_cumple", "telefono", "email", "notas"]
            ],
            use_container_width=True,
        )
