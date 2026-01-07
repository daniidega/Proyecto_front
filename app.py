import streamlit as st
import requests
import os
import uuid
import time
import base64
from typing import Optional

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
APP_NAME = "Extracta"
LOGO_PATH = "assets/buho.png"

API_BASE = "http://localhost:8000"
API_UPLOAD_URL = f"{API_BASE}/storage/pdf"
API_ID_CARGA_URL = f"{API_BASE}/dashboard/id-carga"
API_DASHBOARD_CARGAS_URL = f"{API_BASE}/dashboard/cargas"
API_RETRY_URL = f"{API_BASE}/dashboard/cargas"
API_EXCEL_URL = f"{API_BASE}/dashboard/cargas"

HTTP_TIMEOUT = 120
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(
    page_title=APP_NAME,
    layout="wide",
    page_icon="🦉",
)

# --------------------------------------------------
# CSS (STREAMLIT 1.52.2 FRIENDLY)
# --------------------------------------------------
def inject_css():
    st.markdown(
        """
        <style>
          header[data-testid="stHeader"] { display: none !important; }
          div[data-testid="stToolbar"] { display: none !important; }

          html, body, [class*="css"] { font-size: 18px !important; }
          .block-container { padding-top: 0.9rem !important; padding-bottom: 2rem !important; }

          .stApp{
            background:
              radial-gradient(1200px 700px at 10% 0%, rgba(0, 120, 212, 0.18), transparent 60%),
              radial-gradient(900px 600px at 90% 10%, rgba(0, 153, 188, 0.14), transparent 55%),
              linear-gradient(180deg, #0b1220 0%, #070b14 100%) !important;
          }

          h1 { font-size: 34px !important; }
          h2 { font-size: 28px !important; }
          h3 { font-size: 22px !important; }
          h1,h2,h3 { color: rgba(255,255,255,0.92) !important; }

          /* Sidebar */
          section[data-testid="stSidebar"]{
            background: linear-gradient(180deg, #0a0f1c 0%, #070b14 100%) !important;
            border-right: 1px solid rgba(255,255,255,0.08) !important;
          }
          section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.90) !important; }

          /* Selectbox sidebar */
          section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 12px !important;
          }
          section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="combobox"]{
            background: transparent !important;
            color: rgba(255,255,255,0.95) !important;
          }
          section[data-testid="stSidebar"] div[data-baseweb="select"] span,
          section[data-testid="stSidebar"] div[data-baseweb="select"] input{
            color: rgba(255,255,255,0.95) !important;
            -webkit-text-fill-color: rgba(255,255,255,0.95) !important;
          }

          ul[role="listbox"]{
            background: rgba(10, 15, 28, 0.98) !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            border-radius: 12px !important;
            padding: 6px !important;
          }
          ul[role="listbox"] li{
            color: rgba(255,255,255,0.92) !important;
            border-radius: 10px !important;
            font-size: 16px !important;
          }

          /* Card general */
          .card{
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 18px;
            background: rgba(255,255,255,0.06);
            box-shadow: 0 14px 34px rgba(0,0,0,0.35);
            padding: 22px 24px;
          }

          /* Login */
          .login-wrap { max-width: 460px; margin: 7vh auto 0 auto; }
          .soft-divider { height: 1px; background: rgba(255,255,255,0.10); margin: 16px 0; }

          /* Botones */
          .stButton button, div[data-testid="stDownloadButton"] button{
            border-radius: 12px !important;
            font-size: 16px !important;
            font-weight: 800 !important;
            border: 1px solid rgba(255,255,255,0.16) !important;
            background: rgba(255,255,255,0.08) !important;
            color: rgba(255,255,255,0.92) !important;
            padding: 0.75rem 1.0rem !important;
          }
          .stButton button:hover, div[data-testid="stDownloadButton"] button:hover{
            border-color: rgba(0,120,212,0.60) !important;
            background: rgba(0,120,212,0.22) !important;
          }

          /* KPI */
          .kpi-row { display:flex; gap: 12px; flex-wrap: wrap; margin: 12px 0 16px 0; }
          .kpi {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
            background: rgba(255,255,255,0.06);
            padding: 14px 16px;
            min-width: 190px;
          }
          .kpi .k { font-size: 13px; font-weight: 900; letter-spacing:.6px; text-transform: uppercase; color: rgba(255,255,255,0.62); }
          .kpi .v { font-size: 26px; font-weight: 950; color: rgba(255,255,255,0.92); margin-top: 2px; }

          /* Tabla tipo datatable */
          .grid-wrap {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 16px;
            background: rgba(255,255,255,0.04);
            box-shadow: 0 14px 34px rgba(0,0,0,0.35);
            overflow: hidden;
          }
          .grid-head, .grid-row {
            display: grid;
            grid-template-columns: 2.2fr 2.4fr 1.6fr 5.2fr 2.3fr;
            gap: 12px;
            align-items: center;
            padding: 14px 16px;
          }
          .grid-head {
            background: rgba(10, 15, 28, 0.88);
            border-bottom: 1px solid rgba(255,255,255,0.10);
            font-size: 14px;
            font-weight: 950;
            letter-spacing: .6px;
            text-transform: uppercase;
            color: rgba(255,255,255,0.75);
          }
          .grid-row { border-bottom: 1px solid rgba(255,255,255,0.06); }
          .grid-row:nth-child(even) { background: rgba(255,255,255,0.02); }
          .grid-row:hover { background: rgba(0,120,212,0.12); }

          .grid-cell {
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            font-size: 18px !important;
            color: rgba(255,255,255,0.92) !important;
            font-weight: 750 !important;
          }

          /* ID CARGA (TABLA) – BLANCO FORZADO */
          .grid-mono, .grid-mono *{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            font-weight: 950 !important;
            letter-spacing: 0.4px !important;
            text-shadow: 0 0 10px rgba(0,120,212,0.45) !important;
          }

          .grid-muted { color: rgba(255,255,255,0.78) !important; font-size: 17px !important; font-weight: 700 !important; }

          .chip {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 9px 14px !important;
            border-radius: 999px;
            font-size: 16px !important;
            font-weight: 900;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.06);
            color: rgba(255,255,255,0.92);
          }
          .chip-ok { border-color: rgba(46,204,113,0.40); background: rgba(46,204,113,0.14); }
          .chip-warn { border-color: rgba(241,196,15,0.50); background: rgba(241,196,15,0.14); }
          .chip-err { border-color: rgba(231,76,60,0.55); background: rgba(231,76,60,0.14); }

          /* Panel búho */
          .owl-panel {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 16px;
            background: rgba(255,255,255,0.04);
            box-shadow: 0 14px 34px rgba(0,0,0,0.35);
            height: 170px;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          .owl-panel img { max-height: 120px; width: auto; opacity: 0.95; }

          /* LOGIN INPUTS (NO BLANCOS) – Streamlit 1.52.2 */
          div[data-testid="stTextInput"] label,
          div[data-testid="stPassword"] label{
            color: rgba(255,255,255,0.92) !important;
            font-weight: 750 !important;
            font-size: 16px !important;
          }
          div[data-testid="stTextInput"] div[data-baseweb="base-input"],
          div[data-testid="stPassword"]  div[data-baseweb="base-input"],
          div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
          div[data-testid="stPassword"]  div[data-baseweb="input"] > div,
          div[data-testid="stTextInput"] div[data-baseweb="input"],
          div[data-testid="stPassword"]  div[data-baseweb="input"]{
            background-color: rgba(255,255,255,0.10) !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
            border-radius: 12px !important;
          }
          div[data-testid="stTextInput"] input,
          div[data-testid="stPassword"]  input{
            background-color: rgba(255,255,255,0.10) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #ffffff !important;
            font-size: 18px !important;
            padding: 14px 16px !important;
          }
          div[data-testid="stTextInput"] input:-webkit-autofill,
          div[data-testid="stTextInput"] input:-webkit-autofill:hover,
          div[data-testid="stTextInput"] input:-webkit-autofill:focus,
          div[data-testid="stPassword"] input:-webkit-autofill,
          div[data-testid="stPassword"] input:-webkit-autofill:hover,
          div[data-testid="stPassword"] input:-webkit-autofill:focus{
            -webkit-text-fill-color: #ffffff !important;
            transition: background-color 5000s ease-in-out 0s !important;
            box-shadow: 0 0 0px 1000px rgba(255,255,255,0.10) inset !important;
            border-radius: 12px !important;
          }

          /* SUBIR PDFs – panel ID (reemplaza st.info) */
          .idcard{
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 14px;
            background: rgba(255,255,255,0.06);
            padding: 14px 16px;
            margin: 10px 0 14px 0;
            display:flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
          }
          .idcard .label{
            color: rgba(0, 127, 255);
            font-weight: 800;
            font-size: 16px;
            text-transform: uppercase;
            letter-spacing: .6px;
          }
          .idcard .value{
            color: #007FFF !important;
            -webkit-text-fill-color: #007FFF !important;
            font-weight: 950;
            font-size: 18px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            text-shadow: 0 0 10px rgba(0,120,212,0.45);
          }

          /* FILE UPLOADER – texto claro (agresivo) */
          div[data-testid="stFileUploader"] * {
            color: rgba(255,255,255,0.92) !important;
            -webkit-text-fill-color: rgba(255,255,255,0.92) !important;
            opacity: 1 !important;
          }

          /* =========================================================
             FILE UPLOADER – QUITAR FONDO BLANCO (Streamlit 1.52.2)
             (CORREGIDO: SIN <style> ANIDADO)
             ========================================================= */
          div[data-testid="stFileUploaderDropzone"]{
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 14px !important;
          }

          div[data-testid="stFileUploader"] section{
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 14px !important;
          }

          div[data-testid="stFileUploader"] [data-baseweb="file-uploader"]{
            background: transparent !important;
          }
          div[data-testid="stFileUploader"] [data-baseweb="file-uploader"] > div{
            background: rgba(255,255,255,0.06) !important;
          }

          div[data-testid="stFileUploader"] button{
            background: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.20) !important;
            color: rgba(255,255,255,0.92) !important;
          }

          div[data-testid="stFileUploaderDropzone"]:hover{
            border-color: rgba(0,120,212,0.55) !important;
            background: rgba(0,120,212,0.10) !important;
          }

          /* =========================================================
             SIDEBAR SELECTBOX – NO EDITABLE + CURSOR FIX (Streamlit 1.52.2)
             ========================================================= */
          section[data-testid="stSidebar"] div[data-baseweb="select"] input {
            pointer-events: none !important;
            caret-color: transparent !important;
          }
          section[data-testid="stSidebar"] div[data-baseweb="select"] [role="combobox"]{
            pointer-events: auto !important;
          }

          section[data-testid="stSidebar"] div[data-baseweb="select"],
          section[data-testid="stSidebar"] div[data-baseweb="select"] * {
            cursor: default !important;
          }

          section[data-testid="stSidebar"] div[data-baseweb="select"] input,
          section[data-testid="stSidebar"] div[data-baseweb="select"] input[type="text"],
          section[data-testid="stSidebar"] div[data-baseweb="select"] [contenteditable="true"] {
            cursor: default !important;
            caret-color: transparent !important;
            user-select: none !important;
            pointer-events: none !important;
          }

          section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="combobox"] {
            pointer-events: auto !important;
            cursor: default !important;
          }

          section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="combobox"]:focus,
          section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="combobox"]:focus-within {
            outline: none !important;
            box-shadow: none !important;
          }

          /* =========================
             FOOTER – HECHO CON AMOR
             (NO FIJO: se ve solo al final con scroll)
             ========================= */
          .app-footer{
            margin-top: 48px;
            padding: 18px 0 8px 0;
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            color: rgba(255,255,255,0.55);
            letter-spacing: 0.4px;
          }
          .app-footer span{
            color: rgba(0, 120, 212, 0.85);
            font-weight: 900;
          }
          .app-footer .heart{
            color: #ff4d6d;
            margin: 0 4px;
          }

        </style>
        """,
        unsafe_allow_html=True,
    )

