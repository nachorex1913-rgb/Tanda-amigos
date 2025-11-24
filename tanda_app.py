def load_participants():
    df = get_as_dataframe(sheet_participantes, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")
    df = df.fillna("")
    return df

def save_participants(df):
    sheet_participantes.clear()
    set_with_dataframe(sheet_participantes, df)

def load_calendar():
    df = get_as_dataframe(sheet_calendario, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")
    df = df.fillna("")
    return df

def save_calendar(df):
    sheet_calendario.clear()
    set_with_dataframe(sheet_calendario, df)
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Alcances necesarios para Sheets + Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Cargar credenciales desde secrets de Streamlit
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

# Conectar a Google Sheets
client = gspread.authorize(creds)

# Abrir archivo por nombre
SHEET_NAME = "TandaDB"  # <-- pon el nombre exacto de tu Sheet
spreadsheet = client.open(SHEET_NAME)

# Hojas
sheet_participantes = spreadsheet.worksheet("participantes")
sheet_calendario = spreadsheet.worksheet("calendario")
import os
from datetime import datetime

import pandas as pd
from dateutil.parser import parse as parse_date
import streamlit as st

# Archivos donde se guarda todo
PARTICIPANTS_FILE = "participantes_tanda.csv"
CALENDAR_FILE = "calendario_tanda.csv"


# =============== FUNCIONES DE DATOS ===================

def ensure_columns(df, columns_with_defaults):
    """Asegura que el DataFrame tenga todas las columnas necesarias."""
    for col, default in columns_with_defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


def load_participants():
    """Carga o crea el archivo de participantes."""
    if os.path.exists(PARTICIPANTS_FILE):
        df = pd.read_csv(PARTICIPANTS_FILE)
    else:
        df = pd.DataFrame()

    cols = {
        "id": None,
        "nombre": "",
        "fecha_cumple": "",
        "telefono": "",
        "email": "",
        "notas": "",
    }
    df = ensure_columns(df, cols)

    # Si no hay IDs, los generamos
    if df["id"].isna().all():
        df["id"] = range(1, len(df) + 1)

    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    return df[list(cols.keys())]


def save_participants(df):
    df.to_csv(PARTICIPANTS_FILE, index=False)


def load_calendar():
    """Carga o crea el archivo del calendario de la tanda."""
    if os.path.exists(CALENDAR_FILE):
        df = pd.read_csv(CALENDAR_FILE)
    else:
        df = pd.DataFrame()

    cols = {
        "id": None,
        "anio": datetime.today().year,
        "id_participante": None,
        "nombre_participante": "",
        "fecha_pago": "",
        "monto_por_persona": 0.0,
        "total_a_recibir": 0.0,
        "estatus": "Pendiente",
        "fecha_pago_real": "",
        "notas": "",
    }
    df = ensure_columns(df, cols)

    if df["id"].isna().all():
        df["id"] = range(1, len(df) + 1)

    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    return df[list(cols.keys())]


def save_calendar(df):
    df.to_csv(CALENDAR_FILE, index=False)


def generate_new_id(df):
    """Genera un nuevo ID incremental para una tabla."""
    if df.empty:
        return 1
    max_id = pd.to_numeric(df["id"], errors="coerce").fillna(0).max()
    return int(max_id) + 1


def safe_parse_date(texto):
    """Intenta interpretar una fecha escrita de forma flexible."""
    try:
        return parse_date(texto, dayfirst=True)
    except Exception:
        return None


# =============== CONFIGURACIÓN STREAMLIT ===================

st.set_page_config(page_title="Tanda entre amigos", page_icon="🎉", layout="wide")
st.title("🎉 Tanda entre amigos")


# Cargar datos al iniciar
participants_df = load_participants()
calendar_df = load_calendar()


# =============== PESTAÑAS PRINCIPALES ===================

tab_part, tab_cal, tab_hist = st.tabs(["Participantes", "Calendario", "Historial"])


# =============== TAB: PARTICIPANTES ===================

with tab_part:
    st.header("Participantes")

    col_form, col_list = st.columns([1, 2])

    with col_form:
        mode = st.radio("Modo", ["Agregar", "Editar"], horizontal=True)

        if mode == "Editar" and not participants_df.empty:
            pid = st.selectbox(
                "Selecciona participante",
                participants_df["id"].tolist(),
                format_func=lambda x: participants_df.loc[
                    participants_df["id"] == x, "nombre"
                ].values[0],
            )
            row = participants_df[participants_df["id"] == pid].iloc[0]
        else:
            pid = None
            row = {"nombre": "", "fecha_cumple": "", "telefono": "", "email": "", "notas": ""}

        nombre = st.text_input("Nombre completo", row["nombre"])
        fecha_cumple = st.text_input(
            "Fecha de cumpleaños (ej. 15/04/1990)", row["fecha_cumple"]
        )
        telefono = st.text_input("Teléfono", row["telefono"])
        email = st.text_input("Email", row["email"])
        notas = st.text_area("Notas", row["notas"])

        if st.button("Guardar participante"):
            if not nombre.strip():
                st.warning("El nombre es obligatorio.")
            else:
                fecha_clean = fecha_cumple.strip()
                if fecha_clean:
                    d = safe_parse_date(fecha_clean)
                    if not d:
                        st.error("La fecha de cumpleaños no es válida.")
                        st.stop()
                    fecha_clean = d.strftime("%Y-%m-%d")

                if mode == "Agregar":
                    new_id = generate_new_id(participants_df)
                    new_row = {
                        "id": new_id,
                        "nombre": nombre.strip(),
                        "fecha_cumple": fecha_clean,
                        "telefono": telefono.strip(),
                        "email": email.strip(),
                        "notas": notas.strip(),
                    }
                    participants_df = pd.concat(
                        [participants_df, pd.DataFrame([new_row])],
                        ignore_index=True,
                    )
                    save_participants(participants_df)
                    st.success("Participante agregado.")
                else:
                    participants_df.loc[participants_df["id"] == pid, "nombre"] = nombre.strip()
                    participants_df.loc[participants_df["id"] == pid, "fecha_cumple"] = fecha_clean
                    participants_df.loc[participants_df["id"] == pid, "telefono"] = telefono.strip()
                    participants_df.loc[participants_df["id"] == pid, "email"] = email.strip()
                    participants_df.loc[participants_df["id"] == pid, "notas"] = notas.strip()
                    save_participants(participants_df)
                    st.success("Participante actualizado.")

        if mode == "Editar" and pid is not None:
            if st.button("Eliminar participante"):
                participants_df = participants_df[participants_df["id"] != pid]
                save_participants(participants_df)
                st.warning("Participante eliminado. Revisa el calendario si ya tenía turno.")

    with col_list:
        st.subheader("Lista de participantes")
        if participants_df.empty:
            st.info("Aún no hay participantes registrados.")
        else:
            st.dataframe(participants_df, use_container_width=True)


# =============== TAB: CALENDARIO ===================

with tab_cal:
    st.header("Calendario de la tanda")

    if participants_df.empty:
        st.info("Primero agrega participantes.")
    else:
        col_left, col_right = st.columns([1, 2])

        with col_left:
            anio = st.number_input(
                "Año de la tanda",
                min_value=2000,
                max_value=2100,
                value=datetime.today().year,
                step=1,
            )
            monto = st.number_input(
                "Monto que aporta cada persona (USD)",
                min_value=1.0,
                value=50.0,
                step=1.0,
            )
            st.caption(
                "El total que recibe cada cumpleañero será: (número de amigos - 1) × monto por persona."
            )

            if st.button("Generar / regenerar calendario"):
                valid = []
                for _, p in participants_df.iterrows():
                    if p["fecha_cumple"]:
                        d = safe_parse_date(p["fecha_cumple"])
                        if d:
                            valid.append(
                                {
                                    "id": int(p["id"]),
                                    "nombre": p["nombre"],
                                    "mes": d.month,
                                    "dia": d.day,
                                }
                            )

                if not valid:
                    st.error("Ningún participante tiene fecha de cumpleaños válida.")
                else:
                    valid = sorted(valid, key=lambda x: (x["mes"], x["dia"]))
                    n = len(participants_df)
                    total = (n - 1) * monto

                    # Quitamos cualquier calendario previo de ese año
                    calendar_df = calendar_df[calendar_df["anio"] != anio]

                    new_rows = []
                    for v in valid:
                        fecha_pago = datetime(anio, v["mes"], v["dia"]).strftime("%Y-%m-%d")
                        rid = generate_new_id(calendar_df)
                        new_rows.append(
                            {
                                "id": rid,
                                "anio": anio,
                                "id_participante": v["id"],
                                "nombre_participante": v["nombre"],
                                "fecha_pago": fecha_pago,
                                "monto_por_persona": monto,
                                "total_a_recibir": total,
                                "estatus": "Pendiente",
                                "fecha_pago_real": "",
                                "notas": "",
                            }
                        )

                    calendar_df = pd.concat(
                        [calendar_df, pd.DataFrame(new_rows)], ignore_index=True
                    )
                    save_calendar(calendar_df)
                    st.success(f"Calendario generado para {anio}.")

        with col_right:
            year_df = calendar_df[calendar_df["anio"] == anio].copy()

            if year_df.empty:
                st.info("No hay calendario para este año.")
            else:
                year_df["fecha_pago"] = pd.to_datetime(
                    year_df["fecha_pago"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")

                st.caption(
                    "Puedes editar el estatus, la fecha real de pago y las notas directamente en la tabla."
                )

                editable = year_df[
                    [
                        "id",
                        "nombre_participante",
                        "fecha_pago",
                        "monto_por_persona",
                        "total_a_recibir",
                        "estatus",
                        "fecha_pago_real",
                        "notas",
                    ]
                ]

                edited = st.data_editor(
                    editable,
                    num_rows="fixed",
                    use_container_width=True,
                )

                if st.button("Guardar cambios del calendario"):
                    # Aseguramos tipos de ID
                    calendar_df["id"] = pd.to_numeric(calendar_df["id"], errors="coerce").astype("Int64")
                    edited["id"] = pd.to_numeric(edited["id"], errors="coerce").astype("Int64")

                    for _, r in edited.iterrows():
                        if pd.isna(r["id"]):
                            continue
                        mask = calendar_df["id"] == r["id"]
                        if not mask.any():
                            continue

                        estatus = str(r.get("estatus", "") or "").strip()
                        notas_val = str(r.get("notas", "") or "").strip()
                        fecha_real = str(r.get("fecha_pago_real", "") or "").strip()

                        calendar_df.loc[mask, "estatus"] = estatus
                        calendar_df.loc[mask, "notas"] = notas_val

                        if fecha_real:
                            calendar_df.loc[mask, "fecha_pago_real"] = fecha_real
                        else:
                            if estatus == "Completado":
                                calendar_df.loc[mask, "fecha_pago_real"] = datetime.today().strftime(
                                    "%Y-%m-%d"
                                )

                    save_calendar(calendar_df)
                    st.success("Cambios guardados.")

# =============== TAB: HISTORIAL ===================

with tab_hist:
    st.header("Historial y resumen")

    if calendar_df.empty:
        st.info("Aún no hay información de calendario.")
    else:
        anios = sorted(calendar_df["anio"].unique())
        anio_sel = st.selectbox("Selecciona año", anios)

        df_year = calendar_df[calendar_df["anio"] == anio_sel].copy()

        if df_year.empty:
            st.info("No hay registros para ese año.")
        else:
            total_turnos = len(df_year)
            total_completos = (df_year["estatus"] == "Completado").sum()
            total_pend = (df_year["estatus"] == "Pendiente").sum()
            dinero_total = df_year["total_a_recibir"].sum()

            st.subheader("Resumen general")
            st.write(f"Turnos en la tanda: **{total_turnos}**")
            st.write(f"Completados: **{total_completos}**")
            st.write(f"Pendientes: **{total_pend}**")
            st.write(f"Dinero total del año: **${dinero_total:,.2f} USD**")

            st.subheader("Por participante")
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

            st.subheader("Detalle de turnos")
            df_year["fecha_pago"] = pd.to_datetime(
                df_year["fecha_pago"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")
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
