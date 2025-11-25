import streamlit as st
import pandas as pd
from datetime import datetime

from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe

# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(page_title="Tanda de cumpleaños", page_icon="💸", layout="wide")

# Título centrado
st.markdown(
    "<h1 style='text-align:center;'>💸 Tanda de cumpleaños</h1>",
    unsafe_allow_html=True,
)

# ============================================================
# OCULTAR MENÚ Y FOOTER, ICONOS DE LA DERECHA + CSS GLOBAL
# ============================================================
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        div[data-testid="stToolbar"] { display: none !important; }

        /* Animación global para la barra de progreso de la tanda */
        @keyframes tandaProgress {
            0%   { width: 0%; }
            50%  { width: 91%; }
            100% { width: 0%; }
        }
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
    "pagos_detalle",
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
# LOGIN CON PIN (SOLO LECTURA)
# ============================================================

PASSWORD = "1111"  # PIN para tus amigos

def check_password():
    if st.session_state.get("auth_dashboard", False):
        return True

    st.subheader("🔐 Acceso a la Tanda")

    with st.form("login_form_dashboard"):
        pwd = st.text_input("PIN de acceso", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        if pwd == PASSWORD:
            st.session_state["auth_dashboard"] = True
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

# Selección automática del año más reciente
if available_years:
    selected_year = max(available_years)
else:
    selected_year = None
    st.warning("Todavía no hay calendario cargado en Google Sheets.")

# Filtrar por año seleccionado
if selected_year is not None:
    df_year = calendar_df[calendar_df["anio"] == selected_year].copy()
    if not df_year.empty:
        df_year["fecha_pago_dt"] = pd.to_datetime(
            df_year["fecha_pago"], errors="coerce"
        )
    else:
        df_year["fecha_pago_dt"] = pd.NaT
else:
    df_year = pd.DataFrame(columns=COLS_CALENDARIO)
    df_year["fecha_pago_dt"] = pd.NaT

st.markdown("---")

# ============================================================
# TARJETAS RESUMEN
# ============================================================

col1, col2, col3 = st.columns(3)

# 👥 Participantes
num_participants = len(participants_df)
with col1:
    st.markdown(
        f"""
        <div style="background-color:#111827;padding:10px 15px;border-radius:10px;
                    text-align:center;border:1px solid #374151;">
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
        <div style="background-color:#111827;padding:10px 15px;border-radius:10px;
                    text-align:center;border:1px solid #374151;">
            <div style="font-size:24px;">💸</div>
            <div style="font-size:13px;color:#9CA3AF;">Aporte por persona</div>
            <div style="font-size:22px;font-weight:bold;color:white;">
                ${aporte_por_persona:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 💰 Monto por cumpleañero
if not df_year.empty:
    monto_por_cumpleanero = float(df_year["total_a_recibir"].iloc[0])
else:
    monto_por_cumpleanero = 0.0

with col3:
    st.markdown(
        f"""
        <div style="background-color:#111827;padding:10px 15px;border-radius:10px;
                    text-align:center;border:1px solid #374151;">
            <div style="font-size:24px;">💰</div>
            <div style="font-size:13px;color:#9CA3AF;">Monto por cumpleañero</div>
            <div style="font-size:22px;font-weight:bold;color:white;">
                ${monto_por_cumpleanero:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ============================================================
# PRÓXIMO EN RECIBIR
# ============================================================

st.subheader("🎉 Próximo en recibir su tanda")

if not df_year.empty:
    hoy = datetime.today().date()

    df_year["fecha_pago_dt"] = pd.to_datetime(df_year["fecha_pago_dt"], errors="coerce")

    futuros = df_year[
        df_year["fecha_pago_dt"].notna()
        & (df_year["fecha_pago_dt"].dt.date >= hoy)
    ].sort_values("fecha_pago_dt")

    if not futuros.empty:
        nr = futuros.iloc[0]
    else:
        df_valid = df_year[df_year["fecha_pago_dt"].notna()].sort_values("fecha_pago_dt")
        if not df_valid.empty:
            nr = df_valid.iloc[-1]
        else:
            nr = df_year.iloc[0]

    if not pd.isna(nr["fecha_pago_dt"]):
        fecha_pago_dt = nr["fecha_pago_dt"]
        fecha_str = fecha_pago_dt.strftime("%Y-%m-%d")
        mes_pago = fecha_pago_dt.month
    else:
        fecha_str = str(nr["fecha_pago"])
        mes_pago = hoy.month  # fallback

    # Tarjeta principal
    st.markdown(
        f"""
        <div style="background-color:#111827;padding:20px;border-radius:15px;
                    border:1px solid #374151;">
            <h2 style="margin-top:0;color:white;">🎂 {nr['nombre_participante']}</h2>
            <p style="color:#D1D5DB;"><b>Fecha de pago:</b> {fecha_str}</p>
            <p style="color:#D1D5DB;"><b>Monto a recibir:</b>
                ${float(nr['total_a_recibir']):,.2f}</p>
            <p style="color:#D1D5DB;"><b>Estatus:</b> {nr['estatus']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # BARRA ANIMADA 0% → 91% → 0% (SIN PORCENTAJE) + NICKNAME
    # CON FRASE SEGÚN MES
    # =====================================================

    # Intentar obtener nickname desde participantes (campo notas)
    nickname = ""
    try:
        pid = int(nr.get("id_participante", 0))
        p_row = participants_df[participants_df["id"] == pid]
        if not p_row.empty:
            nickname = str(p_row.iloc[0].get("notas", "")).strip()
    except Exception:
        nickname = ""

    # Fallbacks de nickname
    if nickname == "":
        nickname = str(nr.get("notas", "")).strip()
    if nickname == "":
        nickname = nr["nombre_participante"]

    # Frase según el mes del pago
    def frase_por_mes(mes: int) -> str:
        if mes == 1:
            return "arrancamos el año con tu tanda... ya viene la lana 💸🎉"
        elif mes == 6:
            return "tu mitad de año viene con billete 😉"
        elif mes == 12:
            return "¡cierre de año y lana asegurada! 🎄💰"
        else:
            return "tu cumpleaños se acerca... ya viene la lana 💸"

    frase_mes = frase_por_mes(mes_pago)

    # Barra animada simple (sin porcentaje visible)
    st.markdown(
        f"""
        <div style="margin-top:14px;margin-bottom:4px;">
            <div style="color:#D1D5DB;font-size:14px;margin-bottom:6px;">
                <b>{nickname}</b>, {frase_mes}
            </div>
            <div style="
                background-color:#374151;
                border-radius:9999px;
                overflow:hidden;
                height:16px;
                position:relative;
            ">
                <div style="
                    height:100%;
                    background:linear-gradient(90deg,#22c55e,#16a34a);
                    animation:tandaProgress 12s ease-in-out infinite;
                    box-shadow:0 0 10px #22c55e,0 0 20px #22c55e,0 0 30px #16a34a;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

else:
    st.info("Todavía no hay calendario generado para el año actual de la tanda.")

st.markdown("---")

# ============================================================
# CALENDARIO DE PAGOS COMO TARJETAS
# ============================================================

st.subheader("📅 Calendario de pagos")

if df_year.empty:
    st.info("No hay calendario para el año actual de la tanda.")
else:
    df_calendar_sorted = df_year.copy()
    df_calendar_sorted["fecha_pago_dt"] = pd.to_datetime(
        df_calendar_sorted["fecha_pago_dt"], errors="coerce"
    )
    df_calendar_sorted = df_calendar_sorted.sort_values("fecha_pago_dt")

    for _, row in df_calendar_sorted.iterrows():
        if not pd.isna(row["fecha_pago_dt"]):
            fecha_str = row["fecha_pago_dt"].strftime("%Y-%m-%d")
        else:
            fecha_str = str(row["fecha_pago"])

        st.markdown(
            f"""
            <div style="background-color:#111827;padding:12px 15px;border-radius:10px;
                        margin-bottom:8px;border:1px solid #374151;">
                <div style="font-size:16px;font-weight:bold;color:white;">
                    📆 {row['nombre_participante']}
                </div>
                <div style="color:#D1D5DB;">
                    <b>Fecha de pago:</b> {fecha_str}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")

# ============================================================
# LISTA DE PARTICIPANTES
# ============================================================

st.subheader("👥 Participantes")

if participants_df.empty:
    st.info("Aún no hay participantes registrados.")
else:
    items = []
    for _, row in participants_df.iterrows():
        nickname_p = str(row.get("notas", "")).strip()
        if nickname_p == "":
            nickname_p = "-"
        items.append(f"<li>{row['nombre']} — {nickname_p}</li>")

    lista_html = (
        "<ul style='color:#D1D5DB;font-size:16px;margin:0;padding-left:20px;'>"
        + "".join(items)
        + "</ul>"
    )

    st.markdown(
        f"""
        <div style="
            background-color:#111827;
            padding:16px 18px;
            border-radius:12px;
            border:1px solid #374151;
        ">
            <h4 style="color:white;margin-top:0;margin-bottom:10px;">
                👥 Participantes
            </h4>
            {lista_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ============================================================
# HISTORIAL: DOS TARJETAS (RECIBIERON / PENDIENTES)
# ============================================================

st.subheader("📜 Historial de la tanda")

if df_year.empty:
    st.info("No hay historial para el año actual de la tanda.")
else:
    df_hist = df_year.copy()
    df_hist["fecha_pago_dt"] = pd.to_datetime(df_hist["fecha_pago_dt"], errors="coerce")

    recibieron = df_hist[df_hist["estatus"] == "Completado"].sort_values(
        "fecha_pago_dt"
    )
    pendientes = df_hist[df_hist["estatus"] == "Pendiente"].sort_values(
        "fecha_pago_dt"
    )

    col_r, col_p = st.columns(2)

    # ✅ Ya recibieron
    with col_r:
        if recibieron.empty:
            contenido_r = "<p style='color:#D1D5DB;'>— Ninguno todavía.</p>"
        else:
            items_r = []
            for _, row in recibieron.iterrows():
                if not pd.isna(row["fecha_pago_dt"]):
                    fecha_str = row["fecha_pago_dt"].strftime("%Y-%m-%d")
                else:
                    fecha_str = str(row["fecha_pago"])
                items_r.append(f"<li>{row['nombre_participante']} — {fecha_str}</li>")
            contenido_r = "<ul style='color:#D1D5DB;'>" + "".join(items_r) + "</ul>"

        st.markdown(
            f"""
            <div style="background-color:#111827;padding:15px;border-radius:15px;
                        border:1px solid #374151; min-height:150px;">
                <h3 style="color:white;margin-top:0;">✅ Ya recibieron su tanda</h3>
                {contenido_r}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ⏳ Pendientes
    with col_p:
        if pendientes.empty:
            contenido_p = "<p style='color:#D1D5DB;'>— Ninguno pendiente.</p>"
        else:
            items_p = []
            for _, row in pendientes.iterrows():
                if not pd.isna(row["fecha_pago_dt"]):
                    fecha_str = row["fecha_pago_dt"].strftime("%Y-%m-%d")
                else:
                    fecha_str = str(row["fecha_pago"])
                items_p.append(f"<li>{row['nombre_participante']} — {fecha_str}</li>")
            contenido_p = "<ul style='color:#D1D5DB;'>" + "".join(items_p) + "</ul>"

        st.markdown(
            f"""
            <div style="background-color:#111827;padding:15px;border-radius:15px;
                        border:1px solid #374151; min-height:150px;">
                <h3 style="color:white;margin-top:0;">⏳ Pendientes por recibir</h3>
                {contenido_p}
            </div>
            """,
            unsafe_allow_html=True,
        )

# ============================================================
# FRASE MOTIVACIONAL FINAL
# ============================================================

st.markdown("---")

st.markdown(
    """
    <div style="
        text-align:center;
        margin-top:20px;
        margin-bottom:10px;
        color:#D1D5DB;
        font-size:16px;
        background-color:#111827;
        padding:15px;
        border-radius:12px;
        border:1px solid #374151;
    ">
        🌟 "Cada aporte es un recordatorio de que las mejores celebraciones
        se construyen juntos. ¡Gracias por ser parte de esta tanda!" 🌟
    </div>
    """,
    unsafe_allow_html=True,
)
