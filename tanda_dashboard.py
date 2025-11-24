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
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(
        datetime.today().year
    ).astype(int)
    return df


# ============================================================
# LOGIN CON PIN (y se oculta tras entrar)
# ============================================================

PASSWORD = "12345"  # cámbiala si quieres

def check_password():
    # Si ya está autenticado, no mostramos el login
    if st.session_state.get("auth", False):
        return True

    st.title("🔐 Acceso al Dashboard Financiero")

    with st.form("login_form"):
        pwd = st.text_input("PIN de acceso", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        if pwd == PASSWORD:
            st.session_state["auth"] = True
            st.experimental_rerun()
        else:
            st.error("PIN incorrecto")

    return False


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

# Procesar fechas
if not df_year.empty:
    df_year["fecha_pago_dt"] = pd.to_datetime(df_year["fecha_pago"], errors="coerce")
else:
    df_year["fecha_pago_dt"] = pd.NaT


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 Dashboard de la Tanda")
st.sidebar.markdown("Navega por la información financiera de la tanda.")

menu = st.sidebar.radio(
    "Secciones",
    ["🏠 Inicio", "📅 Calendario", "👥 Participantes", "📊 Historial"],
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Año actual: {anio_actual}")


# ============================================================
# SECCIÓN: INICIO (vista financiera con iconos pequeños)
# ============================================================

if menu == "🏠 Inicio":
    st.markdown("<h1 style='text-align:center;'>💸 Dashboard Financiero de la Tanda</h1>", unsafe_allow_html=True)
    st.write("")

    # Métricas rápidas con iconos pequeños
    col1, col2, col3 = st.columns(3)

    # 👥 Número de participantes
    num_participants = len(participants_df)
    with col1:
        st.markdown(
            f"""
            <div style="background-color:#f5f5f5;padding:10px 15px;border-radius:10px; text-align:center;">
                <div style="font-size:28px;">👥</div>
                <div style="font-size:14px;color:#555;">Participantes</div>
                <div style="font-size:22px;font-weight:bold;">{num_participants}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 💵 Monto que recibe cada uno (tanda por cumpleañero)
    if not df_year.empty:
        monto_por_persona = df_year["total_a_recibir"].iloc[0]
    else:
        monto_por_persona = 0.0

    with col2:
        st.markdown(
            f"""
            <div style="background-color:#f5f5f5;padding:10px 15px;border-radius:10px; text-align:center;">
                <div style="font-size:28px;">💵</div>
                <div style="font-size:14px;color:#555;">Monto por cumpleañero</div>
                <div style="font-size:22px;font-weight:bold;">${monto_por_persona:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 💰 Bolsa total del año (suma total_a_recibir)
    if not df_year.empty:
        bolsa_total = df_year["total_a_recibir"].sum()
    else:
        bolsa_total = 0.0

    with col3:
        st.markdown(
            f"""
            <div style="background-color:#f5f5f5;padding:10px 15px;border-radius:10px; text-align:center;">
                <div style="font-size:28px;">💰</div>
                <div style="font-size:14px;color:#555;">Bolsa acumulada del año</div>
                <div style="font-size:22px;font-weight:bold;">${bolsa_total:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Tarjeta: Próximo en recibir por cumpleaños / fecha de pago
    st.subheader("🎉 Próximo en recibir su tanda")

    if not df_year.empty:
        hoy = datetime.today().date()
        df_future = df_year[df_year["fecha_pago_dt"].dt.date >= hoy].sort_values("fecha_pago_dt")

        if not df_future.empty:
            nr = df_future.iloc[0]
        else:
            # Si ya pasaron todos, mostramos el último del año
            nr = df_year.sort_values("fecha_pago_dt").iloc[-1]

        st.markdown(
            f"""
            <div style="background-color:#e8f5e9;padding:20px;border-radius:15px;">
                <h2 style="margin-top:0;">🎂 {nr['nombre_participante']}</h2>
                <p><b>Fecha de pago:</b> {nr['fecha_pago_dt'].strftime('%Y-%m-%d')}</p>
                <p><b>Monto que recibirá:</b> ${nr['total_a_recibir']:,.2f}</p>
                <p><b>Estatus:</b> {nr['estatus']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Todavía no hay calendario generado para este año.")


# ============================================================
# SECCIÓN: CALENDARIO
# ============================================================

elif menu == "📅 Calendario":
    st.header("📅 Calendario de pagos de la tanda")

    if df_year.empty:
        st.info("No hay calendario registrado para este año.")
    else:
        df_view = df_year.copy()
        df_view["fecha_pago"] = df_view["fecha_pago_dt"].dt.strftime("%Y-%m-%d")

        st.dataframe(
            df_view[
                [
                    "nombre_participante",
                    "fecha_pago",
                    "estatus",
                    "total_a_recibir",
                    "notas",
                ]
            ].sort_values("fecha_pago"),
            use_container_width=True,
        )


# ============================================================
# SECCIÓN: PARTICIPANTES
# ============================================================

elif menu == "👥 Participantes":
    st.header("👥 Lista de participantes")

    if participants_df.empty:
        st.info("Aún no hay participantes registrados.")
    else:
        for _, row in participants_df.iterrows():
            st.markdown(
                f"""
                <div style="background-color:#f9f9f9;padding:12px 15px;border-radius:10px;margin-bottom:8px;">
                    <div style="font-size:20px;font-weight:bold;">👤 {row['nombre']}</div>
                    <div><b>🎂 Cumpleaños:</b> {row['fecha_cumple']}</div>
                    <div><b>📞 Teléfono:</b> {row['telefono']}</div>
                    <div><b>📧 Email:</b> {row['email']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# SECCIÓN: HISTORIAL
# ============================================================

elif menu == "📊 Historial":
    st.header("📊 Historial financiero del año")

    if df_year.empty:
        st.info("No hay historial registrado para este año.")
    else:
        completados = (df_year["estatus"] == "Completado").sum()
        pendientes = (df_year["estatus"] == "Pendiente").sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pagos completados", completados)
        with col2:
            st.metric("Pagos pendientes", pendientes)

        df_hist = df_year.copy()
        df_hist["fecha_pago"] = df_hist["fecha_pago_dt"].dt.strftime("%Y-%m-%d")
        st.subheader("Detalle de turnos")
        st.dataframe(
            df_hist[
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