def hide_sidebar():
    st.markdown(
        """
        <style>
          section[data-testid="stSidebar"] { display: none !important; }
          div[data-testid="stSidebarNav"] { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

inject_css()

# --------------------------------------------------
# LOGIN
# --------------------------------------------------
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "usuario": {"password": "user123", "rol": "usuario"},
}

if "login" not in st.session_state:
    st.session_state.login = False

if "rol" not in st.session_state:
    st.session_state.rol = "usuario"

if "excel_ready" not in st.session_state:
    st.session_state.excel_ready = {}

def login():
    hide_sidebar()
    st.markdown('<div class="login-wrap"><div class="card">', unsafe_allow_html=True)

    logo_b64 = img_to_base64(LOGO_PATH) if os.path.exists(LOGO_PATH) else ""
    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">
          {"<img src='data:image/png;base64," + logo_b64 + "' style='width:120px;height:auto;display:block;margin:0 auto 12px auto;' />" if logo_b64 else "<div style='font-size:64px;margin-bottom:8px;'>🦉</div>"}
          <div style="font-size:34px;font-weight:950;margin-bottom:4px;color:rgba(255,255,255,0.92);">{APP_NAME}</div>
          <div style="font-size:15px;color:rgba(255,255,255,0.70);">Dashboard de cargas y extracción de PDFs</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

    cc1, cc2, cc3 = st.columns([1.4, 2.2, 1.4])
    with cc2:
        usuario = st.text_input("Usuario", placeholder="Usuario")
        password = st.text_input("Contraseña", type="password", placeholder="Contraseña")
        ingresar = st.button("Ingresar", use_container_width=True)

    if ingresar:
        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            st.session_state.login = True
            st.session_state.rol = USUARIOS[usuario]["rol"]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

    st.markdown("</div></div>", unsafe_allow_html=True)

if not st.session_state.login:
    login()
    st.stop()

# --------------------------------------------------
# API HELPERS
# --------------------------------------------------
def obtener_id_carga() -> str:
    resp = requests.get(API_ID_CARGA_URL, timeout=HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if "id_carga" not in data or not data["id_carga"]:
        raise Exception(f"Respuesta inválida: {data}")
    return data["id_carga"]

def obtener_cargas_desde_backend():
    resp = requests.get(API_DASHBOARD_CARGAS_URL, timeout=HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()

def retry_carga_backend(id_carga: str):
    url = f"{API_RETRY_URL}/{id_carga}/retry"
    resp = requests.post(url, timeout=HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()

def descargar_excel_backend(id_carga: str) -> bytes:
    url = f"{API_EXCEL_URL}/{id_carga}/excel"
    resp = requests.get(url, timeout=HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    return resp.content

def nombre_unico(nombre: str) -> str:
    base, ext = os.path.splitext(nombre)
    return f"{base}_{uuid.uuid4().hex}{ext}"

def subir_pdf_a_api(file_bytes: bytes, filename: str, id_carga: str):
    files = {"file": (filename, file_bytes, "application/pdf")}
    data = {"id_carga": id_carga}
    resp = requests.post(API_UPLOAD_URL, files=files, data=data, timeout=HTTP_TIMEOUT)
    if resp.status_code not in (200, 201):
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()

def comentario_por_estado(status: str, error_message: Optional[str]) -> str:
    st_norm = (status or "").upper()
    if st_norm == "ERROR":
        msg = (error_message or "").strip()
        return msg if msg else "Error en el procesamiento"
    if st_norm == "UPLOADED":
        return "Archivo cargado. En espera de procesamiento."
    if st_norm == "PROCESSED":
        return "Procesamiento finalizado. Excel disponible."
    return "Estado actualizado."

# --------------------------------------------------
# SIDEBAR + MENU
# --------------------------------------------------
st.sidebar.markdown(f"## {APP_NAME}")
st.sidebar.caption(f"Rol: **{st.session_state.rol}**")

menu = st.sidebar.selectbox(
    "Menú",
    ["Dashboard", "Subir PDFs"] if st.session_state.rol == "admin" else ["Dashboard"],
    index=0,
)

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
if menu == "Dashboard":
    top_left, top_right = st.columns([3.4, 1.4], vertical_alignment="top")

    with top_left:
        st.markdown("## Estado de las cargas")

        c1, c2 = st.columns([1.4, 1.6], vertical_alignment="center")
        with c1:
            refrescar = st.button("Refrescar", use_container_width=True)
        with c2:
            ocultar_ok = st.toggle("Ocultar OK", value=False)

        if refrescar:
            st.rerun()

    with top_right:
        if os.path.exists(LOGO_PATH):
            logo_b64 = img_to_base64(LOGO_PATH)
            st.markdown(
                f"""
                <div class="owl-panel">
                  <img src="data:image/png;base64,{logo_b64}" alt="logo"/>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="owl-panel" style="font-size:64px;">🦉</div>', unsafe_allow_html=True)

    try:
        cargas = obtener_cargas_desde_backend()
    except Exception as e:
        st.error(f"No se pudo consultar el dashboard: {e}")
        st.stop()

    if not cargas:
        st.info("No hay cargas registradas.")
        st.stop()

    rows = []
    for r in cargas:
        id_carga = r.get("id_carga") or ""
        fecha = r.get("updated_at") or r.get("fecha") or ""
        status = (r.get("status") or r.get("estado") or "")
        status_norm = status.upper()
        error_message = r.get("error_message")

        if ocultar_ok and status_norm == "PROCESSED":
            continue

        rows.append({
            "id_carga": id_carga,
            "fecha": fecha,
            "status_norm": status_norm,
            "comentario": comentario_por_estado(status, error_message),
        })

    total = len(rows)
    ok = sum(1 for x in rows if x["status_norm"] == "PROCESSED")
    err = sum(1 for x in rows if x["status_norm"] == "ERROR")
    upl = sum(1 for x in rows if x["status_norm"] == "UPLOADED")

    st.markdown(
        f"""
        <div class="kpi-row">
          <div class="kpi"><div class="k">Total</div><div class="v">{total}</div></div>
          <div class="kpi"><div class="k">Procesados</div><div class="v">{ok}</div></div>
          <div class="kpi"><div class="k">Errores</div><div class="v">{err}</div></div>
          <div class="kpi"><div class="k">Cargados</div><div class="v">{upl}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="grid-wrap">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="grid-head">
          <div>ID Carga</div>
          <div>Fecha</div>
          <div>Estado</div>
          <div>Comentario</div>
          <div style="text-align:center;">Acción</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for x in rows:
        id_carga = x["id_carga"]
        status_norm = x["status_norm"]

        if status_norm == "PROCESSED":
            chip = '<span class="chip chip-ok">✅ Procesado</span>'
        elif status_norm == "UPLOADED":
            chip = '<span class="chip chip-warn">⬆️ Cargado</span>'
        elif status_norm == "ERROR":
            chip = '<span class="chip chip-err">⛔ Error</span>'
        else:
            chip = f'<span class="chip">ℹ️ {status_norm or "DESCONOCIDO"}</span>'

        c_id, c_fecha, c_estado, c_coment, c_accion = st.columns(
            [2.2, 2.4, 1.6, 5.2, 2.3],
            vertical_alignment="center"
        )

        with c_id:
            st.markdown(
                f"""
                <div class="grid-cell grid-mono">
                  <span style="color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; opacity:1 !important;">
                    {id_carga}
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_fecha:
            st.markdown(f'<div class="grid-cell grid-muted">{x["fecha"]}</div>', unsafe_allow_html=True)

        with c_estado:
            st.markdown(f'<div class="grid-cell">{chip}</div>', unsafe_allow_html=True)

        with c_coment:
            st.markdown(f'<div class="grid-cell grid-muted">{x["comentario"]}</div>', unsafe_allow_html=True)

        with c_accion:
            if status_norm == "ERROR" and st.session_state.rol == "admin":
                if st.button("Reintentar", key=f"retry_{id_carga}", use_container_width=True):
                    try:
                        retry_carga_backend(id_carga)
                        st.success(f"Reintento enviado: {id_carga}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo reintentar: {e}")

            elif status_norm == "PROCESSED":
                if id_carga in st.session_state.excel_ready:
                    st.download_button(
                        label="Descargar Excel",
                        data=st.session_state.excel_ready[id_carga],
                        file_name=f"{id_carga}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_{id_carga}",
                        use_container_width=True,
                    )
                else:
                    if st.button("Excel", key=f"excel_{id_carga}", use_container_width=True):
                        try:
                            st.session_state.excel_ready[id_carga] = descargar_excel_backend(id_carga)
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo preparar Excel: {e}")
            else:
                st.caption("—")

        st.markdown(
            "<div style='height:1px; background:rgba(255,255,255,0.06); margin: 0 16px;'></div>",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# SUBIR PDFs (COMPACTO)
# --------------------------------------------------
elif menu == "Subir PDFs":
    st.markdown("## Subir PDFs")

    h1c, h2c = st.columns([3, 1], vertical_alignment="center")

    try:
        id_carga = obtener_id_carga()
    except Exception as e:
        st.error(f"No se pudo generar ID de carga: {e}")
        st.stop()

    st.markdown(
        f"""
        <div class="idcard">
          <div class="label">ID Carga asignado</div>
          <div class="value">{id_carga}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    archivos = st.file_uploader(
        "Selecciona archivos PDF",
        type=["pdf"],
        accept_multiple_files=True,
    )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    iniciar = st.button("Iniciar carga", disabled=not bool(archivos))

    if iniciar and archivos:
        progress = st.progress(0)
        total = len(archivos)
        ok_count = 0
        errores = []

        for i, archivo in enumerate(archivos):
            try:
                if archivo.size == 0:
                    raise Exception("PDF vacío")

                file_bytes = archivo.getbuffer().tobytes()
                nombre_envio = nombre_unico(archivo.name)

                subir_pdf_a_api(file_bytes, nombre_envio, id_carga)
                ok_count += 1

            except Exception as e:
                errores.append(f"{archivo.name}: {str(e)}")

            progress.progress(int(((i + 1) / total) * 100))
            time.sleep(0.02)

        if errores:
            st.error(f"Carga finalizada con errores. OK={ok_count}/{total}")
            st.code("\n".join(errores), language=None)
        else:
            st.success(f"Carga completada correctamente. OK={ok_count}/{total}")

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
st.sidebar.divider()
if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()

# --------------------------------------------------
# FOOTER (SOLO AL FINAL: se ve al hacer scroll)
# --------------------------------------------------
st.markdown(
    """
    <div class="app-footer">
        Hecho con <span class="heart">❤️</span> por <span>Extracta</span>
    </div>
    """,
    unsafe_allow_html=True
)
