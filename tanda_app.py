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
# CONFIG GOOGLE SHEETS
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
    "pagos_detalle",
]

# ============================================================
# BASE DE DATOS
# ============================================================

def ensure_columns(df, columns):
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df[columns]

def load_participants():
    df = get_as_dataframe(sheet_participantes, header=0)
    df = df.dropna(how="all")
    if df.empty:
        return pd.DataFrame(columns=COLS_PARTICIPANTES)
    df = ensure_columns(df.fillna(""), COLS_PARTICIPANTES)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    return df

def save_new_participant(nombre, fecha_cumple_dt, telefono, email, notas):
    df = load_participants()
    new_id = 1 if df.empty else int(df["id"].max()) + 1

    fecha_str = fecha_cumple_dt.strftime("%Y-%m-%d")

    sheet_participantes.append_row(
        [new_id, nombre, fecha_str, telefono, email, notas]
    )

def load_calendar():
    df = get_as_dataframe(sheet_calendario, header=0)
    df = df.dropna(how="all")
    if df.empty:
        return pd.DataFrame(columns=COLS_CALENDARIO)
    df = ensure_columns(df.fillna(""), COLS_CALENDARIO)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(datetime.today().year).astype(int)
    return df

def save_calendar_for_year(df_new_year, year):
    df_all = load_calendar()
    if df_all.empty:
        df_out = df_new_year.copy()
    else:
        df_other = df_all[df_all["anio"] != year]
    df_out = pd.concat([df_other, df_new_year], ignore_index=True)

    # ordenar
    df_out["fecha_pago_dt"] = pd.to_datetime(df_out["fecha_pago"], errors="coerce")
    df_out = df_out.sort_values(["anio", "fecha_pago_dt", "id"])
    df_out = df_out.drop(columns=["fecha_pago_dt"])

    sheet_calendario.clear()
    set_with_dataframe(sheet_calendario, df_out[COLS_CALENDARIO])

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(["👥 Participantes", "📅 Calendario", "💳 Pagos / Estatus"])

# ============================================================
# TAB 1 – PARTICIPANTES
# ============================================================

with tab1:
    st.subheader("Registrar nuevo participante")

    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre completo")
        fecha_cumple = st.date_input("Fecha de cumpleaños", value=date(1990,1,1))
    with col2:
        telefono = st.text_input("Teléfono")
        email = st.text_input("Email")

    notas = st.text_area("Notas (nickname)", height=70)

    if st.button("Guardar participante"):
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            save_new_participant(nombre, fecha_cumple, telefono, email, notas)
            st.success("Participante registrado correctamente.")

    st.markdown("---")
    st.subheader("Lista de participantes")

    dfp = load_participants()
    if dfp.empty:
        st.info("Aún no hay participantes.")
    else:
        # MOSTRAR LISTA • Nombre — Nickname
        items = []
        for _, row in dfp.iterrows():
            nickname = str(row["notas"]).strip()
            if nickname == "":
                nickname = "-"
            items.append(f"<li>{row['nombre']} — {nickname}</li>")

        html_list = "<ul style='color:#D1D5DB;font-size:17px;'>" + "".join(items) + "</ul>"
        st.markdown(html_list, unsafe_allow_html=True)

# ============================================================
# TAB 2 – CALENDARIO
# ============================================================

