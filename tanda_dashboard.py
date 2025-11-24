import streamlit as st
import pandas as pd
from datetime import datetime

from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe


# ============================================================
# CONFIG: GOOGLE SHEETS (SOLO LECTURA)
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

SHEET_NAME = "TandaDB"
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
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(datetime.today().year).astype(int)
    return df


# ============================================================
# LOGIN
# ============================================================

PASSWORD = "12345"

def check_password():
    with st.form("login"):
        st.subheader("🔐 Acceso al Dashboard Financiero")
        pwd = st.text_input("Contraseña", type="password")
        btn = st.form_submit_button("Entrar")

    if btn:
        if pwd == PASSWORD:
            st.session_state.auth = True
        else:
            st.error("Contraseña incorrecta")

    return st.session_state.get("auth", False)


st.set_page_config(page_title="Tanda Dashboard", page_icon="💸", layout="wide")

if not check_password():
    st.stop()


# ============================================================
# CARGA DE DATOS
# ============================================================

participants_df = load_participants()
calendar_df = load_calendar()

anio_actual = datetime.today().year
df_year = calendar_df[calendar_df["anio"] == anio_actual].copy()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 Dashboard Financiero")
st.sidebar.markdown("Visualización completa de la Tanda")

menu = st.sidebar.radio(
    "Selecciona sección",
    ["🏠 Inicio", "📅 Calendario", "👥 Participantes", "📊 Historial"],
)

st.sidebar.markdown("---")
st.sidebar.caption("Tanda entre Amigos — Vista Solo Lectura")


# ============================================================
# SECCIÓN: INICIO FINANCIERO
# ============================================================

if menu == "🏠 Inicio":

    st.markdown("<h1 style='text-align:center;'>💸 Dashboard Financiero</h1>", unsafe_allow_html=True)

    if not df_year.empty:

        # TOTAL BOLSA
        total_bolsa = df_year["total_a_recibir"].sum()

        # SIGUIENTE EN RECIBIR
        df_year_sorted = df_year.sort_values("fecha_pago")
        hoy = datetime.today().date()

        df_year_sorted["fecha_pago_date"] = pd.to_datetime(df_year_sorted["fecha_pago"]).dt.date
        next_row = df_year_sorted[df_year_sorted["fecha_pago_date"] >= hoy].head(1)

        # Widget 1: Bolsa
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div style="background-color:#e8f5e9;padding:25px;border-radius:15px;text-align:center;">
                <h2>💰 Bolsa del Año</h2>
                <h1 style="color:#2e7d32;">${:,.2f}</h1>
            </div>
            """.format(total_bolsa), unsafe_allow_html=True)

        # Widget 2: Participantes
        with col2:
            st.markdown(f"""
            <div style="background-color:#e3f2fd;padding:25px;border-radius:15px;text-align:center;">
                <h2>👥 Participantes</h2>
                <h1 style="color:#0277bd;">{len(participants_df)}</h1>
            </div>
            """, unsafe_allow_html=True)

        # Widget 3: Turnos pendientes
        pendientes = (df_year["estatus"] == "Pendiente").sum()
        with col3:
            st.markdown(f"""
            <div style="background-color:#fff9c4;padding:25px;border-radius:15px;text-align:center;">
                <h2>⏳ Pendientes</h2>
                <h1 style="color:#f57f17;">{pendientes}</h1>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Tarjeta: Próximo en recibir
        if not next_row.empty:
            nr = next_row.iloc[0]
            st.markdown(f"""
            <div style="background-color:#ede7f6;padding:30px;border-radius:15px;">
                <h2>🎉 Próximo en recibir su tanda</h2>
                <h1 style="font-size:36px;">{nr['nombre_participante']}</h1>
                <p><b>Fecha:</b> {nr['fecha_pago']}</p>
                <p><b>Total a recibir:</b> ${nr['total_a_recibir']:,.2f}</p>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.info("Aún no hay calendario generado para este año.")


# ============================================================
# SECCIÓN: CALENDARIO
# ============================================================

elif menu == "📅 Calendario":

    st.header("📅 Calendario del Año")

    if df_year.empty:
        st.info("No hay calendario para este año.")
    else:
        st.dataframe(
            df_year[
                ["nombre_participante", "fecha_pago", "estatus", "total_a_recibir", "notas"]
            ].sort_values("fecha_pago"),
            use_container_width=True,
        )


# ============================================================
# SECCIÓN: PARTICIPANTES
# ============================================================

elif menu == "👥 Participantes":

    st.header("👥 Lista de Participantes")

    for _, row in participants_df.iterrows():
        st.markdown(f"""
        <div style="background-color:#f5f5f5;padding:15px;border-radius:10px;margin-bottom:10px;">
            <h3>👤 {row['nombre']}</h3>
            <p><b>🎂 Cumpleaños:</b> {row['fecha_cumple']}</p>
            <p><b>📞 Teléfono:</b> {row['telefono']}</p>
            <p><b>📧 Email:</b> {row['email']}</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# SECCIÓN: HISTORIAL
# ============================================================

elif menu == "📊 Historial":

    st.header("📊 Historial Financiero")

    if df_year.empty:
        st.info("No hay historial este año.")
    else:
        completados = (df_year["estatus"] == "Completado").sum()
        st.metric("Pagos completados", completados)

        st.dataframe(
            df_year[
                ["nombre_participante", "fecha_pago", "fecha_pago_real", "estatus", "total_a_recibir"]
            ],
            use_container_width=True,
        )
