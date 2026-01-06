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

API_UPLOAD_URL = "https://proyectoback-h6ajcba8cpewd5bc.brazilsouth-01.azurewebsites.net/storage/pdf"
HTTP_TIMEOUT = 120

UPLOAD_DIR = "uploads"  # respaldo local opcional
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------------------------
# LOGIN Y ROLES (igual a tu versión)
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
    # Cada carga: {id, fecha, estado, comentario}
    st.session_state.cargas = []
if "documentos" not in st.session_state:
    # Por carga_id: lista de docs {nombre_original, nombre_enviado, ruta_local, estado, error, blob_url, blob_name, container}
    st.session_state.documentos = {}
if "next_carga_id" not in st.session_state:
    st.session_state.next_carga_id = 1

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def ahora_str() -> str:
    return datetime.now().isoformat(sep=" ", timespec="microseconds")

def nombre_unico(nombre: str) -> str:
    base, ext = os.path.splitext(nombre)
    return f"{base}_{uuid.uuid4().hex}{ext}"

def subir_pdf_a_api(file_bytes: bytes, filename: str) -> dict:
    files = {"file": (filename, file_bytes, "application/pdf")}
    resp = requests.post(API_UPLOAD_URL, files=files, timeout=HTTP_TIMEOUT)
    if resp.status_code not in (200, 201):
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    try:
        return resp.json()
    except Exception:
        raise Exception(f"Respuesta no es JSON: {resp.text}")

def crear_carga() -> int:
    carga_id = st.session_state.next_carga_id
    st.session_state.next_carga_id += 1

    st.session_state.cargas.insert(0, {
        "id": carga_id,
        "fecha": ahora_str(),
        "estado": "EN_PROCESO",
        "comentario": "Carga iniciada"
    })
    st.session_state.documentos[carga_id] = []
    return carga_id

def actualizar_carga(carga_id: int, estado: str, comentario: str):
    for c in st.session_state.cargas:
        if c["id"] == carga_id:
            c["estado"] = estado
            c["comentario"] = comentario
            return

def registrar_documento(carga_id: int, doc: dict):
    st.session_state.documentos.setdefault(carga_id, []).append(doc)

def documentos_de_carga(carga_id: int):
    return st.session_state.documentos.get(carga_id, [])

def reintentar_carga(carga_id: int):
    docs = documentos_de_carga(carga_id)
    if not docs:
        actualizar_carga(carga_id, "ERROR", "No hay documentos asociados para reintentar")
        st.error("No hay documentos para reintentar")
        return

    # Solo reintentar los que están en ERROR
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

            if os.path.getsize(ruta_local) == 0:
                raise Exception("Archivo local vacío")

            with open(ruta_local, "rb") as f:
                file_bytes = f.read()

            r = subir_pdf_a_api(file_bytes, d["nombre_enviado"])

            d["estado"] = "OK"
            d["error"] = ""
            d["container"] = r.get("container")
            d["blob_name"] = r.get("blob_name")
            d["blob_url"] = r.get("blob_url")

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
    ["Dashboard", "Subir PDFs"] if st.session_state.rol == "admin" else ["Dashboard"]
)

# --------------------------------------------------
# DASHBOARD (mismo estilo/columnas)
# --------------------------------------------------
if menu == "Dashboard":
    st.subheader("📝 Estado de las cargas")

    cargas = st.session_state.cargas

    if not cargas:
        st.info("No hay cargas registradas en esta sesión.")
    else:
        header = st.columns([1, 3, 2, 6, 2])
        header[0].markdown("**ID**")
        header[1].markdown("**Fecha**")
        header[2].markdown("**Estado**")
        header[3].markdown("**Comentario**")
        header[4].markdown("**Acción**")

        for row in cargas:
            cols = st.columns([1, 3, 2, 6, 2])

            cols[0].write(row["id"])
            cols[1].write(row["fecha"])
            cols[2].write(row["estado"])
            cols[3].write(row["comentario"])

            if row["estado"] == "ERROR" and st.session_state.rol == "admin":
                if cols[4].button("🔄 Reintentar", key=f"retry_{row['id']}"):
                    reintentar_carga(int(row["id"]))
                    st.rerun()
            else:
                cols[4].write("—")

    # Opcional: ver detalles de una carga (no cambia el dashboard principal)
    st.divider()
    st.subheader("📄 Detalle de documentos por carga")
    carga_id = st.number_input("ID de carga", min_value=1, step=1)

    if st.button("Ver documentos"):
        docs = documentos_de_carga(int(carga_id))
        if not docs:
            st.info("No hay documentos para esa carga.")
        else:
            # tabla de detalle (no altera los campos del dashboard)
            st.dataframe(docs, use_container_width=True)

# --------------------------------------------------
# SUBIR PDFs
# --------------------------------------------------
elif menu == "Subir PDFs":
    st.subheader("📤 Carga de PDFs")

    col1, col2 = st.columns([2, 1])
    with col2:
        guardar_respaldo = st.checkbox("Guardar respaldo local", value=True)

    archivos = st.file_uploader(
        "Selecciona archivos PDF",
        type=["pdf"],
        accept_multiple_files=True
    )

    if archivos:
        carga_id = crear_carga()

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
                "blob_url": ""
            }

            try:
                if archivo.size == 0:
                    raise Exception("PDF vacío")

                file_bytes = archivo.getbuffer().tobytes()
                nombre_envio = nombre_unico(archivo.name)
                doc["nombre_enviado"] = nombre_envio

                # respaldo local para reintentos
                if guardar_respaldo:
                    ruta_local = os.path.join(UPLOAD_DIR, nombre_envio)
                    with open(ruta_local, "wb") as f:
                        f.write(file_bytes)
                    doc["ruta_local"] = ruta_local

                # subir al backend
                r = subir_pdf_a_api(file_bytes, nombre_envio)

                doc["estado"] = "OK"
                doc["container"] = r.get("container")
                doc["blob_name"] = r.get("blob_name")
                doc["blob_url"] = r.get("blob_url")

                ok += 1

            except Exception as e:
                doc["estado"] = "ERROR"
                doc["error"] = str(e)
                errores.append(f"{archivo.name}: {str(e)}")

            registrar_documento(carga_id, doc)
            progress.progress(int(((i + 1) / total) * 100))
            time.sleep(0.03)

        # estado final de la carga
        if errores:
            actualizar_carga(carga_id, "ERROR", f"Errores en carga. OK={ok}/{total}")
            st.error("Carga finalizada con errores")
            st.text("\n".join(errores))
        else:
            actualizar_carga(carga_id, "COMPLETADO", f"Carga completada correctamente. OK={ok}/{total}")
            st.success("Carga completada correctamente")

        st.divider()
        st.subheader(f"Resultado de la carga #{carga_id}")
        st.dataframe(documentos_de_carga(carga_id), use_container_width=True)

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
st.sidebar.divider()
if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()