with tab2:
    st.subheader("Generar calendario de pagos")

    dfp = load_participants()
    if dfp.empty:
        st.warning("Primero registra participantes.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            yr = st.number_input("Año", min_value=2020, max_value=2100, value=datetime.today().year)
        with col2:
            aporte = st.number_input("Aporte por persona", min_value=0.0, step=5.0, value=50.0)

        if st.button("Generar / Reemplazar calendario"):
            df_cal = load_calendar()
            max_id = 0 if df_cal.empty else int(df_cal["id"].max())

            rows = []
            num_total = len(dfp)
            num_aportan = max(num_total - 1, 0)
            total_recibir = aporte * num_aportan

            for _, row in dfp.iterrows():
                try:
                    fcx = datetime.strptime(row["fecha_cumple"], "%Y-%m-%d")
                except:
                    fcx = pd.to_datetime(row["fecha_cumple"], errors="coerce")

                if pd.isna(fcx):
                    continue

                try:
                    fpay = fcx.replace(year=int(yr))
                except:
                    if fcx.month == 2 and fcx.day == 29:
                        fpay = datetime(int(yr), 2, 28)
                    else:
                        continue

                max_id += 1
                rows.append({
                    "id": max_id,
                    "anio": int(yr),
                    "id_participante": int(row["id"]),
                    "nombre_participante": row["nombre"],
                    "fecha_pago": fpay.strftime("%Y-%m-%d"),
                    "monto_por_persona": float(aporte),
                    "total_a_recibir": float(total_recibir),
                    "estatus": "Pendiente",
                    "fecha_pago_real": "",
                    "notas": "",
                    "pagos_detalle": "",
                })

            df_new = pd.DataFrame(rows, columns=COLS_CALENDARIO)
            save_calendar_for_year(df_new, int(yr))
            st.success("Calendario generado correctamente.")

        st.markdown("---")
        st.subheader("Vista del calendario")

        dfc = load_calendar()
        if dfc.empty:
            st.info("Aún no hay calendario.")
        else:
            years = sorted(dfc["anio"].unique())
            sy = st.selectbox("Año", years, index=years.index(max(years)))

            dfy = dfc[dfc["anio"] == sy].copy()
            dfy["fecha_pago_dt"] = pd.to_datetime(dfy["fecha_pago"], errors="coerce")
            dfy = dfy.sort_values("fecha_pago_dt")
            dfy["fecha_pago"] = dfy["fecha_pago_dt"].dt.strftime("%Y-%m-%d")

            st.dataframe(
                dfy[["nombre_participante","fecha_pago","monto_por_persona","total_a_recibir","estatus"]],
                use_container_width=True
            )

# ============================================================
# TAB 3 – PAGOS / ESTATUS
# ============================================================

with tab3:
    st.subheader("Actualizar pagos")

    dfc = load_calendar()
    if dfc.empty:
        st.info("Aún no hay calendario.")
    else:
        years = sorted(dfc["anio"].unique())
        sy = st.selectbox("Año", years, index=years.index(max(years)))

        dfy = dfc[dfc["anio"] == sy].copy()
        dfy["fecha_pago_dt"] = pd.to_datetime(dfy["fecha_pago"], errors="coerce")
        dfy = dfy.sort_values("fecha_pago_dt")

        df_edit = dfy.copy()
        df_edit["fecha_pago"] = df_edit["fecha_pago_dt"].dt.strftime("%Y-%m-%d")

        st.write("Edita estatus y fecha de pago real:")
        edited = st.data_editor(
            df_edit[
                ["id","nombre_participante","fecha_pago","monto_por_persona",
                 "total_a_recibir","estatus","fecha_pago_real","notas"]
            ],
            num_rows="fixed"
        )

        if st.button("Guardar cambios generales"):
            for idx,row in edited.iterrows():
                mask = dfy["id"] == row["id"]
                dfy.loc[mask,"estatus"] = row["estatus"]
                dfy.loc[mask,"fecha_pago_real"] = row["fecha_pago_real"]
                dfy.loc[mask,"notas"] = row["notas"]

            df_all = load_calendar()
            df_out = pd.concat([df_all[df_all["anio"]!=sy], dfy], ignore_index=True)
            df_out = ensure_columns(df_out, COLS_CALENDARIO)

            sheet_calendario.clear()
            set_with_dataframe(sheet_calendario, df_out[COLS_CALENDARIO])

            st.success("Cambios guardados correctamente.")

        st.markdown("---")
        st.subheader("Control de pagos por integrante")

        dfp = load_participants()
        if dfp.empty:
            st.info("No hay participantes.")
        else:
            opciones = []
            ids_turno = []

            for _, r in dfy.iterrows():
                fecha_lbl = r["fecha_pago_dt"].strftime("%Y-%m-%d")
                opciones.append(f"{r['nombre_participante']} — {fecha_lbl}")
                ids_turno.append(int(r["id"]))

            if opciones:
                sel = st.selectbox("Selecciona la tanda", opciones)
                idx_sel = opciones.index(sel)
                id_turno = ids_turno[idx_sel]

                row_t = dfy[dfy["id"]==id_turno].iloc[0]

                pagos_raw = str(row_t["pagos_detalle"]).strip()
                pagados = set([int(x) for x in pagos_raw.split(",") if x.strip().isdigit()])

                fecha_lbl = row_t["fecha_pago_dt"].strftime("%Y-%m-%d")

                st.write(f"Pagos para **{row_t['nombre_participante']}** — {fecha_lbl}")

                checks = {}
                for _, p in dfp.iterrows():
                    pid = int(p["id"])
                    checks[pid] = st.checkbox(
                        p["nombre"],
                        value=(pid in pagados),
                        key=f"chk_{id_turno}_{pid}"
                    )

                if st.button("Guardar control de pagos"):
                    new_pagos = [pid for pid,v in checks.items() if v]
                    pagos_str = ",".join(str(x) for x in new_pagos)

                    dfy.loc[dfy["id"] == id_turno, "pagos_detalle"] = pagos_str

                    if len(new_pagos) >= len(dfp):
                        dfy.loc[dfy["id"]==id_turno, "estatus"] = "Completado"

                    df_all = load_calendar()
                    df_out = pd.concat([df_all[df_all["anio"]!=sy], dfy], ignore_index=True)
                    df_out = ensure_columns(df_out, COLS_CALENDARIO)

                    sheet_calendario.clear()
                    set_with_dataframe(sheet_calendario, df_out[COLS_CALENDARIO])

                    st.success("Control de pagos actualizado.")
