import streamlit as st
import pandas as pd
from datetime import datetime, date

from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(page_title="Panel administrador – Tanda", page_icon="💸", layout="wide")

st.title("💸 Panel administrador – Tanda de cumpleaños")

# ============================================================
# CONFIG: GOOGLE SHEETS (LECTURA / ESCRITURA)
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


def save_new_participant(nombre, fecha_cumple_dt, telefono, email, notas):
    df = load_participants()
    if df.empty:
        new_id = 1
    else:
        new_id = int(df["id"].max()) + 1

    # Guardamos SIEMPRE en formato ISO: YYYY-MM-DD
    fecha_cumple_str = fecha_cumple_dt.strftime("%Y-%m-%d")

    new_row = [
        new_id,
        nombre,
        fecha_cumple_str,
        telefono,
        email,
        notas,
    ]
    sheet_participantes.append_row(new_row)


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


def save_calendar_for_year(df_new_year, year):
    """
    Reemplaza SOLO el calendario del año indicado,
    manteniendo los demás años intactos.
    """
    df_all = load_calendar()
    if df_all.empty:
        df_out = df_new_year.copy()
    else:
        df_other = df_all[df_all["anio"] != year]
        df_out = pd.concat([df_other, df_new_year], ignore_index=True)

    # Reordenar columnas y ordenar por año + fecha_pago
    df_out = ensure_columns(df_out, COLS_CALENDARIO)
    df_out["fecha_pago_dt"] = pd.to_datetime(df_out["fecha_pago"], errors="coerce")
    df_out = df_out.sort_values(["anio", "fecha_pago_dt", "id"])

    # Quitamos columna auxiliar antes de escribir
    df_out = df_out.drop(columns=["fecha_pago_dt"])

    sheet_calendario.clear()
    set_with_dataframe(sheet_calendario, df_out[COLS_CALENDARIO])


# ============================================================
# TABS PRINCIPALES
# ============================================================

tab1, tab2, tab3 = st.tabs(["👥 Participantes", "📅 Calendario", "💳 Pagos / Estatus"])


# ============================================================
# TAB 1: PARTICIPANTES
# ============================================================

with tab1:
    st.subheader("Registrar nuevo participante")

    col_a, col_b = st.columns(2)
    with col_a:
        nombre = st.text_input("Nombre completo")
        fecha_cumple = st.date_input("Fecha de cumpleaños", value=date(1990, 1, 1))
    with col_b:
        telefono = st.text_input("Teléfono")
        email = st.text_input("Email")
    notas = st.text_area("Notas", height=80)

    if st.button("Guardar participante"):
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            save_new_participant(nombre, fecha_cumple, telefono, email, notas)
            st.success("Participante registrado correctamente.")

    st.markdown("---")
    st.subheader("Lista de participantes")

    participants_df = load_participants()
    if participants_df.empty:
        st.info("Aún no hay participantes registrados.")
    else:
        # Mostramos siempre fecha_cumple tal cual ISO (YYYY-MM-DD)
        st.dataframe(
            participants_df[["id", "nombre", "fecha_cumple", "telefono", "email"]],
            use_container_width=True,
        )


# ============================================================
# TAB 2: CALENDARIO
# ============================================================

