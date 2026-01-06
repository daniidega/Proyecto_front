import streamlit as st
import requests
import os
import uuid
import time
from datetime import datetime

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
st.set_page_config(page_title="Dashboard Cargas PDF", layout="wide")

API_BASE = "https://proyectoback-h6ajcba8cpewd5bc.brazilsouth-01.azurewebsites.net"
API_UPLOAD_URL = f"{API_BASE}/storage/pdf"
API_ID_CARGA_URL = f"{API_BASE}/dashboard/id-carga"

HTTP_TIMEOUT = 120

UPLOAD_DIR = "uploads"  # respaldo local opcional
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEBUG_API = False  # <- ponlo True temporalmente si quieres ver status/response

# --------------------------------------------------
# LOGIN Y ROLES
# --------------------------------------------------
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "usuario": {"password": "user123", "rol": "usuario"},
}

def login():
    st.title("🔐 Login")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            st.session_state.login = True
            st.session_state.rol = USUARIOS[usuario]["rol"]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    login()
    st.stop()

# --------------------------------------------------
# STATE EN MEMORIA (sin SQLite)
# --------------------------------------------------
if "cargas" not in st.session_state:
    # Cada carga: {id (str), fecha, estado, comentario}
    st.session_state.cargas = []

if "documentos" not in st.session_state:
    # Por carga_id (str): lista de docs
    st.session_state.documentos = {}

if "id_carga_actual" not in st.session_state:
    st.session_state.id_carga_actual = ""

# clave dinámica para resetear el file_uploader y evitar re-subidas
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 1

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def ahora_str() -> str:
    return datetime.now().isoformat(sep=" ", timespec="microseconds")

def nombre_unico(nombre: str) -> str:
    base, ext = os.path.splitext(nombre)
    return f"{base}_{uuid.uuid4().hex}{ext}"

