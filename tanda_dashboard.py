import streamlit as st
import pandas as pd
from datetime import datetime
from urllib.parse import urlencode, quote_plus

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

SHEET_NAME = "TandaDB"  # <-- Asegúrate que el nombre coincide
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
# LOGIN CON CONTRASEÑA (Opción A)
# ============================================================

PASSWORD = "12345"  # <-- cámbiala a lo que quieras

def check_password():
    """Pantalla de login simple."""

    with st.form("login_form"):
        st.subheader("🔐 Acceso al Dashboard de la Tanda")
        st.write("Ingresa la contraseña para ver la información.")
        pwd = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        if pwd == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("Acceso concedido 🎉")
        else:
            st.error("Contraseña incorrecta ❌")

    return st.session_state.get("authenticated", False)


# ============================================================
# CONFIG STREAMLIT
# ============================================================

st.set_page_config(page_title="Tanda Dashboard", page_icon="📱", layout="wide")


# Si no está autenticado → mostrar login
if not check_password():
    st.stop()


# ============================================================
# PORTADA / ENCABEZADO
# ============================================================

st.markdown("""
<div style='text-align:center;margin-top:10px;'>
    <h1 style='font-size:48px;margin-bottom:0;'>📱 Tanda entre Amigos</h1>
    <p style='font-size:20px;margin-top:5px;'>
        Dashboard de consulta • Solo lectura<br>
        Consulta turnos, pagos y calendario desde tu celular
    </p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# CARGA DE DATOS
# ============================================================

participants_df = load_participants()
calendar_df = load_calendar()


# ============================================================
# MENÚ PRINCIPAL (BOTONES GRANDES TIPO APP)
# ============================================================

st.markdown("## 📌 Selecciona lo que quieres ver")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📅 Calendario", use_container_width=True):
        st.session_state["view"] = "calendario"

with col2:
    if st.button("📊 Historial", use_container_width=True):
        st.session_state["view"] = "historial"

with col3:
    if st.button("👥 Participantes", use_container_width=True):
        st.session_state["view"] = "participantes"


view = st.session_state.get("view", "calendario")


# ============================================================
# FUNCIÓN PARA GENERAR LINK DE WHATSAPP
# ============================================================

MENSAJE_WHATSAPP = (
    "¡Hola! Te recordamos que mañana es tu contribución de $50 USD para la tanda. ¡Gracias!"
)

def whatsapp_link(telefono):
    if not telefono:
        return None
    mensaje = quote_plus(MENSAJE_WHATSAPP)
    return f"https://wa.me/{telefono}?text={mensaje}"


# ============================================================
# VISTA: CALENDARIO
# ============================================================

if view == "calendario":
    st.header("📅 Calendario de Pagos")

    if calendar_df.empty:
        st.info("No hay datos todavía.")
    else:
        anios = sorted(calendar_df["anio"].unique())
        anio_sel = st.selectbox("Selecciona el año", anios)

        df_year = calendar_df[calendar_df["anio"] == anio_sel].copy()
        df_year["fecha_pago"] = pd.to_datetime(
            df_year["fecha_pago"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        st.write("### Turnos del Año")
        st.dataframe(
            df_year[
                ["nombre_participante", "fecha_pago", "estatus", "fecha_pago_real", "total_a_recibir", "notas"]
            ],
            use_container_width=True,
        )

        st.write("### Enviar recordatorio por WhatsApp")
        for _, row in df_year.iterrows():
            telefono = participants_df.loc[
                participants_df["id"] == row["id_participante"], "telefono"
            ].values[0]

            wa = whatsapp_link(telefono)

            if wa:
                st.markdown(
                    f"**{row['nombre_participante']}** — "
                    f"[📲 Enviar mensaje]({wa})",
                    unsafe_allow_html=True
                )


# ============================================================
# VISTA: HISTORIAL
# ============================================================

elif view == "historial":
    st.header("📊 Historial General")

    if calendar_df.empty:
        st.info("Aún no hay historial.")
    else:
        anios = sorted(calendar_df["anio"].unique())
        anio_sel = st.selectbox("Año", anios)

        df_year = calendar_df[calendar_df["anio"] == anio_sel].copy()

        completados = (df_year["estatus"] == "Completado").sum()
        pendientes = (df_year["estatus"] == "Pendiente").sum()
        total_dinero = df_year["total_a_recibir"].sum()

        st.subheader("Resumen del Año")
        st.metric("Turnos Totales", len(df_year))
        st.metric("Pagados", completados)
        st.metric("Pendientes", pendientes)
        st.metric("Total Acumulado", f"${total_dinero:,.2f} USD")

        st.write("### Tabla Completa")
        st.dataframe(
            df_year[
                ["nombre_participante", "fecha_pago", "fecha_pago_real", "estatus", "total_a_recibir", "notas"]
            ],
            use_container_width=True,
        )


# ============================================================
# VISTA: PARTICIPANTES
# ============================================================

elif view == "participantes":
    st.header("👥 Lista de Participantes")

    st.dataframe(
        participants_df[["nombre", "fecha_cumple", "telefono", "email", "notas"]],
        use_container_width=True,
    )
