import streamlit as st
import sqlite3
import pandas as pd
import time
import os
from datetime import datetime
import uuid

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(page_title="Dashboard Cargas PDF", layout="wide")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------------------------
# LOGIN Y ROLES
# --------------------------------------------------
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "usuario": {"password": "user123", "rol": "usuario"}
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
# BASE DE DATOS
# --------------------------------------------------
def get_connection():
    return sqlite3.connect("crud.db", check_same_thread=False)

conn = get_connection()
cursor = conn.cursor()

# --------------------------------------------------
# TABLAS
# --------------------------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS cargas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    estado TEXT,
    comentario TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_archivo TEXT,
    ruta TEXT,
    tamaño_kb REAL,
    fecha_carga TEXT,
    id_carga INTEGER
)
""")
conn.commit()

# --------------------------------------------------
# FUNCIONES DE BD
# --------------------------------------------------
def crear_carga():
    cursor.execute("""
        INSERT INTO cargas (fecha, estado, comentario)
        VALUES (?, ?, ?)
    """, (datetime.now(), "EN_PROCESO", "Carga iniciada"))
    conn.commit()
    return cursor.lastrowid

def actualizar_carga(id_carga, estado, comentario):
    cursor.execute("""
        UPDATE cargas SET estado=?, comentario=? WHERE id=?
    """, (estado, comentario, id_carga))
    conn.commit()

def guardar_pdf(nombre, ruta, tamaño, id_carga):
    cursor.execute("""
        INSERT INTO documentos
        (nombre_archivo, ruta, tamaño_kb, fecha_carga, id_carga)
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, ruta, tamaño, datetime.now(), id_carga))
    conn.commit()

def obtener_cargas():
    return pd.read_sql("SELECT * FROM cargas ORDER BY id DESC", conn)

def obtener_documentos_por_carga(id_carga):
    return pd.read_sql(
        "SELECT * FROM documentos WHERE id_carga=?",
        conn,
        params=(id_carga,)
    )

def nombre_unico(nombre):
    base, ext = os.path.splitext(nombre)
    return f"{base}_{uuid.uuid4().hex}{ext}"

# --------------------------------------------------
# REINTENTAR CARGA
# --------------------------------------------------
def reintentar_carga(id_carga):
    actualizar_carga(id_carga, "EN_PROCESO", "Reintentando carga")

    docs = obtener_documentos_por_carga(id_carga)
    progress = st.progress(0)
    total = len(docs)

    errores = []

    for i, row in docs.iterrows():
        try:
            if not os.path.exists(row["ruta"]):
                raise Exception("Archivo no existe")

            if os.path.getsize(row["ruta"]) == 0:
                raise Exception("Archivo vacío")

            time.sleep(0.1)
            progress.progress(int(((i + 1) / total) * 100))

        except Exception as e:
            errores.append(f"{row['nombre_archivo']}: {str(e)}")

    if errores:
        actualizar_carga(id_carga, "ERROR", " | ".join(errores))
        st.error("Reintento fallido")
    else:
        actualizar_carga(id_carga, "COMPLETADO", "Reintento exitoso")
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
# DASHBOARD
# --------------------------------------------------
if menu == "Dashboard":
    st.subheader("📈 Estado de las cargas")

    df = obtener_cargas()

    if df.empty:
        st.info("No hay cargas registradas")
    else:
        header = st.columns([1, 3, 2, 6, 2])
        header[0].markdown("**ID**")
        header[1].markdown("**Fecha**")
        header[2].markdown("**Estado**")
        header[3].markdown("**Comentario**")
        header[4].markdown("**Acción**")

        for _, row in df.iterrows():
            cols = st.columns([1, 3, 2, 6, 2])

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

    archivos = st.file_uploader(
        "Selecciona archivos PDF",
        type=["pdf"],
        accept_multiple_files=True
    )

    if archivos:
        id_carga = crear_carga()
        progress = st.progress(0)
        errores = []

        for i, archivo in enumerate(archivos):
            try:
                if archivo.size == 0:
                    raise Exception("PDF vacío")

                nombre = nombre_unico(archivo.name)
                ruta = os.path.join(UPLOAD_DIR, nombre)

                with open(ruta, "wb") as f:
                    f.write(archivo.getbuffer())

                guardar_pdf(
                    nombre,
                    ruta,
                    round(archivo.size / 1024, 2),
                    id_carge
                )

                progress.progress(int(((i + 1) / len(archivos)) * 100))
                time.sleep(0.05)

            except Exception as e:
                errores.append(f"{archivo.name}: {str(e)}")

        if errores:
            actualizar_carga(id_carga, "ERROR", " | ".join(errores))
            st.error("Carga finalizada con errores")
            st.text("\n".join(errores))
        else:
            actualizar_carga(id_carga, "COMPLETADO", "Carga completada correctamente")
            st.success("Carga completada correctamente")

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
st.sidebar.divider()
if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()
