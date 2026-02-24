# -*- coding: utf-8 -*-
"""
Created on Tue Dec 30 12:18:15 2025

@author: Malavert
"""
import os
import re
import sqlite3
from datetime import datetime, date, time
from pathlib import Path
from typing import Optional, Dict, Any

import streamlit as st
import pandas as pd

# ==============================
# Configuración general
# ==============================
st.set_page_config(
    page_title="Inventario de Instrumentos",
    page_icon="🧪",
    layout="wide",
)

st.markdown("""
<style>

/* TEXTO DE LOS TABS */
button[data-baseweb="tab"] p {
    font-size: 24px !important;
    font-weight: 600 !important;
}

/* TAB ACTIVO */
button[data-baseweb="tab"][aria-selected="true"] p {
    font-size: 24px !important;
    color: #ff4b4b !important;
}

/* ESPACIADO */
button[data-baseweb="tab"] {
    padding: 16px 24px !important;
}

</style>
""", unsafe_allow_html=True)

# Carpeta base
BASE_DIR = Path(__file__).resolve().parent

# Base de datos y fotos
DB_PATH = BASE_DIR / "instrumentos.db"
IMAGES_DIR = BASE_DIR / "instrument_photos"
IMAGES_DIR.mkdir(exist_ok=True)

# ==============================
# Encabezado con logo (arriba derecha)
# ==============================
LOGO_PATH = BASE_DIR / "Logo_CI.png"

col_title, col_logo = st.columns([6, 1])

with col_title:
    st.title("Inventario de Instrumentos - Cultivos Industriales - FAUBA")
    st.markdown(
        """
        <p style='font-size:22px;'>
        Sistema para registrar y consultar instrumentos, con información básica,
        responsable y reservas de uso.
        </p>
        """,
        unsafe_allow_html=True
    )

with col_logo:
    if LOGO_PATH.exists():
        st.image(LOGO_PATH, width=200)

#st.caption(f"Base de datos: {DB_PATH}")
#st.caption(f"Carpeta de fotos: {IMAGES_DIR}")

# ==============================
# Compatibilidad rerun
# ==============================
def do_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ==============================
# Funciones de base de datos
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS instrumentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo_unidad TEXT,
            responsable TEXT,
            investigador_grupo TEXT NOT NULL,
            instrumento TEXT NOT NULL,
            numero_inventario TEXT,
            reserva_uso TEXT,
            estado TEXT,
            ubicacion TEXT,
            descripcion TEXT,
            foto_path TEXT,
            fecha_registro TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrumento_id INTEGER NOT NULL,
            usuario TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            comentario TEXT,
            estado TEXT,
            fecha_registro TEXT,
            FOREIGN KEY(instrumento_id) REFERENCES instrumentos(id)
        )
        """
    )

    conn.commit()
    conn.close()


def guardar_imagen(uploaded_file) -> Optional[str]:
    if uploaded_file is None:
        return None
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg", ".tif", ".tiff"]:
        suffix = ".png"
    file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{suffix}"
    file_path = IMAGES_DIR / file_name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)


# ---------- Instrumentos ----------
def insertar_instrumento(
    grupo_unidad: str,
    responsable: str,
    investigador_grupo: str,
    instrumento: str,
    numero_inventario: str,
    reserva_uso: str,
    estado: str,
    ubicacion: str,
    descripcion: str,
    foto_path: Optional[str],
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO instrumentos
        (grupo_unidad, responsable, investigador_grupo, instrumento,
         numero_inventario, reserva_uso, estado, ubicacion,
         descripcion, foto_path, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            grupo_unidad,
            responsable,
            investigador_grupo,
            instrumento,
            numero_inventario,
            reserva_uso,
            estado,
            ubicacion,
            descripcion,
            foto_path,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def cargar_instrumentos(
    filtro_grupo: str = "",
    filtro_investigador: str = "",
    filtro_instrumento: str = "",
) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM instrumentos WHERE 1=1"
    params: list[str] = []

    if filtro_grupo:
        query += " AND grupo_unidad LIKE ?"
        params.append(f"%{filtro_grupo}%")
    if filtro_investigador:
        query += " AND investigador_grupo LIKE ?"
        params.append(f"%{filtro_investigador}%")
    if filtro_instrumento:
        query += " AND instrumento LIKE ?"
        params.append(f"%{filtro_instrumento}%")

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def obtener_instrumento_por_id(instrumento_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM instrumentos WHERE id = ?", (instrumento_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_instrumento(
    instrumento_id: int,
    grupo_unidad: str,
    responsable: str,
    investigador_grupo: str,
    instrumento: str,
    numero_inventario: str,
    reserva_uso: str,
    estado: str,
    ubicacion: str,
    descripcion: str,
    foto_path: Optional[str],
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE instrumentos
        SET grupo_unidad = ?,
            responsable = ?,
            investigador_grupo = ?,
            instrumento = ?,
            numero_inventario = ?,
            reserva_uso = ?,
            estado = ?,
            ubicacion = ?,
            descripcion = ?,
            foto_path = ?
        WHERE id = ?
        """,
        (
            grupo_unidad,
            responsable,
            investigador_grupo,
            instrumento,
            numero_inventario,
            reserva_uso,
            estado,
            ubicacion,
            descripcion,
            foto_path,
            instrumento_id,
        ),
    )
    conn.commit()
    conn.close()


