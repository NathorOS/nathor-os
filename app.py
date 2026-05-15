import streamlit as st
import pandas as pd
import psycopg2  # CAMBIO: Motor para la nube
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
import os
import warnings

# Limpieza de avisos
warnings.filterwarnings('ignore')

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="NATHOR OS", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# ☁️ CONEXIÓN DEFINITIVA A SUPABASE ☁️
# ==========================================
def conectar_db():
    URI = "postgresql://postgres:40928478niqo@db.spnksfiyyjkcolgsjjim.supabase.co:5432/postgres"
    return psycopg2.connect(URI)

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    # CAMBIO: Usamos SERIAL para que el ID se sume solo en la nube
    cursor.execute('''CREATE TABLE IF NOT EXISTS horno_registros (id SERIAL PRIMARY KEY, fecha_hora TEXT, Z1 REAL, Z2 REAL, Z3 REAL, Z4 REAL, Z5 REAL, Z6 REAL, Z7 REAL, Z8 REAL, Z9 REAL, Z10 REAL, banda REAL, calibre TEXT, operador TEXT, estado TEXT, minutos_estado REAL, observacion TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS set_points (nombre_prueba TEXT PRIMARY KEY, S1 REAL, S2 REAL, S3 REAL, S4 REAL, S5 REAL, S6 REAL, S7 REAL, S8 REAL, S9 REAL, S10 REAL, S_banda REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS balance_masa (id SERIAL PRIMARY KEY, fecha_hora TEXT, lote TEXT, kg_ingresado REAL, kg_blanched REAL, kg_partido REAL, kg_rechazo REAL, operador TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (username TEXT PRIMARY KEY, password TEXT, rol TEXT)''')
    
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES ('admin', 'nathor2026', 'Admin')")
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES ('operador', 'horno123', 'Operador')")
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES ('gerencia', 'olega2026', 'Solo Lectura')")
    conn.commit(); conn.close()

# Ejecutar inicialización
try:
    inicializar_db()
except Exception as e:
    st.error(f"Error de conexión a la nube: {e}")

# --- SISTEMA DE SESIÓN ---
if 'usuario' not in st.session_state: st.session_state['usuario'] = None
if 'rol' not in st.session_state: st.session_state['rol'] = None
if 'menu_actual' not in st.session_state: st.session_state['menu_actual'] = "Dashboard Central"

