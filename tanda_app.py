import pandas as pd
import streamlit as st
from datetime import datetime
from dateutil.parser import parse as parse_date

from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe


# ============================================================
# CONFIG: GOOGLE SHEETS
# ============================================================

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
SHEET_NAME = "TandaDB"  # cambia esto si tu Sheet se llama diferente
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
    """Asegura que el DataFrame tenga todas las columnas."""
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df[columns]


def load_participants():
    """Carga participantes desde Google Sheets."""
    df = get_as_dataframe(sheet_participantes, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

    if df.empty:
        df = pd.DataFrame(columns=COLS_PARTICIPANTES)

    df = ensure_columns(df.fillna(""), COLS_PARTICIPANTES)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)

    return df


def save_participants(df):
    df_to_save = ensure_columns(df.copy(), COLS_PARTICIPANTES).fillna("")
    sheet_participantes.clear()
    set_with_dataframe(
        sheet_participantes,
        df_to_save,
        include_index=False,
        include_column_header=True,
    )


def load_calendar():
    """Carga calendario desde Google Sheets."""
    df = get_as_dataframe(sheet_calendario, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

    if df.empty:
        df = pd.DataFrame(columns=COLS_CALENDARIO)

    df = ensure_columns(df.fillna(""), COLS_CALENDARIO)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(
        datetime.today().year
    ).astype(int)

    return df


def save_calendar(df):
    df_to_save = ensure_columns(df.copy(), COLS_CALENDARIO).fillna("")
    sheet_calendario.clear()
    set_with_dataframe(
        sheet_calendario,
        df_to_save,
        include_index=False,
        include_column_header=True,
    )


def generate_new_id(df):
    """Genera un nuevo ID incremental."""
    if df.empty or "id" not in df.columns:
        return 1
    max_id = pd.to_numeric(df["id"], errors="coerce").fillna(0).max()
    return int(max_id) + 1


def safe_parse_date(text):
    """Interpreta una fecha flexible."""
    try:
        return parse_date(text, dayfirst=True)
    except Exception:
        return None


# ============================================================
# CONFIG STREAMLIT
# ============================================================

st.set_page_config(page_title="Tanda Admin", page_icon="🎉", layout="wide")
st.title("🎉 Tanda entre Amigos – Panel Administrador")
st.caption("Gestiona participantes, calendario y pagos reales.")


# CARGA DE DATOS
participants_df = load_participants()
calendar_df = load_calendar()

tab_part, tab_cal, tab_hist = st.tabs(["Participantes", "Calendario", "Historial"])


# ============================================================
# TAB PARTICIPANTES
# ============================================================

with tab_part:
    st.header("Gestionar Participantes")

    col_form, col_list = st.columns([1, 2])

    with col_form:
        mode = st.radio("Modo", ["Agregar", "Editar"], horizontal=True, key="mode_part")

        # ---------- MODO AGREGAR ----------
        if mode == "Agregar":
            nombre = st.text_input("Nombre", key="add_nombre")
            fecha_cumple = st.text_input("Fecha de cumpleaños (ej. 15/04/1990)", key="add_fecha_cumple")
            telefono = st.text_input("Teléfono", key="add_telefono")
            email = st.text_input("Email", key="add_email")
            notas_p = st.text_area("Notas", key="add_notas")

            if st.button("Guardar Participante", key="btn_add_guardar"):
                if not nombre.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    fecha_clean = fecha_cumple.strip()
                    if fecha_clean:
                        f = safe_parse_date(fecha_clean)
                        if not f:
                            st.error("Fecha inválida. Usa un formato tipo 15/04/1990.")
                            st.stop()
                        fecha_clean = f.strftime("%Y-%m-%d")

                    new_id = generate_new_id(participants_df)
                    new_row = {
                        "id": new_id,
                        "nombre": nombre.strip(),
                        "fecha_cumple": fecha_clean,
                        "telefono": telefono.strip(),
                        "email": email.strip(),
                        "notas": notas_p.strip(),
                    }
                    participants_df = pd.concat(
                        [participants_df, pd.DataFrame([new_row])],
                        ignore_index=True
                    )
                    save_participants(participants_df)
                    participants_df = load_participants()
                    st.success("Participante agregado correctamente.")

                    # 🔄 LIMPIAR FORMULARIO DESPUÉS DE GUARDAR
                    for key in ["add_nombre", "add_fecha_cumple", "add_telefono", "add_email", "add_notas"]:
                        st.session_state[key] = ""

        # ---------- MODO EDITAR ----------
        else:
            if participants_df.empty:
                st.info("No hay participantes para editar.")
            else:
                pid = st.selectbox(
                    "Selecciona participante",
                    participants_df["id"].tolist(),
                    format_func=lambda x: participants_df.loc[
                        participants_df["id"] == x, "nombre"
                    ].values[0],
                    key="edit_pid",
                )

                row = participants_df[participants_df["id"] == pid].iloc[0]

                # Inicializar campos de edición la primera vez o cuando cambia el participante
                if (
                    "edit_current_id" not in st.session_state
                    or st.session_state["edit_current_id"] != int(pid)
                ):
                    st.session_state["edit_nombre"] = row["nombre"]
                    st.session_state["edit_fecha_cumple"] = row["fecha_cumple"]
                    st.session_state["edit_telefono"] = row["telefono"]
                    st.session_state["edit_email"] = row["email"]
                    st.session_state["edit_notas"] = row["notas"]
                    st.session_state["edit_current_id"] = int(pid)

                nombre_e = st.text_input("Nombre", key="edit_nombre")
                fecha_cumple_e = st.text_input(
                    "Fecha de cumpleaños (ej. 15/04/1990)",
                    key="edit_fecha_cumple",
                )
                telefono_e = st.text_input("Teléfono", key="edit_telefono")
                email_e = st.text_input("Email", key="edit_email")
                notas_e = st.text_area("Notas", key="edit_notas")

                if st.button("Guardar Cambios", key="btn_edit_guardar"):
                    if not nombre_e.strip():
                        st.error("El nombre es obligatorio.")
                    else:
                        fecha_clean = fecha_cumple_e.strip()
                        if fecha_clean:
                            f = safe_parse_date(fecha_clean)
                            if not f:
                                st.error("Fecha inválida.")
                                st.stop()
                            fecha_clean = f.strftime("%Y-%m-%d")

                        participants_df.loc[participants_df["id"] == pid, "nombre"] = nombre_e.strip()
                        participants_df.loc[participants_df["id"] == pid, "fecha_cumple"] = fecha_clean
                        participants_df.loc[participants_df["id"] == pid, "telefono"] = telefono_e.strip()
                        participants_df.loc[participants_df["id"] == pid, "email"] = email_e.strip()
                        participants_df.loc[participants_df["id"] == pid, "notas"] = notas_e.strip()

                        save_participants(participants_df)
                        participants_df = load_participants()
                        st.success("Participante actualizado correctamente.")

                if st.button("Eliminar participante", key="btn_edit_eliminar"):
                    participants_df = participants_df[participants_df["id"] != pid]
                    save_participants(participants_df)
                    participants_df = load_participants()
                    st.warning("Participante eliminado.")

                    # limpiar estado de edición
                    for key in [
                        "edit_nombre",
                        "edit_fecha_cumple",
                        "edit_telefono",
                        "edit_email",
                        "edit_notas",
                        "edit_current_id",
                    ]:
                        if key in st.session_state:
                            del st.session_state[key]

    with col_list:
        st.subheader("Lista de participantes")
        st.dataframe(participants_df, use_container_width=True)


# ============================================================
# TAB CALENDARIO
# ============================================================

with tab_cal:
    st.header("Calendario de Pagos")

    if participants_df.empty:
        st.info("Agrega participantes primero.")
    else:
        colA, colB = st.columns([1, 2])

        with colA:
            anio = st.number_input("Año", min_value=2000, max_value=2100, value=datetime.today().year)
            monto = st.number_input("Monto por persona (USD)", min_value=1.0, value=50.0)

            if st.button("Generar Calendario", key="btn_generar_cal"):
                valid = []
                for _, p in participants_df.iterrows():
                    if p["fecha_cumple"]:
                        d = safe_parse_date(p["fecha_cumple"])
                        if d:
                            valid.append({
                                "id": int(p["id"]),
                                "nombre": p["nombre"],
                                "mes": d.month,
                                "dia": d.day,
                            })

                if not valid:
                    st.error("Ningún participante tiene fecha de cumpleaños válida.")
                else:
                    valid = sorted(valid, key=lambda x: (x["mes"], x["dia"]))
                    total = (len(participants_df) - 1) * monto

                    # Eliminar calendario previo de ese año
                    calendar_df = calendar_df[calendar_df["anio"] != anio]

                    new_rows = []
                    for v in valid:
                        fecha_pago = datetime(anio, v["mes"], v["dia"]).strftime("%Y-%m-%d")
                        rid = generate_new_id(calendar_df)
                        new_rows.append({
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
                        })

                    calendar_df = pd.concat(
                        [calendar_df, pd.DataFrame(new_rows)],
                        ignore_index=True
                    )
                    save_calendar(calendar_df)
                    calendar_df = load_calendar()
                    st.success("Calendario generado.")

        with colB:
            year_df = calendar_df[calendar_df["anio"] == anio].copy()

            if year_df.empty:
                st.info("No hay calendario para este año.")
            else:
                year_df["fecha_pago"] = pd.to_datetime(
                    year_df["fecha_pago"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")

                edited = st.data_editor(
                    year_df[
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
                    ],
                    num_rows="fixed",
                    use_container_width=True,
                    key="editor_calendario",
                )

                if st.button("Guardar Cambios del Calendario", key="btn_guardar_cal"):
                    for _, r in edited.iterrows():
                        rid = int(r["id"])
                        mask = calendar_df["id"] == rid
                        if not mask.any():
                            continue

                        calendar_df.loc[mask, "estatus"] = r["estatus"]
                        calendar_df.loc[mask, "notas"] = r["notas"]

                        fecha_real = str(r.get("fecha_pago_real", "")).strip()

                        if fecha_real:
                            calendar_df.loc[mask, "fecha_pago_real"] = fecha_real
                        else:
                            if r["estatus"] == "Completado":
                                calendar_df.loc[mask, "fecha_pago_real"] = datetime.today().strftime(
                                    "%Y-%m-%d"
                                )

                    save_calendar(calendar_df)
                    calendar_df = load_calendar()
                    st.success("Cambios guardados.")


# ============================================================
# TAB HISTORIAL
# ============================================================

with tab_hist:
    st.header("Historial General")

    if calendar_df.empty:
        st.info("Aún no hay calendario registrado.")
    else:
        anios = sorted(calendar_df["anio"].unique())
        anio_sel = st.selectbox("Selecciona año", anios)

        df_year = calendar_df[calendar_df["anio"] == anio_sel].copy()

        if df_year.empty:
            st.info("No hay registros para ese año.")
        else:
            completados = (df_year["estatus"] == "Completado").sum()
            pendientes = (df_year["estatus"] == "Pendiente").sum()
            dinero_total = df_year["total_a_recibir"].sum()

            st.subheader("Resumen")
            st.write(f"Turnos: **{len(df_year)}**")
            st.write(f"Completados: **{completados}**")
            st.write(f"Pendientes: **{pendientes}**")
            st.write(f"Dinero total: **${dinero_total:,.2f} USD**")

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

            st.subheader("Detalle")
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
                ],
                use_container_width=True,
            )