def contar_reservas_de_instrumento(instrumento_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM reservas WHERE instrumento_id = ?", (instrumento_id,))
    n = cur.fetchone()[0]
    conn.close()
    return int(n)


def borrar_reservas_de_instrumento(instrumento_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM reservas WHERE instrumento_id = ?", (instrumento_id,))
    conn.commit()
    conn.close()


def borrar_instrumento(instrumento_id: int):
    inst = obtener_instrumento_por_id(instrumento_id)
    foto_path = inst.get("foto_path") if inst else None

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM instrumentos WHERE id = ?", (instrumento_id,))
    conn.commit()
    conn.close()

    if foto_path and os.path.exists(foto_path):
        try:
            os.remove(foto_path)
        except OSError:
            pass


# ---------- Reservas ----------
def insertar_reserva(
    instrumento_id: int,
    usuario: str,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    comentario: str,
    estado: str = "Confirmada",
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reservas
        (instrumento_id, usuario, fecha_inicio, fecha_fin,
         comentario, estado, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            instrumento_id,
            usuario,
            fecha_inicio.strftime("%Y-%m-%d %H:%M:%S"),
            fecha_fin.strftime("%Y-%m-%d %H:%M:%S"),
            comentario,
            estado,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def cargar_reservas(instrumento_id: Optional[int] = None) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    if instrumento_id is None:
        query = """
        SELECT r.id, r.instrumento_id, i.instrumento,
               r.usuario, r.fecha_inicio, r.fecha_fin,
               r.estado, r.comentario
        FROM reservas r
        JOIN instrumentos i ON r.instrumento_id = i.id
        ORDER BY r.fecha_inicio DESC
        """
        params: list[Any] = []
    else:
        query = """
        SELECT r.id, r.instrumento_id, i.instrumento,
               r.usuario, r.fecha_inicio, r.fecha_fin,
               r.estado, r.comentario
        FROM reservas r
        JOIN instrumentos i ON r.instrumento_id = i.id
        WHERE r.instrumento_id = ?
        ORDER BY r.fecha_inicio DESC
        """
        params = [instrumento_id]

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def obtener_reserva_por_id(reserva_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM reservas WHERE id = ?", (reserva_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_reserva(
    reserva_id: int,
    instrumento_id: int,
    usuario: str,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    comentario: str,
    estado: str,
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE reservas
        SET instrumento_id = ?,
            usuario = ?,
            fecha_inicio = ?,
            fecha_fin = ?,
            comentario = ?,
            estado = ?
        WHERE id = ?
        """,
        (
            instrumento_id,
            usuario,
            fecha_inicio.strftime("%Y-%m-%d %H:%M:%S"),
            fecha_fin.strftime("%Y-%m-%d %H:%M:%S"),
            comentario,
            estado,
            reserva_id,
        ),
    )
    conn.commit()
    conn.close()


def borrar_reserva(reserva_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM reservas WHERE id = ?", (reserva_id,))
    conn.commit()
    conn.close()


# ==============================
# Inicializar DB
# ==============================
init_db()

# ==============================
# UI: pestañas
# ==============================
tab1, tab2, tab3 = st.tabs(
    ["➕ Cargar instrumento", "📋 Ver base de datos", "📅 Reservas de uso"]
)

# ------------------------------
# TAB 1: Cargar instrumento
# ------------------------------
with tab1:
    st.subheader("Nuevo instrumento")

    with st.form("form_instrumento", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            grupo_unidad = st.text_input("Grupo / Unidad")
            responsable = st.text_input("Responsable", value="Cristian Malavert")
            investigador_grupo = st.text_input("Investigador / Grupo *")
            instrumento = st.text_input("Instrumento *")
            numero_inventario = st.text_input("Número de inventario")

        with col2:
            ubicacion = st.text_input("Ubicación")
            reserva_uso = st.selectbox("Reserva de uso", ["Libre", "Con reserva", "Uso restringido"], index=1)
            estado = st.selectbox("Estado del instrumento", ["Operativo", "En reparación", "Fuera de servicio", "De baja"], index=0)
            descripcion = st.text_area("Descripción / Observaciones")
            foto = st.file_uploader("Foto del instrumento", type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button("Guardar instrumento")

        if submitted:
            if not investigador_grupo or not instrumento:
                st.error("Por favor complete al menos 'Investigador / Grupo' e 'Instrumento'.")
            else:
                foto_path = guardar_imagen(foto)
                insertar_instrumento(
                    grupo_unidad=grupo_unidad,
                    responsable=responsable,
                    investigador_grupo=investigador_grupo,
                    instrumento=instrumento,
                    numero_inventario=numero_inventario,
                    reserva_uso=reserva_uso,
                    estado=estado,
                    ubicacion=ubicacion,
                    descripcion=descripcion,
                    foto_path=foto_path,
                )
                st.success("Instrumento guardado correctamente.")
                do_rerun()

# ------------------------------
# TAB 2: Ver / Editar / Borrar instrumentos
# ------------------------------
with tab2:
    st.subheader("Base de datos de instrumentos")

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        filtro_grupo = st.text_input("Filtrar por Grupo / Unidad")
    with colf2:
        filtro_inv = st.text_input("Filtrar por Investigador / Grupo")
    with colf3:
        filtro_inst = st.text_input("Filtrar por Instrumento")

    df_inst = cargar_instrumentos(filtro_grupo, filtro_inv, filtro_inst)

    if df_inst.empty:
        st.info("Todavía no hay instrumentos cargados que coincidan con el filtro.")
    else:
        st.markdown("#### Tabla de instrumentos")
        df_tabla = df_inst.drop(columns=["foto_path"], errors="ignore")
        st.dataframe(df_tabla, use_container_width=True)

        csv = df_tabla.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar inventario en CSV",
            data=csv,
            file_name="inventario_instrumentos.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("### Detalle de un instrumento")

        ids = df_inst["id"].tolist()
        id_sel = st.selectbox("Seleccionar ID de instrumento", ids, key="inst_detail_select")

        inst_row = df_inst[df_inst["id"] == id_sel].iloc[0]

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown(f"**Grupo / Unidad:** {inst_row['grupo_unidad']}")
            st.markdown(f"**Responsable:** {inst_row['responsable']}")
            st.markdown(f"**Investigador / Grupo:** {inst_row['investigador_grupo']}")
            st.markdown(f"**Instrumento:** {inst_row['instrumento']}")
            st.markdown(f"**Número de inventario:** {inst_row['numero_inventario']}")
            st.markdown(f"**Reserva de uso:** {inst_row['reserva_uso']}")
            st.markdown(f"**Estado:** {inst_row['estado']}")
            st.markdown(f"**Ubicación:** {inst_row['ubicacion']}")
            st.markdown(f"**Descripción:** {inst_row['descripcion']}")
            st.markdown(f"**Fecha de registro:** {inst_row['fecha_registro']}")

        with col_b:
            foto_path = inst_row.get("foto_path", None)
            if foto_path and os.path.exists(foto_path):
                st.image(foto_path, caption="Foto del instrumento")
            else:
                st.caption("Sin foto disponible para este instrumento.")

        st.markdown("---")
        st.markdown("## Editar / Borrar instrumento")

        inst_actual = obtener_instrumento_por_id(int(id_sel))
        if inst_actual is None:
            st.warning("No se encontró el instrumento seleccionado.")
        else:
            with st.expander("✏️ Editar instrumento", expanded=False):
                with st.form("form_editar_instrumento"):
                    c1, c2 = st.columns(2)

                    with c1:
                        e_grupo_unidad = st.text_input("Grupo / Unidad", value=inst_actual.get("grupo_unidad") or "")
                        e_responsable = st.text_input("Responsable", value=inst_actual.get("responsable") or "")
                        e_investigador_grupo = st.text_input("Investigador / Grupo *", value=inst_actual.get("investigador_grupo") or "")
                        e_instrumento = st.text_input("Instrumento *", value=inst_actual.get("instrumento") or "")
                        e_numero_inventario = st.text_input("Número de inventario", value=inst_actual.get("numero_inventario") or "")

                    with c2:
                        e_ubicacion = st.text_input("Ubicación", value=inst_actual.get("ubicacion") or "")
                        e_reserva_uso = st.selectbox(
                            "Reserva de uso",
                            ["Libre", "Con reserva", "Uso restringido"],
                            index=["Libre", "Con reserva", "Uso restringido"].index(inst_actual.get("reserva_uso") or "Con reserva"),
                        )
                        e_estado = st.selectbox(
                            "Estado del instrumento",
                            ["Operativo", "En reparación", "Fuera de servicio", "De baja"],
                            index=["Operativo", "En reparación", "Fuera de servicio", "De baja"].index(inst_actual.get("estado") or "Operativo"),
                        )
                        e_descripcion = st.text_area("Descripción / Observaciones", value=inst_actual.get("descripcion") or "")
                        nueva_foto = st.file_uploader("Reemplazar foto (opcional)", type=["png", "jpg", "jpeg"], key=f"foto_edit_{id_sel}")

                    guardar_cambios = st.form_submit_button("Guardar cambios")

                    if guardar_cambios:
                        if not e_investigador_grupo or not e_instrumento:
                            st.error("Complete al menos 'Investigador / Grupo' e 'Instrumento'.")
                        else:
                            foto_path_final = inst_actual.get("foto_path")
                            if nueva_foto is not None:
                                if foto_path_final and os.path.exists(foto_path_final):
                                    try:
                                        os.remove(foto_path_final)
                                    except OSError:
                                        pass
                                foto_path_final = guardar_imagen(nueva_foto)

                            actualizar_instrumento(
                                instrumento_id=int(id_sel),
                                grupo_unidad=e_grupo_unidad,
                                responsable=e_responsable,
                                investigador_grupo=e_investigador_grupo,
                                instrumento=e_instrumento,
                                numero_inventario=e_numero_inventario,
                                reserva_uso=e_reserva_uso,
                                estado=e_estado,
                                ubicacion=e_ubicacion,
                                descripcion=e_descripcion,
                                foto_path=foto_path_final,
                            )
                            st.success("Instrumento actualizado.")
                            do_rerun()

            with st.expander("🗑️ Borrar instrumento", expanded=False):
                n_res = contar_reservas_de_instrumento(int(id_sel))
                st.write(f"Reservas asociadas a este instrumento: **{n_res}**")

                borrar_con_reservas = st.checkbox(
                    "Borrar también todas las reservas asociadas",
                    value=False,
                    key=f"del_cascade_{id_sel}",
                )
                confirmar = st.text_input("Escribí BORRAR para confirmar", key=f"confirm_del_{id_sel}")

                if st.button("Eliminar definitivamente", key=f"btn_del_{id_sel}"):
                    if confirmar.strip().upper() != "BORRAR":
                        st.error("Confirmación incorrecta. Escribí BORRAR.")
                    else:
                        if n_res > 0 and not borrar_con_reservas:
                            st.error("Este instrumento tiene reservas. Marcá la opción para borrarlas o cancelá.")
                        else:
                            if borrar_con_reservas and n_res > 0:
                                borrar_reservas_de_instrumento(int(id_sel))
                            borrar_instrumento(int(id_sel))
                            st.success("Instrumento eliminado.")
                            do_rerun()

# ------------------------------
# TAB 3: Reservas + editar/borrar reservas
# ------------------------------
with tab3:
    st.subheader("Reservas de uso de instrumentos")

    df_all_inst = cargar_instrumentos()
    if df_all_inst.empty:
        st.info("Primero cargue al menos un instrumento en la pestaña anterior.")
    else:
        opciones = {
            f"[ID {row.id}] {row.instrumento} – {row.investigador_grupo}": int(row.id)
            for _, row in df_all_inst.iterrows()
        }
        etiqueta_seleccion = st.selectbox("Seleccionar instrumento para reservar", list(opciones.keys()), key="inst_reserve_select")
        instrumento_id = opciones[etiqueta_seleccion]

        st.markdown("#### Nueva reserva")
        with st.form("form_reserva", clear_on_submit=True):
            usuario_res = st.text_input("Usuario solicitante *")
            col_fecha1, col_fecha2 = st.columns(2)

            with col_fecha1:
                fecha_inicio_d = st.date_input("Fecha inicio", value=date.today())
                hora_inicio_t = st.time_input("Hora inicio", value=time(9, 0))
            with col_fecha2:
                fecha_fin_d = st.date_input("Fecha fin", value=date.today())
                hora_fin_t = st.time_input("Hora fin", value=time(12, 0))

            comentario_res = st.text_area("Comentario")
            estado_res = st.selectbox("Estado de la reserva", ["Confirmada", "Tentativa", "Cancelada"], index=0)

            submitted_reserva = st.form_submit_button("Registrar reserva")

            if submitted_reserva:
                if not usuario_res:
                    st.error("Por favor complete el campo 'Usuario solicitante'.")
                else:
                    fecha_inicio_dt = datetime.combine(fecha_inicio_d, hora_inicio_t)
                    fecha_fin_dt = datetime.combine(fecha_fin_d, hora_fin_t)

                    if fecha_fin_dt <= fecha_inicio_dt:
                        st.error("La fecha/hora de fin debe ser posterior al inicio.")
                    else:
                        insertar_reserva(
                            instrumento_id=instrumento_id,
                            usuario=usuario_res,
                            fecha_inicio=fecha_inicio_dt,
                            fecha_fin=fecha_fin_dt,
                            comentario=comentario_res,
                            estado=estado_res,
                        )
                        st.success("Reserva registrada correctamente.")
                        do_rerun()

        st.markdown("---")
        st.markdown("#### Reservas registradas")

        ver_todas = st.checkbox("Ver reservas de todos los instrumentos", value=False)

        if ver_todas:
            df_res = cargar_reservas(instrumento_id=None)
        else:
            df_res = cargar_reservas(instrumento_id=instrumento_id)

        if df_res.empty:
            st.info("No hay reservas registradas.")
        else:
            st.dataframe(df_res, use_container_width=True)

            csv_res = df_res.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar reservas en CSV",
                data=csv_res,
                file_name="reservas_instrumentos.csv",
                mime="text/csv",
            )

            st.markdown("---")
            st.markdown("## Editar / Borrar reserva")

            ids_res = df_res["id"].tolist()
            reserva_id_sel = st.selectbox("Seleccionar ID de reserva", ids_res, key="res_edit_select")

            res_actual = obtener_reserva_por_id(int(reserva_id_sel))
            if res_actual is None:
                st.warning("No se encontró la reserva seleccionada.")
            else:
                with st.expander("✏️ Editar reserva", expanded=False):
                    with st.form("form_editar_reserva"):
                        df_inst_all = cargar_instrumentos()
                        mapa_inst = {
                            f"[ID {row.id}] {row.instrumento} – {row.investigador_grupo}": int(row.id)
                            for _, row in df_inst_all.iterrows()
                        }
                        etiquetas = list(mapa_inst.keys())

                        inst_actual_id = int(res_actual.get("instrumento_id"))
                        default_label = next((lab for lab, iid in mapa_inst.items() if iid == inst_actual_id), etiquetas[0])
                        idx_default = etiquetas.index(default_label) if default_label in etiquetas else 0

                        r_inst_label = st.selectbox("Instrumento", etiquetas, index=idx_default, key=f"res_inst_{reserva_id_sel}")
                        r_instrumento_id = mapa_inst[r_inst_label]

                        r_usuario = st.text_input("Usuario solicitante *", value=res_actual.get("usuario") or "")

                        dt_ini = datetime.strptime(res_actual["fecha_inicio"], "%Y-%m-%d %H:%M:%S")
                        dt_fin = datetime.strptime(res_actual["fecha_fin"], "%Y-%m-%d %H:%M:%S")

                        cfi, cff = st.columns(2)
                        with cfi:
                            r_fecha_ini = st.date_input("Fecha inicio", value=dt_ini.date(), key=f"ri_d_{reserva_id_sel}")
                            r_hora_ini = st.time_input("Hora inicio", value=dt_ini.time(), key=f"ri_t_{reserva_id_sel}")
                        with cff:
                            r_fecha_fin = st.date_input("Fecha fin", value=dt_fin.date(), key=f"rf_d_{reserva_id_sel}")
                            r_hora_fin = st.time_input("Hora fin", value=dt_fin.time(), key=f"rf_t_{reserva_id_sel}")

                        r_estado = st.selectbox(
                            "Estado de la reserva",
                            ["Confirmada", "Tentativa", "Cancelada"],
                            index=["Confirmada", "Tentativa", "Cancelada"].index(res_actual.get("estado") or "Confirmada"),
                        )
                        r_coment = st.text_area("Comentario", value=res_actual.get("comentario") or "")

                        guardar_reserva_btn = st.form_submit_button("Guardar cambios")

                        if guardar_reserva_btn:
                            if not r_usuario:
                                st.error("Complete 'Usuario solicitante'.")
                            else:
                                r_dt_ini = datetime.combine(r_fecha_ini, r_hora_ini)
                                r_dt_fin = datetime.combine(r_fecha_fin, r_hora_fin)

                                if r_dt_fin <= r_dt_ini:
                                    st.error("La fecha/hora de fin debe ser posterior al inicio.")
                                else:
                                    actualizar_reserva(
                                        reserva_id=int(reserva_id_sel),
                                        instrumento_id=int(r_instrumento_id),
                                        usuario=r_usuario,
                                        fecha_inicio=r_dt_ini,
                                        fecha_fin=r_dt_fin,
                                        comentario=r_coment,
                                        estado=r_estado,
                                    )
                                    st.success("Reserva actualizada.")
                                    do_rerun()

                with st.expander("🗑️ Borrar reserva", expanded=False):
                    confirmar_r = st.text_input("Escribí BORRAR para confirmar", key=f"confirm_del_res_{reserva_id_sel}")
                    if st.button("Eliminar reserva", key=f"btn_del_res_{reserva_id_sel}"):
                        if confirmar_r.strip().upper() != "BORRAR":
                            st.error("Confirmación incorrecta. Escribí BORRAR.")
                        else:
                            borrar_reserva(int(reserva_id_sel))
                            st.success("Reserva eliminada.")
                            do_rerun()
