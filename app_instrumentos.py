# -*- coding: utf-8 -*-
"""
Created on Tue Dec 30 12:18:15 2025

@author: Malavert
"""
"""
Inventario de Instrumentos - Cultivos Industriales - FAUBA
Backend persistente: Supabase PostgreSQL + Supabase Storage.
"""
from datetime import datetime, date, time
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse, unquote
import uuid
import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Inventario de Instrumentos", page_icon="🧪", layout="wide")
st.markdown("""
<style>
button[data-baseweb="tab"] p {font-size:24px!important;font-weight:600!important;}
button[data-baseweb="tab"][aria-selected="true"] p {font-size:24px!important;color:#ff4b4b!important;}
button[data-baseweb="tab"] {padding:16px 24px!important;}
</style>""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    SUPABASE_BUCKET = st.secrets.get("SUPABASE_BUCKET", "instrumentos-fotos")
except Exception:
    st.error("Faltan las credenciales de Supabase en Secrets de Streamlit.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

LOGO_LEFT = BASE_DIR / "logo_fauba.jpg"
LOGO_RIGHT = BASE_DIR / "Logo_CI.jpg"
col_left, col_center, col_right = st.columns([2.2, 6, 2.2])
with col_left:
    if LOGO_LEFT.exists(): st.image(str(LOGO_LEFT), width="stretch")
with col_center:
    st.title("Inventario de Instrumentos - Cultivos Industriales - FAUBA")
    st.markdown("""<p style='font-size:22px;margin-top:-8px;text-align:center;'>
    Sistema para registrar y consultar instrumentos, con información básica,
    responsable y reservas de uso.</p>""", unsafe_allow_html=True)
with col_right:
    if LOGO_RIGHT.exists(): st.image(str(LOGO_RIGHT), width="stretch")

def do_rerun():
    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

def parse_datetime(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

def guardar_imagen(uploaded_file) -> Optional[str]:
    """
    Sube la foto al bucket privado de Supabase y devuelve solo la ruta/nombre
    del archivo. Esa ruta se guarda en la columna foto_url.
    """
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg"]:
        suffix = ".png"

    nombre = f"{uuid.uuid4().hex}{suffix}"

    supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=nombre,
        file=uploaded_file.getvalue(),
        file_options={
            "content-type": getattr(uploaded_file, "type", None)
            or "application/octet-stream",
            "upsert": "false",
        },
    )

    return nombre


def obtener_url_foto(foto_path: Optional[str]) -> Optional[str]:
    """
    Genera una URL firmada temporal para visualizar una foto
    guardada en el bucket privado de Supabase.
    """

    # Sin foto / None / NaN de pandas
    if foto_path is None:
        return None

    try:
        if pd.isna(foto_path):
            return None
    except (TypeError, ValueError):
        pass

    # Supabase necesita que path sea str
    foto_path = str(foto_path).strip()

    if not foto_path:
        return None

    # Compatibilidad con registros antiguos que tenían guardada
    # una URL completa en vez del nombre/ruta del archivo
    if foto_path.startswith("http://") or foto_path.startswith("https://"):
        return foto_path

    response = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(
        foto_path,
        3600,
    )

    if isinstance(response, dict):
        return response.get("signedURL") or response.get("signedUrl")

    return str(response)


def borrar_imagen_por_url(foto_path: Optional[str]):
    """
    Borra del bucket la imagen cuya ruta está guardada en foto_url.
    """
    if not foto_path:
        return

    try:
        supabase.storage.from_(SUPABASE_BUCKET).remove([foto_path])
    except Exception:
        pass


def insertar_instrumento(grupo_unidad, responsable, investigador_grupo, instrumento,
                         numero_inventario, reserva_uso, estado, ubicacion, descripcion, foto_url):
    supabase.table("instrumentos").insert({
        "grupo_unidad":grupo_unidad, "responsable":responsable,
        "investigador_grupo":investigador_grupo, "instrumento":instrumento,
        "numero_inventario":numero_inventario, "reserva_uso":reserva_uso,
        "estado":estado, "ubicacion":ubicacion, "descripcion":descripcion,
        "foto_url":foto_url}).execute()

def cargar_instrumentos(filtro_grupo="", filtro_investigador="", filtro_instrumento=""):
    q = supabase.table("instrumentos").select("*").order("id")
    if filtro_grupo: q = q.ilike("grupo_unidad", f"%{filtro_grupo}%")
    if filtro_investigador: q = q.ilike("investigador_grupo", f"%{filtro_investigador}%")
    if filtro_instrumento: q = q.ilike("instrumento", f"%{filtro_instrumento}%")
    return pd.DataFrame(q.execute().data or [])

def obtener_instrumento_por_id(instrumento_id):
    r = supabase.table("instrumentos").select("*").eq("id", instrumento_id).limit(1).execute()
    return r.data[0] if r.data else None

def actualizar_instrumento(instrumento_id, grupo_unidad, responsable, investigador_grupo,
                           instrumento, numero_inventario, reserva_uso, estado, ubicacion,
                           descripcion, foto_url):
    supabase.table("instrumentos").update({
        "grupo_unidad":grupo_unidad, "responsable":responsable,
        "investigador_grupo":investigador_grupo, "instrumento":instrumento,
        "numero_inventario":numero_inventario, "reserva_uso":reserva_uso,
        "estado":estado, "ubicacion":ubicacion, "descripcion":descripcion,
        "foto_url":foto_url}).eq("id", instrumento_id).execute()

def contar_reservas_de_instrumento(instrumento_id):
    r = supabase.table("reservas").select("id").eq("instrumento_id", instrumento_id).execute()
    return len(r.data or [])

def borrar_reservas_de_instrumento(instrumento_id):
    supabase.table("reservas").delete().eq("instrumento_id", instrumento_id).execute()

def borrar_instrumento(instrumento_id):
    inst = obtener_instrumento_por_id(instrumento_id)
    foto = inst.get("foto_url") if inst else None
    supabase.table("instrumentos").delete().eq("id", instrumento_id).execute()
    borrar_imagen_por_url(foto)

def insertar_reserva(instrumento_id, usuario, fecha_inicio, fecha_fin, comentario,
                     estado="Confirmada"):
    supabase.table("reservas").insert({
        "instrumento_id":instrumento_id, "usuario":usuario,
        "fecha_inicio":fecha_inicio.isoformat(), "fecha_fin":fecha_fin.isoformat(),
        "comentario":comentario, "estado":estado}).execute()

def cargar_reservas(instrumento_id=None):
    q = supabase.table("reservas").select(
        "id,instrumento_id,usuario,fecha_inicio,fecha_fin,estado,comentario,instrumentos(instrumento)"
    ).order("fecha_inicio", desc=True)
    if instrumento_id is not None: q = q.eq("instrumento_id", instrumento_id)
    rows = []
    for x in q.execute().data or []:
        inst = x.pop("instrumentos", None)
        x["instrumento"] = inst.get("instrumento") if isinstance(inst, dict) else ""
        rows.append(x)
    cols = ["id","instrumento_id","instrumento","usuario","fecha_inicio","fecha_fin","estado","comentario"]
    return pd.DataFrame(rows, columns=cols)

def obtener_reserva_por_id(reserva_id):
    r = supabase.table("reservas").select("*").eq("id", reserva_id).limit(1).execute()
    return r.data[0] if r.data else None

def actualizar_reserva(reserva_id, instrumento_id, usuario, fecha_inicio, fecha_fin,
                       comentario, estado):
    supabase.table("reservas").update({
        "instrumento_id":instrumento_id, "usuario":usuario,
        "fecha_inicio":fecha_inicio.isoformat(), "fecha_fin":fecha_fin.isoformat(),
        "comentario":comentario, "estado":estado}).eq("id", reserva_id).execute()

def borrar_reserva(reserva_id):
    supabase.table("reservas").delete().eq("id", reserva_id).execute()


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
                foto_url = guardar_imagen(foto)
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
                    foto_url=foto_url,
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
        df_tabla = df_inst.drop(columns=["foto_url"], errors="ignore")
        st.dataframe(df_tabla, width="stretch")

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
            foto_path = inst_row.get("foto_url", None)
            foto_url = obtener_url_foto(foto_path)
            if foto_url:
                st.image(foto_url, caption="Foto del instrumento")
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
                            foto_url_final = inst_actual.get("foto_url")
                            if nueva_foto is not None:
                                borrar_imagen_por_url(foto_url_final)
                                foto_url_final = guardar_imagen(nueva_foto)

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
                                foto_url=foto_url_final,
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
            st.dataframe(df_res, width="stretch")

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

                        dt_ini = parse_datetime(res_actual["fecha_inicio"])
                        dt_fin = parse_datetime(res_actual["fecha_fin"])

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
