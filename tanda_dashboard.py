import streamlit as st
import pandas as pd
from datetime import datetime

from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe

# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(page_title="Tanda Dashboard", page_icon="💸", layout="wide")

# ============================================================
# OCULTAR MENÚ Y FOOTER, PERO DEJAR HEADER (HAMBURGUER) VISIBLE
# ============================================================
hide_streamlit_style = """
    <style>
        /* Oculta el menú principal de Streamlit (arriba Izq en desktop) */
        #MainMenu {visibility: hidden !important;}

        /* Oculta el pie de página "Made with Streamlit" */
        footer {visibility: hidden !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


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
# LOGIN CON PIN
# ============================================================

PASSWORD = "12345"  # puedes cambiarlo

def check_password():
    # Si ya está autenticado, no mostramos login
    if st.session_state.get("auth", False):
        return True

    st.title("🔐 Acceso al Dashboard Financiero")

    with st.form("login_form"):
        pwd = st.text_input("PIN de acceso", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        if pwd == PASSWORD:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("PIN incorrecto")

    return False


if not check_password():
    st.stop()


# ============================================================
# CARGA DE DATOS
# ============================================================

participants_df = load_participants()
calendar_df = load_calendar()

if not calendar_df.empty:
    available_years = sorted(calendar_df["anio"].unique())
else:
    available_years = []


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 Dashboard de la Tanda")

if available_years:
    default_year = max(available_years)
    selected_year = st.sidebar.selectbox(
        "Año de la tanda",
        options=available_years,
        index=available_years.index(default_year),
    )
else:
    selected_year = None

menu = st.sidebar.radio(
    "Secciones",
    ["🏠 Inicio", "📅 Calendario", "👥 Participantes", "📊 Historial"],
)

st.sidebar.markdown("---")
if selected_year:
    st.sidebar.caption(f"Año seleccionado: {selected_year}")
else:
    st.sidebar.caption("Sin calendario aún.")


# Filtrar por año
if selected_year is not None:
    df_year = calendar_df[calendar_df["anio"] == selected_year].copy()
    if not df_year.empty:
        df_year["fecha_pago_dt"] = pd.to_datetime(df_year["fecha_pago"], errors="coerce")
    else:
        df_year["fecha_pago_dt"] = pd.NaT
else:
    df_year = pd.DataFrame(columns=COLS_CALENDARIO)
    df_year["fecha_pago_dt"] = pd.NaT


# ============================================================
# SECCIÓN: INICIO
# ============================================================

if menu == "🏠 Inicio":
    st.markdown(
        "<h1 style='text-align:center;'>💸 Dashboard Financiero de la Tanda</h1>",
        unsafe_allow_html=True,
    )
    st.write("")

    # Tarjetas pequeñas con iconos
    col1, col2, col3 = st.columns(3)

    # 👥 Participantes
    num_participants = len(participants_df)
    with col1:
        st.markdown(
            f"""
            <div style="background-color:#111827;padding:10px 15px;border-radius:10px; text-align:center;border:1px solid #374151;">
                <div style="font-size:24px;">👥</div>
                <div style="font-size:13px;color:#9CA3AF;">Participantes</div>
                <div style="font-size:22px;font-weight:bold;color:white;">{num_participants}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 💸 Aporte por persona
    if not df_year.empty:
        aporte_por_persona = float(df_year["monto_por_persona"].iloc[0])
    else:
        aporte_por_persona = 0.0

    with col2:
        st.markdown(
            f"""
            <div style="background-color:#111827;padding:10px 15px;border-radius:10px; text-align:center;border:1px solid #374151;">
                <div style="font-size:24px;">💸</div>
                <div style="font-size:13px;color:#9CA3AF;">Aporte por persona</div>
                <div style="font-size:22px;font-weight:bold;color:white;">${aporte_por_persona:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 💰 Monto que recibe cada cumpleañero
    if not df_year.empty:
        monto_por_cumpleanero = float(df_year["total_a_recibir"].iloc[0])
    else:
        monto_por_cumpleanero = 0.0

    with col3:
        st.markdown(
            f"""
            <div style="background-color:#111827;padding:10px 15px;border-radius:10px; text-align:center;border:1px solid #374151;">
                <div style="font-size:24px;">💰</div>
                <div style="font-size:13px;color:#9CA3AF;">Monto por cumpleañero</div>
                <div style="font-size:22px;font-weight:bold;color:white;">${monto_por_cumpleanero:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Próximo en recibir
    st.subheader("🎉 Próximo en recibir su tanda")

    if not df_year.empty:
        hoy = datetime.today().date()
        futuros = df_year[df_year["fecha_pago_dt"].dt.date >= hoy].sort_values("fecha_pago_dt")

        if not futuros.empty:
            nr = futuros.iloc[0]
        else:
            nr = df_year.sort_values("fecha_pago_dt").iloc[-1]

        fecha_str = (
            nr["fecha_pago_dt"].strftime("%Y-%m-%d")
            if not pd.isna(nr["fecha_pago_dt"])
            else nr["fecha_pago"]
        )

        st.markdown(
            f"""
            <div style="background-color:#111827;padding:20px;border-radius:15px;border:1px solid #374151;">
                <h2 style="margin-top:0;color:white;">🎂 {nr['nombre_participante']}</h2>
                <p style="color:#D1D5DB;"><b>Fecha de pago:</b> {fecha_str}</p>
                <p style="color:#D1D5DB;"><b>Monto a recibir:</b> ${float(nr['total_a_recibir']):,.2f}</p>
                <p style="color:#D1D5DB;"><b>Estatus:</b> {nr['estatus']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Todavía no hay calendario generado para el año seleccionado.")


# ============================================================
# SECCIÓN: CALENDARIO
# ============================================================

elif menu == "📅 Calendario":
    st.header("📅 Calendario de pagos")

    if df_year.empty:
        st.info("No hay calendario para el año seleccionado.")
    else:
        df_view = df_year.copy()
        df_view["fecha_pago"] = pd.to_datetime(
            df_view["fecha_pago"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        st.dataframe(
            df_view[
                [
                    "nombre_participante",
                    "fecha_pago",
                    "monto_por_persona",
                    "total_a_recibir",
                    "estatus",
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
                <div style="background-color:#111827;padding:12px 15px;border-radius:10px;margin-bottom:8px;border:1px solid #374151;">
                    <div style="font-size:18px;font-weight:bold;color:white;">👤 {row['nombre']}</div>
                    <div style="color:#D1D5DB;"><b>🎂 Cumpleaños:</b> {row['fecha_cumple']}</div>
                    <div style="color:#D1D5DB;"><b>📞 Teléfono:</b> {row['telefono']}</div>
                    <div style="color:#D1D5DB;"><b>📧 Email:</b> {row['email']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# SECCIÓN: HISTORIAL
# ============================================================

elif menu == "📊 Historial":
    st.header("📊 Historial financiero")

    if df_year.empty:
        st.info("No hay historial para el año seleccionado.")
    else:
        completados = (df_year["estatus"] == "Completado").sum()
        pendientes = (df_year["estatus"] == "Pendiente").sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pagos completados", completados)
        with col2:
            st.metric("Pagos pendientes", pendientes)

        df_hist = df_year.copy()
        df_hist["fecha_pago"] = pd.to_datetime(
            df_hist["fecha_pago"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

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
