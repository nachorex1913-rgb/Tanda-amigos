import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dateutil.parser import parse as parse_date

# -------------------------------
# Configuración básica
# -------------------------------
st.set_page_config(
    page_title="Tanda entre amigos",
    page_icon="🎉",
    layout="wide",
)

st.title("🎉 App de Tanda entre Amigos")
st.write(
    "Registra participantes, genera el calendario según cumpleaños y controla el estatus de la tanda."
)

# -------------------------------
# Archivos de datos
# -------------------------------
PARTICIPANTS_FILE = "participantes_tanda.csv"
CALENDAR_FILE = "calendario_tanda.csv"


# -------------------------------
# Funciones auxiliares
# -------------------------------
@st.cache_data
def load_participants():
    if os.path.exists(PARTICIPANTS_FILE):
        df = pd.read_csv(PARTICIPANTS_FILE)
        # Asegurar columnas
        expected_cols = ["id", "nombre", "fecha_cumple", "telefono", "email", "notas"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols]
    else:
        return pd.DataFrame(
            columns=["id", "nombre", "fecha_cumple", "telefono", "email", "notas"]
        )


def save_participants(df):
    df.to_csv(PARTICIPANTS_FILE, index=False)
    load_participants.clear()  # Limpiar cache


@st.cache_data
def load_calendar():
    if os.path.exists(CALENDAR_FILE):
        df = pd.read_csv(CALENDAR_FILE)
        # Asegurar columnas
        expected_cols = [
            "id",
            "anio",
            "id_participante",
            "nombre_participante",
            "fecha_pago",
            "monto_por_persona",
            "total_a_recibir",
            "estatus",
            "notas",
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols]
    else:
        return pd.DataFrame(
            columns=[
                "id",
                "anio",
                "id_participante",
                "nombre_participante",
                "fecha_pago",
                "monto_por_persona",
                "total_a_recibir",
                "estatus",
                "notas",
            ]
        )


def save_calendar(df):
    df.to_csv(CALENDAR_FILE, index=False)
    load_calendar.clear()  # Limpiar cache


def generate_new_id(df):
    if df.empty:
        return 1
    else:
        return int(df["id"].max()) + 1


def safe_parse_date(date_str):
    """
    Intenta interpretar fechas escritas como:
    15/04/1990, 1990-04-15, 15-04-90, etc.
    """
    try:
        return parse_date(date_str, dayfirst=True)
    except Exception:
        return None


# -------------------------------
# Cargar datos iniciales
# -------------------------------
participants_df = load_participants()
calendar_df = load_calendar()

# -------------------------------
# Layout con pestañas
# -------------------------------
tab1, tab2, tab3 = st.tabs(["👥 Participantes", "📅 Calendario de la tanda", "📊 Historial y resumen"])