with tab2:
    st.subheader("Generar / actualizar calendario de pagos")

    participants_df = load_participants()
    if participants_df.empty:
        st.warning("Primero registra participantes en la pestaña 'Participantes'.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            current_year = datetime.today().year
            anio_cal = st.number_input(
                "Año de la tanda",
                min_value=2020,
                max_value=2100,
                value=current_year,
                step=1,
            )
        with col2:
            aporte = st.number_input(
                "Aporte por persona (cuota)",
                min_value=0.0,
                step=10.0,
                value=50.0,
            )

        if st.button("Generar / Reemplazar calendario para este año"):
            # Preparamos df base
            cal_df_all = load_calendar()
            if cal_df_all.empty:
                max_id = 0
            else:
                max_id = int(cal_df_all["id"].max())

            rows = []
            num_participantes = len(participants_df)
            total_por_turno = aporte * num_participantes

            for _, row in participants_df.iterrows():
                # fecha_cumple guardada como 'YYYY-MM-DD'
                try:
                    cumple_dt = datetime.strptime(str(row["fecha_cumple"]), "%Y-%m-%d")
                except Exception:
                    # Si falla, intentamos parsear libre
                    cumple_dt = pd.to_datetime(str(row["fecha_cumple"]), errors="coerce")
                    if pd.isna(cumple_dt):
                        continue  # saltamos si no la podemos interpretar

                # Ajustamos año al año de la tanda
                try:
                    fecha_pago_dt = cumple_dt.replace(year=int(anio_cal))
                except ValueError:
                    # Por si el cumple es 29-feb y el año no es bisiesto
                    if cumple_dt.month == 2 and cumple_dt.day == 29:
                        fecha_pago_dt = datetime(int(anio_cal), 2, 28)
                    else:
                        continue

                max_id += 1
                rows.append(
                    {
                        "id": max_id,
                        "anio": int(anio_cal),
                        "id_participante": int(row["id"]),
                        "nombre_participante": row["nombre"],
                        # Guardamos SIEMPRE fecha de pago en formato ISO YYYY-MM-DD
                        "fecha_pago": fecha_pago_dt.strftime("%Y-%m-%d"),
                        "monto_por_persona": float(aporte),
                        "total_a_recibir": float(total_por_turno),
                        "estatus": "Pendiente",
                        "fecha_pago_real": "",
                        "notas": "",
                    }
                )

            if not rows:
                st.error("No se pudo generar el calendario. Revisa las fechas de cumpleaños.")
            else:
                df_new_year = pd.DataFrame(rows, columns=COLS_CALENDARIO)
                save_calendar_for_year(df_new_year, int(anio_cal))
                st.success(f"Calendario para el año {anio_cal} generado/actualizado correctamente.")

        st.markdown("---")
        st.subheader("Vista del calendario (solo lectura)")

        # Mostrar calendario del año seleccionado
        cal_df = load_calendar()
        if cal_df.empty:
            st.info("Aún no hay calendario generado.")
        else:
            years_available = sorted(cal_df["anio"].unique())
            sel_year = st.selectbox(
                "Ver calendario del año",
                options=years_available,
                index=years_available.index(max(years_available)),
            )
            cal_year = cal_df[cal_df["anio"] == sel_year].copy()
            if cal_year.empty:
                st.info("No hay registros para ese año.")
            else:
                cal_year["fecha_pago_dt"] = pd.to_datetime(
                    cal_year["fecha_pago"], errors="coerce"
                )
                cal_year = cal_year.sort_values("fecha_pago_dt")

                # Mostramos como tabla simple, fechas en YYYY-MM-DD
                cal_year["fecha_pago"] = cal_year["fecha_pago_dt"].dt.strftime(
                    "%Y-%m-%d"
                )

                st.dataframe(
                    cal_year[
                        [
                            "nombre_participante",
                            "fecha_pago",
                            "monto_por_persona",
                            "total_a_recibir",
                            "estatus",
                        ]
                    ],
                    use_container_width=True,
                )


# ============================================================
# TAB 3: PAGOS / ESTATUS
# ============================================================

with tab3:
    st.subheader("Actualizar estatus de pagos")

    cal_df = load_calendar()
    if cal_df.empty:
        st.info("Aún no hay calendario para actualizar.")
    else:
        years_available = sorted(cal_df["anio"].unique())
        sel_year = st.selectbox(
            "Selecciona el año a editar",
            options=years_available,
            index=years_available.index(max(years_available)),
            key="year_pagos",
        )

        df_edit = cal_df[cal_df["anio"] == sel_year].copy()
        if df_edit.empty:
            st.info("No hay registros para ese año.")
        else:
            df_edit["fecha_pago_dt"] = pd.to_datetime(
                df_edit["fecha_pago"], errors="coerce"
            )
            df_edit = df_edit.sort_values("fecha_pago_dt")

            # Para edición: solo dejamos cambiar estatus y fecha_pago_real
            df_edit_display = df_edit.copy()
            df_edit_display["fecha_pago"] = df_edit["fecha_pago_dt"].dt.strftime(
                "%Y-%m-%d"
            )

            df_edit_display = df_edit_display[
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

            st.write("Modifica el estatus y la fecha de pago real (opcional):")

            edited = st.data_editor(
                df_edit_display,
                num_rows="fixed",
                use_container_width=True,
                key="editor_pagos",
                column_config={
                    "id": st.column_config.NumberColumn(disabled=True),
                    "nombre_participante": st.column_config.TextColumn(disabled=True),
                    "fecha_pago": st.column_config.TextColumn(disabled=True),
                    "monto_por_persona": st.column_config.NumberColumn(disabled=True),
                    "total_a_recibir": st.column_config.NumberColumn(disabled=True),
                },
            )

            if st.button("Guardar cambios de pagos"):
                # Volcamos cambios sobre df_edit original
                for idx, row in edited.iterrows():
                    id_val = row["id"]
                    mask = df_edit["id"] == id_val
                    df_edit.loc[mask, "estatus"] = row["estatus"]
                    df_edit.loc[mask, "fecha_pago_real"] = row["fecha_pago_real"]
                    df_edit.loc[mask, "notas"] = row["notas"]

                # Reemplazar solo ese año en el calendario completo
                df_all = load_calendar()
                df_other = df_all[df_all["anio"] != sel_year]
                df_out = pd.concat([df_other, df_edit], ignore_index=True)
                df_out = ensure_columns(df_out, COLS_CALENDARIO)

                sheet_calendario.clear()
                set_with_dataframe(sheet_calendario, df_out[COLS_CALENDARIO])

                st.success("Cambios de estatus guardados correctamente.")