def login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if os.path.exists("logo_nathor.png"):
            st.image("logo_nathor.png", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #E63946;'>🔒 NATHOR OS</h1>", unsafe_allow_html=True)
        
        with st.form("login_form_unico"):
            user = st.text_input("Usuario (minúsculas)")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                conn = conectar_db(); cursor = conn.cursor()
                # CAMBIO: %s en vez de ?
                cursor.execute("SELECT rol FROM usuarios WHERE username = %s AND password = %s", (user.lower(), password))
                res = cursor.fetchone()
                conn.close()
                if res:
                    st.session_state['usuario'] = user.lower()
                    st.session_state['rol'] = res[0]
                    st.session_state['menu_actual'] = "Dashboard Central"
                    st.rerun()
                else: st.error("Acceso denegado.")

def logout():
    st.session_state['usuario'] = None
    st.session_state['rol'] = None
    st.session_state['menu_actual'] = "Dashboard Central"
    st.rerun()

# --- ESTILOS ---
def aplicar_estilos():
    st.markdown("""
    <style>
        [data-testid="stToolbar"], [data-testid="stHeader"], footer {visibility: hidden !important; display: none !important;}
        .stApp { background-color: #0e1117; }
        .stApp p, .stApp span, .stApp label, .stApp li { color: #c9d1d9 !important; }
        h1, h2, h3, h1 *, h2 *, h3 * { color: #f0f6fc !important; font-weight: 700 !important; }
        [data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="select"] div { background-color: #0d1117 !important; color: #ffffff !important; border-color: #30363d !important; }
        [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d !important; min-width: 280px !important; }
        [data-testid="stSidebar"] div.stButton > button { background-color: transparent !important; color: #8b949e !important; border: none !important; justify-content: flex-start !important; padding: 10px 15px !important; font-size: 15px !important; border-radius: 6px !important; }
        [data-testid="stSidebar"] div.stButton > button:hover { background-color: #21262d !important; color: #ffffff !important; }
        [data-testid="stMainBlockContainer"] div.stButton > button { background-color: #E63946 !important; color: white !important; font-weight: bold !important; width: 100% !important; }
        [data-testid="stMetric"] { background-color: #1c2128 !important; border: 1px solid #30363d !important; border-radius: 12px !important; padding: 15px !important; }
        .user-card { background-color: #0d1117; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES LÓGICA ---
def formatear_duracion(minutos_decimal):
    if minutos_decimal == 0 or pd.isna(minutos_decimal): return "0s"
    mins = int(minutos_decimal); segs = int((minutos_decimal % 1) * 60)
    return f"{mins} min {segs} seg" if mins > 0 else f"{segs} seg"

def calcular_duracion(ahora_str):
    conn = conectar_db(); cursor = conn.cursor()
    cursor.execute("SELECT fecha_hora FROM horno_registros ORDER BY id DESC LIMIT 1")
    ultimo = cursor.fetchone(); conn.close()
    if not ultimo: return 0.0
    fmt = "%Y-%m-%d %H:%M:%S"
    diferencia = datetime.strptime(ahora_str, fmt) - datetime.strptime(ultimo[0], fmt)
    return diferencia.total_seconds() / 60

def obtener_datos_sp(nombre):
    conn = conectar_db(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM set_points WHERE nombre_prueba = %s", (nombre,))
    columnas = [desc[0] for desc in cursor.description]
    fila = cursor.fetchone(); conn.close()
    return pd.Series(dict(zip(columnas, fila))) if fila else None

def obtener_datos_filtrados(f_inicio, f_fin, turno):
    conn = conectar_db(); df = pd.read_sql_query("SELECT * FROM horno_registros ORDER BY id DESC", conn); conn.close()
    if df.empty: return df
    df['fecha_dt'] = pd.to_datetime(df['fecha_hora'])
    mask_fechas = (df['fecha_dt'].dt.date >= f_inicio) & (df['fecha_dt'].dt.date <= f_fin)
    df = df[mask_fechas]
    if turno == "Mañana (06:00 a 14:00)": df = df[(df['fecha_dt'].dt.hour >= 6) & (df['fecha_dt'].dt.hour < 14)]
    return df

# --- INICIO APP ---
aplicar_estilos()

if st.session_state['usuario'] is None:
    login()
else:
    with st.sidebar:
        if os.path.exists("logo_nathor.png"): st.image("logo_nathor.png", use_container_width=True)
        nav_items = [("📊 Dashboard Central", "Dashboard Central")]
        if st.session_state['rol'] in ["Admin", "Operador"]:
            nav_items.append(("📥 Cargar Horno", "Cargar Datos"))
            nav_items.append(("⚖️ Cargar Balance", "Balance de Masa"))
        if st.session_state['rol'] in ["Admin", "Solo Lectura"]:
            nav_items.append(("📋 Auditoría y Excel", "Historial y Auditoría"))
        if st.session_state['rol'] == "Admin":
            nav_items.append(("⚙️ Set Points", "Configurar Set Points"))

        for label, key in nav_items:
            if st.button(label, key=f"nav_{key}"): st.session_state['menu_actual'] = key; st.rerun()

        st.markdown(f'<div class="user-card"><p style="margin:0; font-size:11px; color:#8b949e;">ACTIVO</p><p style="margin:0; font-size:16px; font-weight:bold; color:white;">{st.session_state["usuario"].upper()}</p></div>', unsafe_allow_html=True)
        if st.button("Salir 🚪"): logout()

    menu = st.session_state['menu_actual']
    
    if menu == "Dashboard Central":
        st.title("📊 Control OLEGA")
        conn = conectar_db(); df_ultimo = pd.read_sql_query("SELECT * FROM horno_registros ORDER BY id DESC LIMIT 1", conn); conn.close()
        if not df_ultimo.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Estado", df_ultimo['estado'].values[0])
            c2.metric("Banda", f"{df_ultimo['banda'].values[0]:.2f} m/min")
            c3.metric("Calibre", df_ultimo['calibre'].values[0])
            st.markdown("---")
            cols = st.columns(5)
            for i in range(1, 11):
                cols[(i-1)%5].metric(f"Zona {i}", f"{df_ultimo[f'z{i}'].values[0]:.1f}°")
        else: st.info("Sin datos.")

    elif menu == "Cargar Datos":
        st.header("📥 Cargar Turno")
        conn = conectar_db(); cursor = conn.cursor(); cursor.execute("SELECT nombre_prueba FROM set_points"); opts = [r[0] for r in cursor.fetchall()]; conn.close()
        if not opts: st.warning("Configurá Set Points.")
        else:
            with st.form("carga_form"):
                banda = st.number_input("Banda", 0.70)
                cal = st.selectbox("Calibre", opts)
                pvs = {f"Z{i}": st.number_input(f"Zona {i}", 90.0) for i in range(1, 11)}
                if st.form_submit_button("Guardar"):
                    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn = conectar_db(); cursor = conn.cursor()
                    cursor.execute('INSERT INTO horno_registros (fecha_hora, Z1, Z2, Z3, Z4, Z5, Z6, Z7, Z8, Z9, Z10, banda, calibre, operador, estado, minutos_estado, observacion) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (ahora, *pvs.values(), banda, cal, st.session_state['usuario'], "En Marcha", 60.0, ""))
                    conn.commit(); conn.close(); st.success("Guardado.")

    elif menu == "Configurar Set Points":
        st.header("⚙️ Set Points")
        with st.form("sp_form"):
            nom = st.text_input("Nombre")
            sb = st.number_input("SP Banda", 0.70)
            sps = {f"S{i}": st.number_input(f"SP Z{i}", 95.0) for i in range(1, 11)}
            if st.form_submit_button("Guardar"):
                conn = conectar_db(); cursor = conn.cursor()
                cursor.execute('DELETE FROM set_points WHERE nombre_prueba = %s', (nom,))
                cursor.execute('INSERT INTO set_points VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (nom, *sps.values(), sb))
                conn.commit(); conn.close(); st.success("Actualizado.")