# ===============================
# TAB 1: PARTICIPANTES
# ===============================
with tab1:
    st.subheader("👥 Gestión de participantes")

    st.write("Agrega o edita los amigos que participan en la tanda.")

    # Columna izquierda: formulario
    col_form, col_table = st.columns([1, 2])

    with col_form:
        st.markdown("### ➕ Agregar / editar participante")

        modo = st.radio("Modo", ["Agregar nuevo", "Editar existente"], horizontal=True)

        if modo == "Editar existente" and not participants_df.empty:
            participante_sel = st.selectbox(
                "Selecciona participante",
                options=participants_df["id"].tolist(),
                format_func=lambda x: participants_df.loc[
                    participants_df["id"] == x, "nombre"
                ].values[0],
            )
            row = participants_df[participants_df["id"] == participante_sel].iloc[0]
            default_nombre = row["nombre"]
            default_fecha_cumple = row["fecha_cumple"]
            default_telefono = row["telefono"]
            default_email = row["email"]
            default_notas = row["notas"]
        else:
            participante_sel = None
            default_nombre = ""
            default_fecha_cumple = ""
            default_telefono = ""
            default_email = ""
            default_notas = ""

        nombre = st.text_input("Nombre completo", value=default_nombre)
        fecha_cumple_str = st.text_input(
            "Fecha de cumpleaños (ej. 15/04/1990)",
            value=default_fecha_cumple,
            help="Formato flexible: 15/04/1990, 1990-04-15, etc.",
        )
        telefono = st.text_input("Teléfono (opcional)", value=default_telefono)
        email = st.text_input("Email (opcional)", value=default_email)
        notas = st.text_area("Notas (opcional)", value=default_notas)

        if st.button("Guardar participante"):
            if not nombre.strip():
                st.warning("El nombre es obligatorio.")
            else:
                # Validar fecha
                if fecha_cumple_str.strip():
                    fecha_parsed = safe_parse_date(fecha_cumple_str.strip())
                    if not fecha_parsed:
                        st.error("La fecha de cumpleaños no se pudo interpretar. Revisa el formato.")
                    else:
                        fecha_cumple_str_clean = fecha_parsed.strftime("%Y-%m-%d")
                else:
                    fecha_cumple_str_clean = ""

                if modo == "Agregar nuevo":
                    new_id = generate_new_id(participants_df)
                    new_row = {
                        "id": new_id,
                        "nombre": nombre.strip(),
                        "fecha_cumple": fecha_cumple_str_clean,
                        "telefono": telefono.strip(),
                        "email": email.strip(),
                        "notas": notas.strip(),
                    }
                    participants_df = pd.concat(
                        [participants_df, pd.DataFrame([new_row])],
                        ignore_index=True,
                    )
                    save_participants(participants_df)
                    st.success("Participante agregado correctamente.")
                else:
                    # Editar
                    participants_df.loc[
                        participants_df["id"] == participante_sel, "nombre"
                    ] = nombre.strip()
                    participants_df.loc[
                        participants_df["id"] == participante_sel, "fecha_cumple"
                    ] = fecha_cumple_str_clean
                    participants_df.loc[
                        participants_df["id"] == participante_sel, "telefono"
                    ] = telefono.strip()
                    participants_df.loc[
                        participants_df["id"] == participante_sel, "email"
                    ] = email.strip()
                    participants_df.loc[
                        participants_df["id"] == participante_sel, "notas"
                    ] = notas.strip()
                    save_participants(participants_df)
                    st.success("Participante actualizado correctamente.")

        if modo == "Editar existente" and participante_sel is not None:
            if st.button("🗑️ Eliminar participante"):
                # Eliminar del DF de participantes
                participants_df = participants_df[participants_df["id"] != participante_sel]
                save_participants(participants_df)
                st.warning("Participante eliminado. Recuerda revisar el calendario de la tanda.")
    
    # Columna derecha: tabla
    with col_table:
        st.markdown("### 📋 Lista de participantes")
        if participants_df.empty:
            st.info("Aún no hay participantes registrados.")
        else:
            st.dataframe(
                participants_df[["id", "nombre", "fecha_cumple", "telefono", "email", "notas"]],
                use_container_width=True,
            )

# ===============================
# TAB 2: CALENDARIO
# ===============================
with tab2:
    st.subheader("📅 Calendario de la tanda")

    if participants_df.empty:
        st.info("Primero agrega participantes en la pestaña de **Participantes**.")
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
            monto_por_persona = st.number_input(
                "Monto que cada persona aporta por cumpleaños (USD)",
                min_value=1.0,
                value=50.0,
                step=1.0,
            )

            st.write(
                "Total a recibir cada cumpleañero = (Número de amigos - 1) × monto por persona."
            )

            if st.button("Generar / Regenerar calendario para este año"):
                # Filtrar participantes con fecha de cumpleaños válida
                valid_participants = []
                for _, row in participants_df.iterrows():
                    if row["fecha_cumple"]:
                        fecha_parsed = safe_parse_date(row["fecha_cumple"])
                        if fecha_parsed:
                            valid_participants.append(
                                {
                                    "id": row["id"],
                                    "nombre": row["nombre"],
                                    "mes": fecha_parsed.month,
                                    "dia": fecha_parsed.day,
                                }
                            )

                if not valid_participants:
                    st.error(
                        "Ningún participante tiene fecha de cumpleaños válida. "
                        "Revisa las fechas en la pestaña de participantes."
                    )
                else:
                    # Ordenar por mes y día
                    valid_participants = sorted(
                        valid_participants, key=lambda x: (x["mes"], x["dia"])
                    )

                    n = len(participants_df)
                    total_por_cumple = (n - 1) * monto_por_persona

                    # Eliminar calendario existente de ese año
                    calendar_df = calendar_df[calendar_df["anio"] != anio]

                    # Crear nuevas filas
                    new_rows = []
                    for vp in valid_participants:
                        fecha_pago = datetime(anio, vp["mes"], vp["dia"]).strftime("%Y-%m-%d")
                        new_id = generate_new_id(calendar_df if not calendar_df.empty else pd.DataFrame(columns=["id"]))
                        new_rows.append(
                            {
                                "id": new_id,
                                "anio": anio,
                                "id_participante": vp["id"],
                                "nombre_participante": vp["nombre"],
                                "fecha_pago": fecha_pago,
                                "monto_por_persona": monto_por_persona,
                                "total_a_recibir": total_por_cumple,
                                "estatus": "Pendiente",
                                "notas": "",
                            }
                        )

                    calendar_df = pd.concat(
                        [calendar_df, pd.DataFrame(new_rows)], ignore_index=True
                    )
                    save_calendar(calendar_df)
                    st.success(f"Calendario de la tanda para {anio} generado/actualizado.")

        with col_right:
            st.markdown("### 📆 Calendario del año seleccionado")

            cal_year_df = calendar_df[calendar_df["anio"] == anio].copy()
            if cal_year_df.empty:
                st.info("Aún no hay calendario generado para este año.")
            else:
                # Convertir estatus en editable con data_editor
                st.write("Puedes actualizar el estatus y las notas directamente en la tabla.")
                cal_year_df_display = cal_year_df.copy()
                cal_year_df_display["fecha_pago"] = pd.to_datetime(
                    cal_year_df_display["fecha_pago"]
                ).dt.strftime("%Y-%m-%d")

                edited = st.data_editor(
                    cal_year_df_display[
                        [
                            "id",
                            "nombre_participante",
                            "fecha_pago",
                            "monto_por_persona",
                            "total_a_recibir",
                            "estatus",
                            "notas",
                        ]
                    ],
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "estatus": st.column_config.SelectboxColumn(
                            "Estatus",
                            options=["Pendiente", "Completado"],
                        ),
                        "notas": st.column_config.TextColumn("Notas"),
                    },
                    key=f"editor_{anio}",
                )

                if st.button("💾 Guardar cambios en el calendario"):
                    # Actualizar el DF original con lo editado
                    for _, row in edited.iterrows():
                        calendar_df.loc[
                            calendar_df["id"] == row["id"], "estatus"
                        ] = row["estatus"]
                        calendar_df.loc[
                            calendar_df["id"] == row["id"], "notas"
                        ] = row["notas"]

                    save_calendar(calendar_df)
                    st.success("Cambios guardados correctamente.")