def obtener_id_carga() -> str:
    resp = requests.get(API_ID_CARGA_URL, timeout=HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if "id_carga" not in data or not data["id_carga"]:
        raise Exception(f"Respuesta inválida: {data}")
    return data["id_carga"]

def _normalizar_respuesta_upload(api_json: dict) -> dict:
    """
    Backend devuelve:
      { "blob": {container, blob_name, url}, "mongo": {...} }

    Front usa:
      container, blob_name, blob_url
    """
    blob = (api_json or {}).get("blob") or {}
    return {
        "container": blob.get("container"),
        "blob_name": blob.get("blob_name"),
        "blob_url": blob.get("url"),
        "mongo": (api_json or {}).get("mongo"),
        "raw": api_json,
    }

def subir_pdf_a_api(file_bytes: bytes, filename: str, id_carga: str) -> dict:
    if not id_carga:
        raise Exception("id_carga vacío: no se puede enviar el PDF")

    files = {"file": (filename, file_bytes, "application/pdf")}
    data = {"id_carga": id_carga}

    if DEBUG_API:
        st.write("DEBUG -> Enviando id_carga:", id_carga)
        st.write("DEBUG -> filename:", filename)

    resp = requests.post(API_UPLOAD_URL, files=files, data=data, timeout=HTTP_TIMEOUT)

    if DEBUG_API:
        st.write("DEBUG -> status_code:", resp.status_code)
        st.write("DEBUG -> response_text:", resp.text)

    if resp.status_code not in (200, 201):
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")

    return _normalizar_respuesta_upload(resp.json())

def crear_carga(carga_id: str) -> str:
    st.session_state.cargas.insert(0, {
        "id": carga_id,
        "fecha": ahora_str(),
        "estado": "EN_PROCESO",
        "comentario": "Carga iniciada",
    })
    st.session_state.documentos[carga_id] = []
    return carga_id

def actualizar_carga(carga_id: str, estado: str, comentario: str):
    for c in st.session_state.cargas:
        if c["id"] == carga_id:
            c["estado"] = estado
            c["comentario"] = comentario
            return

def registrar_documento(carga_id: str, doc: dict):
    st.session_state.documentos.setdefault(carga_id, []).append(doc)

def documentos_de_carga(carga_id: str):
    return st.session_state.documentos.get(carga_id, [])

def reintentar_carga(carga_id: str):
    docs = documentos_de_carga(carga_id)
    if not docs:
        actualizar_carga(carga_id, "ERROR", "No hay documentos asociados para reintentar")
        st.error("No hay documentos para reintentar")
        return

    fallidos = [d for d in docs if d.get("estado") == "ERROR"]
    if not fallidos:
        actualizar_carga(carga_id, "COMPLETADO", "No hay documentos en ERROR para reintentar")
        st.info("No hay documentos en ERROR para reintentar")
        return

    actualizar_carga(carga_id, "EN_PROCESO", "Reintentando carga")

    progress = st.progress(0)
    total = len(fallidos)
    ok = 0
    errores = []

    for i, d in enumerate(fallidos):
        try:
            ruta_local = d.get("ruta_local")
            if not ruta_local or not os.path.exists(ruta_local):
                raise Exception("No existe respaldo local para reintentar (habilita 'Guardar respaldo local')")

            with open(ruta_local, "rb") as f:
                file_bytes = f.read()

            # ✅ Se reenvía el MISMO id_carga (carga_id)
            r = subir_pdf_a_api(file_bytes, d["nombre_enviado"], carga_id)

            d["estado"] = "OK"
            d["error"] = ""
            d["container"] = r.get("container") or ""
            d["blob_name"] = r.get("blob_name") or ""
            d["blob_url"] = r.get("blob_url") or ""

            ok += 1

        except Exception as e:
            d["estado"] = "ERROR"
            d["error"] = str(e)
            errores.append(f"{d.get('nombre_original')}: {str(e)}")

        progress.progress(int(((i + 1) / total) * 100))
        time.sleep(0.03)

    if errores:
        actualizar_carga(carga_id, "ERROR", f"Reintento con errores. OK={ok}/{total}")
        st.error("Reintento finalizado con errores")
        st.text("\n".join(errores))
    else:
        actualizar_carga(carga_id, "COMPLETADO", f"Reintento exitoso. OK={ok}/{total}")
        st.success("Reintento exitoso")

# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("📊 Dashboard de Cargas PDF")
st.sidebar.success(f"Rol: {st.session_state.rol}")

menu = st.sidebar.selectbox(
    "Menú",
    ["Dashboard", "Subir PDFs"] if st.session_state.rol == "admin" else ["Dashboard"],
)

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
if menu == "Dashboard":
    st.subheader("📝 Estado de las cargas")

    cargas = st.session_state.cargas
    if not cargas:
        st.info("No hay cargas registradas en esta sesión.")
    else:
        header = st.columns([2, 3, 2, 6, 2])
        header[0].markdown("**ID Carga**")
        header[1].markdown("**Fecha**")
        header[2].markdown("**Estado**")
        header[3].markdown("**Comentario**")
        header[4].markdown("**Acción**")

        for row in cargas:
            cols = st.columns([2, 3, 2, 6, 2])
            cols[0].write(row["id"])
            cols[1].write(row["fecha"])
            cols[2].write(row["estado"])
            cols[3].write(row["comentario"])

            if row["estado"] == "ERROR" and st.session_state.rol == "admin":
                if cols[4].button("🔄 Reintentar", key=f"retry_{row['id']}"):
                    reintentar_carga(row["id"])
                    st.rerun()
            else:
                cols[4].write("—")

# --------------------------------------------------
# SUBIR PDFs
# --------------------------------------------------
elif menu == "Subir PDFs":
    st.subheader("📤 Carga de PDFs")

    col1, col2 = st.columns([2, 1])
    with col2:
        guardar_respaldo = st.checkbox("Guardar respaldo local", value=True)

    # ID automático
    if not st.session_state.id_carga_actual:
        try:
            st.session_state.id_carga_actual = obtener_id_carga()
        except Exception as e:
            st.error(f"No se pudo generar ID de carga: {e}")
            st.stop()

    st.info(f"ID Carga asignado: **{st.session_state.id_carga_actual}**")

    archivos = st.file_uploader(
        "Selecciona archivos PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
    )

    iniciar = st.button("Iniciar carga", disabled=not bool(archivos))

    if iniciar and archivos:
        carga_id = crear_carga(st.session_state.id_carga_actual)

        progress = st.progress(0)
        total = len(archivos)
        ok = 0
        errores = []

        for i, archivo in enumerate(archivos):
            doc = {
                "nombre_original": archivo.name,
                "nombre_enviado": "",
                "ruta_local": "",
                "estado": "PENDIENTE",
                "error": "",
                "container": "",
                "blob_name": "",
                "blob_url": "",
            }

            try:
                if archivo.size == 0:
                    raise Exception("PDF vacío")

                file_bytes = archivo.getbuffer().tobytes()
                nombre_envio = nombre_unico(archivo.name)
                doc["nombre_enviado"] = nombre_envio

                if guardar_respaldo:
                    ruta_local = os.path.join(UPLOAD_DIR, nombre_envio)
                    with open(ruta_local, "wb") as f:
                        f.write(file_bytes)
                    doc["ruta_local"] = ruta_local

                # ✅ Se envía id_carga (carga_id)
                r = subir_pdf_a_api(file_bytes, nombre_envio, carga_id)

                doc["estado"] = "OK"
                doc["container"] = r.get("container") or ""
                doc["blob_name"] = r.get("blob_name") or ""
                doc["blob_url"] = r.get("blob_url") or ""

                ok += 1

            except Exception as e:
                doc["estado"] = "ERROR"
                doc["error"] = str(e)
                errores.append(f"{archivo.name}: {str(e)}")

            registrar_documento(carga_id, doc)
            progress.progress(int(((i + 1) / total) * 100))
            time.sleep(0.03)

        if errores:
            actualizar_carga(carga_id, "ERROR", f"Errores en carga. OK={ok}/{total}")
            st.error("Carga finalizada con errores")
            st.text("\n".join(errores))
        else:
            actualizar_carga(carga_id, "COMPLETADO", f"Carga completada correctamente. OK={ok}/{total}")
            st.success("Carga completada correctamente")

        # Nuevo ID para próxima carga
        try:
            st.session_state.id_carga_actual = obtener_id_carga()
        except Exception:
            st.session_state.id_carga_actual = ""

        st.session_state.uploader_key += 1
        st.rerun()

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
st.sidebar.divider()
if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()