# ===============================
# TAB 3: HISTORIAL Y RESUMEN
# ===============================
with tab3:
    st.subheader("📊 Historial y resumen de la tanda")

    if calendar_df.empty:
        st.info("Aún no hay registros de calendario. Genera uno en la pestaña de Calendario.")
    else:
        anios_disponibles = sorted(calendar_df["anio"].unique())
        anio_hist = st.selectbox("Selecciona año", options=anios_disponibles)

        hist_df = calendar_df[calendar_df["anio"] == anio_hist].copy()
        if hist_df.empty:
            st.info("No hay registros para este año.")
        else:
            col_a, col_b = st.columns(2)

            with col_a:
                total_eventos = len(hist_df)
                completados = (hist_df["estatus"] == "Completado").sum()
                pendientes = (hist_df["estatus"] == "Pendiente").sum()

                st.markdown("#### Resumen general")
                st.write(f"- Total de turnos en la tanda: **{total_eventos}**")
                st.write(f"- Cumpleaños pagados (Completados): **{completados}**")
                st.write(f"- Pendientes: **{pendientes}**")

                total_dinero_movido = hist_df["total_a_recibir"].sum()
                st.write(f"- Dinero total que se movería este año: **${total_dinero_movido:,.2f} USD**")

            with col_b:
                st.markdown("#### Estado por participante")
                resumen_part = (
                    hist_df.groupby("nombre_participante")
                    .agg(
                        turnos=("id", "count"),
                        completados=("estatus", lambda x: (x == "Completado").sum()),
                        pendientes=("estatus", lambda x: (x == "Pendiente").sum()),
                        total_recibir=("total_a_recibir", "sum"),
                    )
                    .reset_index()
                )
                st.dataframe(resumen_part, use_container_width=True)

            st.markdown("### 📝 Detalle completo de este año")
            hist_df_sorted = hist_df.sort_values("fecha_pago")
            hist_df_sorted["fecha_pago"] = pd.to_datetime(
                hist_df_sorted["fecha_pago"]
            ).dt.strftime("%Y-%m-%d")
            st.dataframe(
                hist_df_sorted[
                    [
                        "nombre_participante",
                        "fecha_pago",
                        "monto_por_persona",
                        "total_a_recibir",
                        "estatus",
                        "notas",
                    ]
                ],
                use_container_width=True,
            )

            st.info(
                "El historial se construye a partir del calendario de la tanda y el estatus "
                "de cada turno. Puedes usar las notas para registrar quién pagó, problemas, etc."
            )
