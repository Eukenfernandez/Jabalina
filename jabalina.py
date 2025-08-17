# app.py
# --------------------------------------------------------------
# App básica (Streamlit) para atleta y entrenador de jabalina — DISEÑO MEJORADO (Tema CLARO)
# --------------------------------------------------------------
# - Registro de lanzamientos (distancia, notas, vídeo)
# - Análisis simple de vídeo + extracción de fotogramas
# - Comparación lado a lado de dos vídeos/fotogramas
# - Mejores marcas por temporada y por disciplina (con edición)
#   · Lanzamientos (jabalina) — se cargan desde "Lanzamientos"
#   · Saltos (profundidad, triple, pentasalto)
#   · Pesas (sentadilla, arrancada, cargada, pull over, pectoral, hip thrust)
#   · Velocidad
# - Planificación (calendario simple + objetivos)
# - Rendimiento (gráficas de progresión y carga percibida)
# - Prevención de lesiones (registro de molestias)
# - Recuperación (rutinas y recordatorios manuales)
# - Chat interno atleta↔entrenador
# - Persistencia en SQLite
# --------------------------------------------------------------

import io
import sqlite3
import datetime as dt
from pathlib import Path
import base64

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
import matplotlib.pyplot as plt

# Opcional (para manejar vídeo y fotogramas)
try:
    import cv2  # opencv-python
except Exception:
    cv2 = None

DB_PATH = "training_app.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ---------------------------- ESTILO / THEME ---------------------------- #

st.set_page_config(page_title="Jabalina Coach", page_icon="🏹", layout="wide")

CUSTOM_CSS = """
<style>
/***** Tipografía y colores base (Tema CLARO) *****/
:root {
  --bg: #ffffff;        /* fondo blanco */
  --panel: #f7f9fc;     /* tarjetas claras */
  --panel-2: #eef4ff;   /* panel alterno suave */
  --text: #0b1220;      /* texto principal oscuro */
  --muted: #475569;     /* texto secundario */
  --brand: #1d4ed8;     /* azul */
  --accent: #16a34a;    /* verde */
  --warn: #d97706;      /* ámbar */
  --danger: #dc2626;    /* rojo */
}

html, body, [class^=block-container] { background: var(--bg) !important; color: var(--text) !important; }

/***** Títulos *****/
h1, h2, h3, h4 { color: var(--text) !important; line-height: 1.25; }
h1 { font-size: 2.1rem !important; font-weight: 800 !important; letter-spacing: .2px; }
h2 { font-size: 1.6rem !important; font-weight: 700 !important; }
h3 { font-size: 1.25rem !important; font-weight: 700 !important; }

/* Separadores */
hr { border: none; height: 1px; background: #e5e7eb; margin: 8px 0 16px; }

/***** Paneles y tarjetas *****/
.card {
  background: linear-gradient(180deg, var(--panel), var(--panel-2));
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 18px 18px;
  box-shadow: 0 8px 22px rgba(2,6,23,0.06);
}
.card h3 { margin: 0 0 8px 0; font-size: 1.08rem; color: var(--text); font-weight: 700; }
.card .value { font-size: 1.85rem; font-weight: 800; letter-spacing: .2px; color: var(--text); }
.card .sub { font-size: .95rem; color: var(--muted); }

/***** DataFrame / tablas *****/
div[data-testid="stDataFrame"] { border: 1px solid #e5e7eb; border-radius: 12px; }
div[data-testid="stDataFrame"] thead tr th { background: #f3f6fb !important; color: #0b1220 !important; }

/***** Sidebar *****/
section[data-testid="stSidebar"] { background: #f8fafc; border-right: 1px solid #e2e8f0; }
section[data-testid="stSidebar"] * { color: var(--text) !important; }

/***** Inputs *****/
input, textarea, select, .stTextInput > div > div > input { color: var(--text) !important; background: #ffffff !important; }
label, .stMarkdown p { color: var(--text) !important; }
small, .markdown-text-container span { color: var(--muted) !important; }

/***** Links *****/
a, .stMarkdown a { color: var(--brand) !important; text-decoration: none; }
a:hover { text-decoration: underline; }

/***** Alerts / mensajes *****/
.stAlert { color: var(--text) !important; }

/***** Ocultar marcas Streamlit *****/
footer, #MainMenu { visibility: hidden; }

/* ====== FIX: encabezados de días en calendarios (evita traducciones raras como "Nosotros") ====== */
/* React-Day-Picker v8 usa clases rdp-*. Forzamos etiquetas en ES */
.stDateInput .rdp-head_cell{color:transparent !important;position:relative;font-weight:700;}
.stDateInput .rdp-head_cell:nth-child(1)::after{content:"Lu";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput .rdp-head_cell:nth-child(2)::after{content:"Ma";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput .rdp-head_cell:nth-child(3)::after{content:"Mi";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput .rdp-head_cell:nth-child(4)::after{content:"Ju";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput .rdp-head_cell:nth-child(5)::after{content:"Vi";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput .rdp-head_cell:nth-child(6)::after{content:"Sá";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput .rdp-head_cell:nth-child(7)::after{content:"Do";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}

/* Fallback para algunas versiones que no exponen rdp-head_cell */
.stDateInput thead th[scope="col"]{color:transparent !important;position:relative;font-weight:700;}
.stDateInput thead th[scope="col"]:nth-child(1)::after{content:"Lu";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput thead th[scope="col"]:nth-child(2)::after{content:"Ma";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput thead th[scope="col"]:nth-child(3)::after{content:"Mi";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput thead th[scope="col"]:nth-child(4)::after{content:"Ju";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput thead th[scope="col"]:nth-child(5)::after{content:"Vi";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput thead th[scope="col"]:nth-child(6)::after{content:"Sá";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.stDateInput thead th[scope="col"]:nth-child(7)::after{content:"Do";color:var(--text);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}

</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Helpers UI

def metric_card(title: str, value: str, sub: str = ""):
    st.markdown(
        f"""
        <div class='card'>
          <h3>{title}</h3>
          <div class='value'>{value}</div>
          <div class='sub'>{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------- DB UTILS ---------------------------- #

SCHEMA = {
    "throws": (
        """
        CREATE TABLE IF NOT EXISTS throws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            session TEXT,
            distance REAL,
            est_speed REAL, -- mantenida por compatibilidad, no usada en la UI
            notes TEXT,
            video_path TEXT
        )
        """
    ),
    "fatigue": (
        """
        CREATE TABLE IF NOT EXISTS fatigue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            rpe INTEGER,   -- 1-10
            sleep_hours REAL,
            soreness INTEGER, -- 0-10
            notes TEXT
        )
        """
    ),
    "gym_logs": (
        """
        CREATE TABLE IF NOT EXISTS gym_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            exercise TEXT,
            weight REAL,
            reps INTEGER,
            velocity REAL,
            notes TEXT
        )
        """
    ),
    "injuries": (
        """
        CREATE TABLE IF NOT EXISTS injuries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            area TEXT,
            pain_level INTEGER, -- 0-10
            description TEXT,
            action TEXT
        )
        """
    ),
    "plans": (
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            title TEXT,
            details TEXT
        )
        """
    ),
    "goals": (
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT,
            end_date TEXT,
            title TEXT,
            metric TEXT,
            target REAL,
            notes TEXT
        )
        """
    ),
    "chat": (
        """
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            sender TEXT,
            message TEXT
        )
        """
    ),
    # NUEVA tabla genérica para mejores marcas de disciplinas que NO son jabalina
    "best_marks": (
        """
        CREATE TABLE IF NOT EXISTS best_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            season INTEGER,
            grp TEXT,           -- 'saltos' | 'pesas' | 'velocidad'
            discipline TEXT,    -- p.ej. 'salto profundidad', 'triple', 'sentadilla', etc.
            value REAL,
            unit TEXT,          -- m, cm, kg, s, etc.
            notes TEXT
        )
        """
    )
}


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with get_conn() as con:
        cur = con.cursor()
        for sql in SCHEMA.values():
            cur.execute(sql)
        con.commit()


# ---------------------------- HELPERS ---------------------------- #

def ensure_table(table: str):
    """Crea la tabla si no existe usando el SQL del SCHEMA."""
    sql = SCHEMA.get(table)
    if sql:
        with get_conn() as con:
            con.execute(sql)
            con.commit()

@st.cache_data(show_spinner=False)
def load_table(table: str) -> pd.DataFrame:
    # Garantiza que la tabla exista antes de leer
    ensure_table(table)
    with get_conn() as con:
        try:
            return pd.read_sql_query(f"SELECT * FROM {table} ORDER BY id DESC", con)
        except Exception as e:
            # Si (por ejemplo en despliegues antiguos) aún no existe, devuelve vacío
            if "no such table" in str(e).lower():
                return pd.DataFrame()
            raise


def insert_row(table: str, data: dict):
    keys = ",".join(data.keys())
    placeholders = ",".join([":" + k for k in data.keys()])
    with get_conn() as con:
        con.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", data)
        con.commit()


def update_row(table: str, row_id: int, data: dict):
    set_clause = ",".join([f"{k} = :{k}" for k in data.keys()])
    data_with_id = {**data, "_id": row_id}
    with get_conn() as con:
        con.execute(f"UPDATE {table} SET {set_clause} WHERE id = :_id", data_with_id)
        con.commit()


def delete_row(table: str, row_id: int):
    with get_conn() as con:
        con.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        con.commit()


def save_upload(file, subdir: str) -> Path:
    folder = UPLOAD_DIR / subdir
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.name}"
    out = folder / safe_name
    with open(out, "wb") as f:
        f.write(file.getbuffer())
    return out


# -------- Video utilities -------- #

def extract_frame(video_path: str | Path, frame_index: int) -> Image.Image | None:
    if cv2 is None:
        return None
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total == 0:
        cap.release()
        return None
    frame_index = int(np.clip(frame_index, 0, total - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return None
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(frame)


def video_frame_count(video_path: str | Path) -> int:
    if cv2 is None:
        return 0
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return total


# ---------------------------- NAV / SIDEBAR ---------------------------- #

init_db()

# --- NUEVO: selector de atleta + tipo de prueba ---
ATHLETES = {
    "Eneko": "peso",
    "Iker": "peso",
    "Lizeta": "peso",
    "Maddi": "peso",
    "Paul": "jabalina",
    "Alaitz": "peso",
    "Euken": "jabalina",
    "Mikel": "jabalina",
}

st.sidebar.title("🏹 Jabalina Coach")

atleta = st.sidebar.selectbox("Atleta", list(ATHLETES.keys()), key="athlete_select")
athlete_event = ATHLETES[atleta]  # 'jabalina' o 'peso'
st.sidebar.caption(f"Disciplina principal: **{athlete_event.capitalize()}**")

section = st.sidebar.radio(
    "Navegación",
    [
        "🏠 Lanzamientos",
        "🆚 Comparación",
        "🏆 Mejores marcas",
        "📝 Entrenamientos",   # ← añadida
        "📈 Rendimiento",
        "🗓️ Planificación",
        "🩹 Lesiones",
        "🧊 Recuperación",
        "💬 Chat",
        "⚙️ Ajustes",
    ],
)
st.sidebar.caption("MVP — Streamlit + SQLite")

# Normalizar sección (quita el emoji)
section_key = section.split(" ", 1)[1]

# --- NUEVO: migración segura de columnas para soportar multi-atleta ---
def ensure_columns():
    with get_conn() as con:
        cur = con.cursor()
        # throws: añadir athlete, event
        cur.execute("PRAGMA table_info(throws)")
        tcols = [r[1] for r in cur.fetchall()]
        if "athlete" not in tcols:
            cur.execute("ALTER TABLE throws ADD COLUMN athlete TEXT")
        if "event" not in tcols:
            cur.execute("ALTER TABLE throws ADD COLUMN event TEXT")

        # best_marks: añadir athlete
        cur.execute("PRAGMA table_info(best_marks)")
        bcols = [r[1] for r in cur.fetchall()]
        if "athlete" not in bcols:
            cur.execute("ALTER TABLE best_marks ADD COLUMN athlete TEXT")

        # NUEVO → fatigue: añadir athlete
        cur.execute("PRAGMA table_info(fatigue)")
        fcols = [r[1] for r in cur.fetchall()]
        if "athlete" not in fcols:
            cur.execute("ALTER TABLE fatigue ADD COLUMN athlete TEXT")

        # NUEVO → gym_logs: añadir athlete
        cur.execute("PRAGMA table_info(gym_logs)")
        gcols = [r[1] for r in cur.fetchall()]
        if "athlete" not in gcols:
            cur.execute("ALTER TABLE gym_logs ADD COLUMN athlete TEXT")

        con.commit()

ensure_columns()

# ---------------------------- Lanzamientos ---------------------------- #

if section_key == "Lanzamientos":
    st.markdown("## Registro de lanzamientos")

    # Nota: si el atleta es de peso, ocultamos 'Sesión/lugar'
    is_javelin = (athlete_event == "jabalina")

    tab1, tab2 = st.tabs(["✍️ Registrar", "🗂️ Histórico & Vídeo"])

    with tab1:
        with st.container():
            c1, c2, c3 = st.columns([1,1,1])
            date = c1.date_input("Fecha", value=dt.date.today())
            session = c2.text_input("Sesión / lugar", placeholder="Pista, playa, etc.") if is_javelin else ""
            distance = c3.number_input("Distancia (m)", min_value=0.0, step=0.1)
            notes = st.text_area("Notas técnicas")
            video = st.file_uploader("Sube vídeo (opcional)", type=["mp4", "mov", "m4v", "avi"], accept_multiple_files=False)
            if st.button("Guardar lanzamiento", use_container_width=True):
                video_path = None
                if video is not None:
                    video_path = str(save_upload(video, "videos"))
                insert_row(
                    "throws",
                    {
                        "date": str(date),
                        "session": session,
                        "distance": float(distance) if distance else None,
                        "notes": notes,
                        "video_path": video_path,
                        # NUEVO: guardar atleta y tipo de prueba
                        "athlete": atleta,
                        "event": athlete_event,  # 'jabalina' o 'peso'
                        "est_speed": None,  # compatibilidad
                    },
                )
                st.success("Lanzamiento guardado ✅")
                st.cache_data.clear()

    with tab2:
        # Filtrar por atleta seleccionado
        df_all = load_table("throws")
        if len(df_all) > 0 and "athlete" in df_all.columns:
            df = df_all[df_all["athlete"] == atleta].copy()
        else:
            df = df_all.copy()

        if len(df) == 0:
            st.info("Aún no hay lanzamientos registrados para este atleta.")
        else:
            cA, cB = st.columns([2, 1])
            with cA:
                st.markdown("#### Historial")
                show_cols = ["id", "date", "distance", "notes", "session", "video_path", "event", "athlete"]
                show_cols = [c for c in show_cols if c in df.columns]
                st.dataframe(df[show_cols], use_container_width=True)

                with st.expander("Borrar lanzamiento por ID"):
                    rid = st.number_input(
                        "ID a borrar",
                        min_value=int(df["id"].min()),
                        max_value=int(df["id"].max()),
                        step=1,
                        key="throw_del_by_id",
                    )
                    if st.button("Eliminar lanzamiento", key="del_throw_btn"):
                        delete_row("throws", int(rid))
                        st.success("Lanzamiento eliminado ✅")
                        st.cache_data.clear()

            with cB:
                st.markdown("#### Revisión de vídeo")
                ids = df["id"].tolist()
                selected_id = st.selectbox(
                    "Selecciona registro",
                    ids,
                    format_func=lambda i: f"#{i} — {df[df.id==i]['date'].iloc[0]} ({df[df.id==i]['distance'].iloc[0]} m)",
                )
                row = df[df.id == selected_id].iloc[0]
                if pd.notna(row.get("video_path")) and str(row["video_path"]).strip():
                    st.video(row["video_path"])
                    if cv2 is None:
                        st.info("Para extraer fotogramas: pip install opencv-python")
                    else:
                        total = video_frame_count(row["video_path"]) or 1
                        idx = st.slider("Fotograma", 0, max(0, total - 1), 0)
                        frame = extract_frame(row["video_path"], idx)
                        if frame is not None:
                            st.image(frame, caption=f"Frame {idx}")
                            buf = io.BytesIO()
                            frame.save(buf, format="PNG")
                            st.download_button(
                                "Descargar fotograma",
                                data=buf.getvalue(),
                                file_name=f"frame_{selected_id}_{idx}.png",
                                mime="image/png",
                                use_container_width=True,
                            )
                    if st.button("Eliminar registro seleccionado", key="del_selected_throw"):
                        delete_row("throws", int(selected_id))
                        st.success("Registro eliminado ✅")
                        st.cache_data.clear()
                else:
                    st.warning("Este registro no tiene vídeo adjunto.")


# ---------------------------- Comparación ---------------------------- #

elif section_key == "Comparación":
    st.markdown("## 🎥 Comparación lado a lado")

    # Cargamos lanzamientos ya guardados
    df = load_table("throws")

    # Filtrar SIEMPRE por atleta y por tipo de prueba para no mezclar datos
    if len(df) > 0:
        if "athlete" in df.columns:
            df = df[df["athlete"] == atleta]
        if "event" in df.columns:
            df = df[df["event"] == athlete_event]

    # Filtro: sólo los que tienen video_path válido
    vids_df = pd.DataFrame()
    if len(df) > 0 and "video_path" in df.columns:
        vids_df = df[df["video_path"].astype(str).str.strip() != ""].copy()
        vids_df = vids_df.dropna(subset=["video_path"])

    # Helper para renderizar video pequeño con <video width="...">
    def render_small_video_from_bytes(video_bytes: bytes, width: int = 360):
        import base64 as _b64
        html = f"""
        <video width="{width}" controls>
            <source src="data:video/mp4;base64,{_b64.b64encode(video_bytes).decode()}">
            Tu navegador no soporta el video.
        </video>
        """
        st.markdown(html, unsafe_allow_html=True)

    def render_small_video_from_path(path: str, width: int = 360):
        try:
            with open(path, "rb") as f:
                video_bytes = f.read()
            render_small_video_from_bytes(video_bytes, width=width)
        except Exception:
            # Fallback a st.video si no podemos leer el archivo
            st.video(path)

    c1, c2 = st.columns(2)

    # -------------------- LADO A --------------------
    with c1:
        st.markdown("#### Lado A")
        srcA = st.radio("Fuente A", ["Guardado", "Subir archivo"], horizontal=True, key="srcA")

        if srcA == "Guardado":
            if len(vids_df) == 0:
                st.info("No hay vídeos guardados aún para este atleta.")
            else:
                idA = st.selectbox(
                    "Selecciona lanzamiento (A)",
                    vids_df["id"].tolist(),
                    format_func=lambda i: f"#{i} — {vids_df[vids_df.id==i]['date'].iloc[0]} ({vids_df[vids_df.id==i]['distance'].iloc[0]} m)",
                    key="selA",
                )
                rA = vids_df[vids_df.id == idA].iloc[0]
                pathA = str(rA["video_path"])
                render_small_video_from_path(pathA, width=360)

                if cv2 is not None:
                    totalA = video_frame_count(pathA) or 1
                    idxA = st.slider("Frame A", 0, max(0, totalA - 1), 0, key="frameA")
                    fA = extract_frame(pathA, idxA)
                    if fA is not None:
                        st.image(fA, caption=f"A — Frame {idxA}")
        else:
            v1 = st.file_uploader("Sube vídeo (A)", type=["mp4", "mov", "avi", "m4v"], key="compA_upload")
            if v1 is not None:
                video_bytes = v1.read()
                render_small_video_from_bytes(video_bytes, width=360)

    # -------------------- LADO B --------------------
    with c2:
        st.markdown("#### Lado B")
        srcB = st.radio("Fuente B", ["Guardado", "Subir archivo"], horizontal=True, key="srcB")

        if srcB == "Guardado":
            if len(vids_df) == 0:
                st.info("No hay vídeos guardados aún para este atleta.")
            else:
                # Intentar elegir un segundo distinto si existe
                default_id = None
                if len(vids_df) >= 2:
                    selA_val = st.session_state.get("selA")
                    idsB = [int(x) for x in vids_df["id"].tolist() if x != selA_val]
                    default_id = idsB[0] if idsB else vids_df["id"].tolist()[0]

                optsB = vids_df["id"].tolist()
                idx_default = optsB.index(default_id) if (default_id in optsB) else 0

                idB = st.selectbox(
                    "Selecciona lanzamiento (B)",
                    optsB,
                    index=idx_default,
                    format_func=lambda i: f"#{i} — {vids_df[vids_df.id==i]['date'].iloc[0]} ({vids_df[vids_df.id==i]['distance'].iloc[0]} m)",
                    key="selB",
                )
                rB = vids_df[vids_df.id == idB].iloc[0]
                pathB = str(rB["video_path"])
                render_small_video_from_path(pathB, width=360)

                if cv2 is not None:
                    totalB = video_frame_count(pathB) or 1
                    idxB = st.slider("Frame B", 0, max(0, totalB - 1), 0, key="frameB")
                    fB = extract_frame(pathB, idxB)
                    if fB is not None:
                        st.image(fB, caption=f"B — Frame {idxB}")
        else:
            v2 = st.file_uploader("Sube vídeo (B)", type=["mp4", "mov", "avi", "m4v"], key="compB_upload")
            if v2 is not None:
                video_bytes = v2.read()
                render_small_video_from_bytes(video_bytes, width=360)

    st.caption("Tip: usa el mismo índice de frame en A y B para comparar posturas clave (solo vídeos guardados).")


elif section_key == "Mejores marcas":
    st.markdown("## 🏆 Mejores marcas por temporada y disciplina")

    # Cargar datos base, SIEMPRE filtrados por atleta
    df_throws = load_table("throws")
    df_best = load_table("best_marks")

    if len(df_throws) > 0 and "athlete" in df_throws.columns:
        df_throws = df_throws[df_throws["athlete"] == atleta].copy()
    if len(df_best) > 0 and "athlete" in df_best.columns:
        df_best = df_best[df_best["athlete"] == atleta].copy()

    # Añadir columna season para throws
    if len(df_throws) > 0 and "date" in df_throws.columns:
        df_throws["season"] = pd.to_datetime(df_throws["date"], errors="coerce").dt.year

    # Filtrar throws por el evento del atleta (jabalina o peso)
    is_javelin = (athlete_event == "jabalina")
    if len(df_throws) > 0 and "event" in df_throws.columns:
        df_throws_evt = df_throws[df_throws["event"] == athlete_event].copy()
    else:
        df_throws_evt = df_throws.copy()

    # Temporadas detectadas (unión de throws filtrados por evento y best_marks)
    seasons = set()
    if len(df_throws_evt) > 0 and "season" in df_throws_evt.columns:
        seasons.update(df_throws_evt["season"].dropna().unique().tolist())
    if len(df_best) > 0 and "season" in df_best.columns:
        seasons.update(df_best["season"].dropna().unique().tolist())
    seasons = sorted([int(s) for s in seasons], reverse=True)

    # Título dinámico del primer tab según el evento del atleta
    first_tab_title = f"🏹 Lanzamientos ({'jabalina' if is_javelin else 'peso'})"
    tabs = st.tabs([first_tab_title, "🦘 Saltos", "🏋️ Pesas", "⚡ Velocidad"])

    # ---------------- Lanzamientos (jabalina o peso, según atleta) ---------------- #
    with tabs[0]:
        st.markdown(f"### Ranking de mejores lanzamientos — {('Jabalina' if is_javelin else 'Peso')}")

        if len(seasons) == 0:
            st.info("No hay datos registrados.")
        else:
            selected_season = st.selectbox("Temporada", seasons, key="season_launch_evt")

            # Filtramos la temporada seleccionada
            if "season" in df_throws_evt.columns:
                jdf = df_throws_evt[df_throws_evt["season"] == selected_season].copy()
            else:
                jdf = df_throws_evt.copy()

            if len(jdf) == 0 or "distance" not in jdf.columns:
                st.info(f"Sin datos de {('jabalina' if is_javelin else 'peso')} para esa temporada.")
            else:
                # Ordenar por distancia descendente (ranking)
                jdf = jdf.dropna(subset=["distance"]).sort_values("distance", ascending=False)

                # Construir tabla a mostrar
                base_cols = ["date", "distance", "notes"]
                # El lugar/sesión SOLO es relevante para jabalina (requisito del usuario)
                if is_javelin and "session" in jdf.columns:
                    show_cols = ["date", "session", "distance", "notes"]
                else:
                    show_cols = [c for c in base_cols if c in jdf.columns]

                jdf_rank = jdf[show_cols].reset_index(drop=True)
                st.dataframe(jdf_rank, use_container_width=True)

                # Métrica de temporada
                if not jdf["distance"].dropna().empty:
                    best = jdf["distance"].max()
                    fecha_best = jdf.loc[jdf["distance"].idxmax(), "date"]
                    metric_card(
                        f"Mejor {('jabalina' if is_javelin else 'peso')}",
                        f"{best:.2f} m",
                        f"Fecha: {fecha_best}"
                    )

    # ---------------- Saltos (CRUD sobre best_marks) ---------------- #
    with tabs[1]:
        st.markdown("### Ranking de saltos")
        SALTOS = [
            ("salto profundidad", "cm"),
            ("triple", "m"),
            ("pentasalto", "m"),
        ]
        csel1, csel2 = st.columns(2)
        disciplina_salto = csel1.selectbox("Disciplina", [d for d, _ in SALTOS])
        unidad_salto = dict(SALTOS)[disciplina_salto]
        temporada_salto = csel2.number_input("Temporada (año)", min_value=2000, max_value=2100, value=dt.date.today().year)

        # Form para añadir/editar
        with st.form("form_saltos"):
            c1, c2, c3 = st.columns(3)
            date = c1.date_input("Fecha", value=dt.date.today(), key="saltos_date")
            value = c2.number_input(f"Marca ({unidad_salto})", min_value=0.0, step=0.01, key="saltos_val")
            notes = c3.text_input("Notas", key="saltos_notes")
            add = st.form_submit_button("Añadir marca")
        if add:
            insert_row("best_marks", {
                "date": str(date),
                "season": int(temporada_salto),
                "grp": "saltos",
                "discipline": disciplina_salto,
                "value": float(value),
                "unit": unidad_salto,
                "notes": notes,
                "athlete": atleta,  # ← no mezclar atletas
            })
            st.success("Marca añadida ✅")
            st.cache_data.clear()

        # Tabla + edición/eliminación
        saltos_df = df_best[
            (df_best["grp"]=="saltos") &
            (df_best["discipline"]==disciplina_salto) &
            (df_best["season"]==int(temporada_salto))
        ].copy()
        saltos_df = saltos_df.sort_values("value", ascending=False)
        st.dataframe(saltos_df, use_container_width=True)

        if len(saltos_df) > 0:
            st.markdown("#### Editar / borrar")
            rid = st.selectbox("ID a editar/borrar", saltos_df["id"].tolist(), key="saltos_edit_id")
            row = saltos_df[saltos_df["id"]==rid].iloc[0]
            with st.form("edit_saltos"):
                c1, c2, c3 = st.columns(3)
                e_date = c1.date_input("Fecha", value=pd.to_datetime(row["date"]).date(), key="saltos_e_date")
                e_value = c2.number_input(f"Marca ({row['unit']})", value=float(row["value"]), min_value=0.0, step=0.01, key="saltos_e_val")
                e_notes = c3.text_input("Notas", value=row.get("notes",""), key="saltos_e_notes")
                cc1, cc2 = st.columns(2)
                ok_update = cc1.form_submit_button("Guardar cambios")
                ok_del = cc2.form_submit_button("Eliminar", type="secondary")
            if ok_update:
                update_row("best_marks", int(rid), {
                    "date": str(e_date),
                    "value": float(e_value),
                    "notes": e_notes,
                })
                st.success("Marca actualizada ✅")
                st.cache_data.clear()
            if ok_del:
                delete_row("best_marks", int(rid))
                st.success("Marca eliminada ✅")
                st.cache_data.clear()

    # ---------------- Pesas (CRUD) ---------------- #
    with tabs[2]:
        st.markdown("### Ranking de pesas")
        PESAS = [
            ("sentadilla", "kg"),
            ("arrancada", "kg"),
            ("cargada", "kg"),
            ("pull over", "kg"),
            ("pectoral", "kg"),
            ("hip thrust", "kg"),
        ]
        csel1, csel2 = st.columns(2)
        disciplina_pesa = csel1.selectbox("Ejercicio", [d for d, _ in PESAS])
        unidad_pesa = dict(PESAS)[disciplina_pesa]
        temporada_pesa = csel2.number_input("Temporada (año)", min_value=2000, max_value=2100, value=dt.date.today().year, key="pesa_temp")

        with st.form("form_pesas"):
            c1, c2, c3 = st.columns(3)
            date = c1.date_input("Fecha", value=dt.date.today(), key="pesas_date")
            value = c2.number_input(f"Marca ({unidad_pesa})", min_value=0.0, step=0.5, key="pesas_val")
            notes = c3.text_input("Notas", key="pesas_notes")
            add = st.form_submit_button("Añadir marca")
        if add:
            insert_row("best_marks", {
                "date": str(date),
                "season": int(temporada_pesa),
                "grp": "pesas",
                "discipline": disciplina_pesa,
                "value": float(value),
                "unit": unidad_pesa,
                "notes": notes,
                "athlete": atleta,  # ← no mezclar atletas
            })
            st.success("Marca añadida ✅")
            st.cache_data.clear()

        pesas_df = df_best[
            (df_best["grp"]=="pesas") &
            (df_best["discipline"]==disciplina_pesa) &
            (df_best["season"]==int(temporada_pesa))
        ].copy()
        pesas_df = pesas_df.sort_values("value", ascending=False)
        st.dataframe(pesas_df, use_container_width=True)

        if len(pesas_df) > 0:
            st.markdown("#### Editar / borrar")
            rid = st.selectbox("ID a editar/borrar", pesas_df["id"].tolist(), key="pesas_edit_id")
            row = pesas_df[pesas_df["id"]==rid].iloc[0]
            with st.form("edit_pesas"):
                c1, c2, c3 = st.columns(3)
                e_date = c1.date_input("Fecha", value=pd.to_datetime(row["date"]).date(), key="pesas_e_date")
                e_value = c2.number_input(f"Marca ({row['unit']})", value=float(row["value"]), min_value=0.0, step=0.5, key="pesas_e_val")
                e_notes = c3.text_input("Notas", value=row.get("notes",""), key="pesas_e_notes")
                cc1, cc2 = st.columns(2)
                ok_update = cc1.form_submit_button("Guardar cambios")
                ok_del = cc2.form_submit_button("Eliminar", type="secondary")
            if ok_update:
                update_row("best_marks", int(rid), {
                    "date": str(e_date),
                    "value": float(e_value),
                    "notes": e_notes,
                })
                st.success("Marca actualizada ✅")
                st.cache_data.clear()
            if ok_del:
                delete_row("best_marks", int(rid))
                st.success("Marca eliminada ✅")
                st.cache_data.clear()

    # ---------------- Velocidad (CRUD) ---------------- #
    with tabs[3]:
        st.markdown("### Ranking de velocidad")
        VELOCIDADES = [
            ("30 m", "s"),
            ("60 m", "s"),
            ("100 m", "s"),
            ("150 m", "s"),
            ("200 m", "s"),
        ]
        csel1, csel2 = st.columns(2)
        disciplina_vel = csel1.selectbox("Prueba", [d for d, _ in VELOCIDADES])
        unidad_vel = dict(VELOCIDADES)[disciplina_vel]
        temporada_vel = csel2.number_input("Temporada (año)", min_value=2000, max_value=2100, value=dt.date.today().year, key="vel_temp")

        with st.form("form_vel"):
            c1, c2, c3 = st.columns(3)
            date = c1.date_input("Fecha", value=dt.date.today(), key="vel_date")
            value = c2.number_input(f"Marca ({unidad_vel})", min_value=0.0, step=0.01, key="vel_val")
            notes = c3.text_input("Notas", key="vel_notes")
            add = st.form_submit_button("Añadir marca")
        if add:
            insert_row("best_marks", {
                "date": str(date),
                "season": int(temporada_vel),
                "grp": "velocidad",
                "discipline": disciplina_vel,
                "value": float(value),
                "unit": unidad_vel,
                "notes": notes,
                "athlete": atleta,  # ← no mezclar atletas
            })
            st.success("Marca añadida ✅")
            st.cache_data.clear()

        # En velocidad, menor tiempo es mejor → ordenar ascendente
        vel_df = df_best[
            (df_best["grp"]=="velocidad") &
            (df_best["discipline"]==disciplina_vel) &
            (df_best["season"]==int(temporada_vel))
        ].copy()
        vel_df = vel_df.sort_values("value", ascending=True)
        st.dataframe(vel_df, use_container_width=True)

        if len(vel_df) > 0:
            st.markdown("#### Editar / borrar")
            rid = st.selectbox("ID a editar/borrar", vel_df["id"].tolist(), key="vel_edit_id")
            row = vel_df[vel_df["id"]==rid].iloc[0]
            with st.form("edit_vel"):
                c1, c2, c3 = st.columns(3)
                e_date = c1.date_input("Fecha", value=pd.to_datetime(row["date"]).date(), key="vel_e_date")
                e_value = c2.number_input(f"Marca ({row['unit']})", value=float(row["value"]), min_value=0.0, step=0.01, key="vel_e_val")
                e_notes = c3.text_input("Notas", value=row.get("notes",""), key="vel_e_notes")
                cc1, cc2 = st.columns(2)
                ok_update = cc1.form_submit_button("Guardar cambios")
                ok_del = cc2.form_submit_button("Eliminar", type="secondary")
            if ok_update:
                update_row("best_marks", int(rid), {
                    "date": str(e_date),
                    "value": float(e_value),
                    "notes": e_notes,
                })
                st.success("Marca actualizada ✅")
                st.cache_data.clear()
            if ok_del:
                delete_row("best_marks", int(rid))
                st.success("Marca eliminada ✅")
                st.cache_data.clear()


# ---------------------------- Entrenamientos ---------------------------- #
elif section_key == "Entrenamientos":
    st.markdown("## 📝 Entrenamientos")

    # Garantiza que exista la tabla 'trainings' (por si es la 1ª vez)
    with get_conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS trainings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                block TEXT,
                exercise TEXT,
                sets TEXT,
                reps TEXT,
                load TEXT,
                rest TEXT,
                notes TEXT
            )
            """
        )
        con.commit()

    st.markdown(
        "Sube un archivo de **Excel/CSV** para importarlo a la base de datos o un **PDF** para archivarlo."
    )

    up = st.file_uploader(
        "Selecciona un archivo (.xlsx, .xls, .csv o .pdf)",
        type=["xlsx", "xls", "csv", "pdf"],
        key="tr_upload_min",
    )

    if up is not None:
        filename = up.name.lower()

        # PDF → solo guardar en disco (no se importa a BD)
        if filename.endswith(".pdf"):
            saved_path = save_upload(up, "trainings")
            st.success(f"PDF guardado en: {saved_path}")
            st.info("El PDF queda almacenado en 'uploads/trainings'. No se importan filas a la base de datos.")

        # Excel/CSV → importar filas a la tabla 'trainings'
        else:
            try:
                if filename.endswith(".csv"):
                    df_new = pd.read_csv(up)
                else:
                    df_new = pd.read_excel(up)
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
                df_new = None

            if df_new is not None and not df_new.empty:
                # Normaliza nombres de columnas (si están en español)
                colmap = {
                    "fecha": "date",
                    "bloque": "block",
                    "ejercicio": "exercise",
                    "series": "sets",
                    "reps": "reps",
                    "carga": "load",
                    "descanso": "rest",
                    "notas": "notes",
                }
                df_norm = df_new.rename(
                    columns={k: v for k, v in colmap.items() if k in df_new.columns}
                )

                # Asegura columnas requeridas
                required = ["date", "block", "exercise", "sets", "reps", "load", "rest", "notes"]
                for col in required:
                    if col not in df_norm.columns:
                        df_norm[col] = None

                # Inserta fila a fila
                insertados = 0
                for _, r in df_norm.iterrows():
                    insert_row(
                        "trainings",
                        {
                            "date": str(r["date"]) if pd.notna(r["date"]) else None,
                            "block": str(r["block"]) if pd.notna(r["block"]) else None,
                            "exercise": str(r["exercise"]) if pd.notna(r["exercise"]) else None,
                            "sets": str(r["sets"]) if pd.notna(r["sets"]) else None,
                            "reps": str(r["reps"]) if pd.notna(r["reps"]) else None,
                            "load": str(r["load"]) if pd.notna(r["load"]) else None,
                            "rest": str(r["rest"]) if pd.notna(r["rest"]) else None,
                            "notes": str(r["notes"]) if pd.notna(r["notes"]) else None,
                        },
                    )
                    insertados += 1

                st.success(f"Se importaron {insertados} filas a 'trainings' ✅")
                st.cache_data.clear()

    st.divider()
    # Vista rápida de lo que hay en la BD (opcional, sin edición)
    try:
        df_tr = load_table("trainings")
        if len(df_tr) > 0:
            st.markdown("#### Entrenamientos en BD")
            st.dataframe(df_tr, use_container_width=True)
        else:
            st.info("Aún no hay entrenamientos importados.")
    except Exception as e:
        st.warning(f"No se pudo cargar 'trainings': {e}")


# ---------------------------- Rendimiento ---------------------------- #

elif section_key == "Rendimiento":
    st.markdown("## 📈 Rendimiento y carga")

    # Cargar y filtrar SIEMPRE por atleta (y por evento en throws)
    df_t = load_table("throws")
    if len(df_t) > 0:
        if "athlete" in df_t.columns:
            df_t = df_t[df_t["athlete"] == atleta]
        if "event" in df_t.columns:
            df_t = df_t[df_t["event"] == athlete_event]

    df_f = load_table("fatigue")
    if len(df_f) > 0 and "athlete" in df_f.columns:
        df_f = df_f[df_f["athlete"] == atleta]

    df_g = load_table("gym_logs")
    if len(df_g) > 0 and "athlete" in df_g.columns:
        df_g = df_g[df_g["athlete"] == atleta]

    # Encabezado de KPIs
    colK1, colK2, colK3 = st.columns(3)
    best = float(df_t["distance"].max()) if len(df_t) and not df_t["distance"].dropna().empty else None
    avg_rpe = float(df_f["rpe"].mean()) if len(df_f) and not df_f["rpe"].dropna().empty else None
    with colK1:
        metric_card(
            "Mejor lanzamiento histórico",
            f"{best:.2f} m" if best else "—",
            f"Atleta: {atleta} • Evento: {athlete_event.capitalize()}"
        )
    with colK2:
        metric_card("RPE medio", f"{avg_rpe:.1f}" if avg_rpe else "—")
    with colK3:
        metric_card("Sesiones registradas", f"{len(df_t)}")

    st.divider()
    st.markdown("### Añadir percepción de carga / fatiga")
    with st.form("fatigue_form"):
        c1, c2, c3, c4 = st.columns(4)
        date = c1.date_input("Fecha", value=dt.date.today(), key="fat_date")
        rpe = c2.slider("RPE (1-10)", 1, 10, 6)
        sleep_hours = c3.number_input("Horas de sueño", 0.0, 24.0, 8.0, 0.5)
        soreness = c4.slider("Dolor muscular (0-10)", 0, 10, 2)
        notes = st.text_input("Notas")
        ok = st.form_submit_button("Guardar", use_container_width=True)
    if ok:
        insert_row("fatigue", {
            "date": str(date),
            "rpe": int(rpe),
            "sleep_hours": float(sleep_hours),
            "soreness": int(soreness),
            "notes": notes,
            "athlete": atleta,  # ← guardar el atleta
        })
        st.success("Fatiga registrada ✅")
        st.cache_data.clear()

    cA, cB = st.columns(2)
    with cA:
        st.markdown("#### Progresión de distancias")
        if len(df_t) > 0:
            plot_df = df_t.dropna(subset=["distance"]).copy()
            if len(plot_df) > 0:
                plot_df["date"] = pd.to_datetime(plot_df["date"], errors="coerce")
                plot_df = plot_df.sort_values("date")
                fig, ax = plt.subplots()
                ax.plot(plot_df["date"], plot_df["distance"], marker="o")
                ax.set_xlabel("Fecha")
                ax.set_ylabel("Distancia (m)")
                ax.set_title(f"Distancia por sesión — {atleta}")
                st.pyplot(fig)
            else:
                st.info("Añade distancias para ver la gráfica.")
        else:
            st.info("Sin datos de lanzamientos para este atleta.")
    with cB:
        st.markdown("#### Carga percibida (RPE)")
        if len(df_f) > 0:
            plot_df = df_f.copy()
            plot_df["date"] = pd.to_datetime(plot_df["date"], errors="coerce")
            plot_df = plot_df.sort_values("date")
            fig, ax = plt.subplots()
            ax.plot(plot_df["date"], plot_df["rpe"], marker="o")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("RPE (1-10)")
            ax.set_title(f"Percepción de esfuerzo — {atleta}")
            st.pyplot(fig)
        else:
            st.info("Registra RPE para ver tendencias.")

    st.divider()
    st.markdown("### Registro de gimnasio (fuerza)")
    with st.form("gym_form"):
        c1, c2, c3, c4, c5 = st.columns(5)
        date = c1.date_input("Fecha", value=dt.date.today(), key="gym_date")
        exercise = c2.text_input("Ejercicio", placeholder="Press militar, sentadilla...")
        weight = c3.number_input("Peso (kg)", 0.0, 500.0, 0.0, 0.5)
        reps = c4.number_input("Reps", 0, 100, 0)
        velocity = c5.number_input("Velocidad barra (m/s)", 0.0, 5.0, 0.0, 0.01)
        notes = st.text_input("Notas", key="gym_notes")
        ok2 = st.form_submit_button("Guardar", use_container_width=True)
    if ok2:
        insert_row("gym_logs", {
            "date": str(date),
            "exercise": exercise,
            "weight": float(weight),
            "reps": int(reps),
            "velocity": float(velocity) if velocity else None,
            "notes": notes,
            "athlete": atleta,  # ← guardar el atleta
        })
        st.success("Sesión de fuerza guardada ✅")
        st.cache_data.clear()

    # Mostrar solo los logs del atleta
    df_g_show = load_table("gym_logs")
    if len(df_g_show) > 0 and "athlete" in df_g_show.columns:
        df_g_show = df_g_show[df_g_show["athlete"] == atleta]
    st.dataframe(df_g_show, use_container_width=True)

# ---------------------------- Planificación ---------------------------- #

elif section_key == "Planificación":
    st.markdown("## 🗓️ Planificación y objetivos")

    tabC, tabD = st.tabs(["📅 Calendario", "🎯 Objetivos"])

    with tabC:
        with st.form("plan_form"):
            c1, c2 = st.columns(2)
            date = c1.date_input("Fecha", value=dt.date.today())
            title = c2.text_input("Título de la sesión", placeholder="Técnica / Fuerza / Velocidad...")
            details = st.text_area("Detalle (series, ejercicios, puntos técnicos)")
            ok = st.form_submit_button("Añadir", use_container_width=True)
        if ok:
            insert_row("plans", {"date": str(date), "title": title, "details": details})
            st.success("Sesión programada ✅")
            st.cache_data.clear()
        st.dataframe(load_table("plans"), use_container_width=True)

    with tabD:
        with st.form("goal_form"):
            c1, c2, c3 = st.columns(3)
            start_date = c1.date_input("Inicio", value=dt.date.today())
            end_date = c2.date_input("Fin", value=dt.date.today() + dt.timedelta(days=30))
            title = c3.text_input("Objetivo", placeholder="Mejorar separación cadera-hombro")
            c4, c5 = st.columns(2)
            metric = c4.text_input("Métrica", placeholder="Distancia (m), RPE, velocidad…")
            target = c5.number_input("Meta numérica (opcional)", 0.0, 1000.0, 0.0, 0.1)
            notes = st.text_area("Notas")
            ok2 = st.form_submit_button("Guardar objetivo", use_container_width=True)
        if ok2:
            insert_row("goals", {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "title": title,
                "metric": metric,
                "target": float(target) if target else None,
                "notes": notes,
            })
            st.success("Objetivo guardado ✅")
            st.cache_data.clear()
        st.dataframe(load_table("goals"), use_container_width=True)

# ---------------------------- Lesiones ---------------------------- #

elif section_key == "Lesiones":
    st.markdown("## 🩹 Prevención y molestias")

    with st.form("inj_form"):
        c1, c2, c3 = st.columns(3)
        date = c1.date_input("Fecha", value=dt.date.today())
        area = c2.text_input("Zona afectada", placeholder="Hombro anterior, codo, lumbar…")
        pain = c3.slider("Dolor (0-10)", 0, 10, 2)
        description = st.text_area("Descripción")
        action = st.text_input("Acciones / tratamiento", placeholder="Hielo, cupping, descanso…")
        ok = st.form_submit_button("Guardar", use_container_width=True)
    if ok:
        insert_row("injuries", {
            "date": str(date),
            "area": area,
            "pain_level": int(pain),
            "description": description,
            "action": action,
        })
        st.success("Registro de lesión/monitoreo guardado ✅")
        st.cache_data.clear()

    df = load_table("injuries")
    st.dataframe(df, use_container_width=True)

    if len(df) > 0:
        st.markdown("#### Dolor a lo largo del tiempo")
        plot_df = df.copy()
        plot_df["date"] = pd.to_datetime(plot_df["date"]).sort_values()
        fig, ax = plt.subplots()
        ax.plot(plot_df["date"], plot_df["pain_level"], marker="o")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Dolor (0-10)")
        ax.set_title("Evolución del dolor")
        st.pyplot(fig)

# ---------------------------- Recuperación ---------------------------- #

elif section_key == "Recuperación":
    st.markdown("## 🧊 Recuperación")

    st.markdown(
        """
        **Rutina sugerida post-entreno (editable):**
        - 10–15' movilidad de hombro y columna torácica
        - 8–12' estiramientos activos de pectoral, dorsal y flexores de cadera
        - 2–3 series de respiración diafragmática (90/90)
        - Automasaje suave en manguito rotador (3–5')
        - Cupping ligero 24–48h post-sesión (si te va bien)
        - Hidratación + proteína
        """
    )

    with st.form("rec_form"):
        note = st.text_area("Añade recordatorios de recuperación")
        ok = st.form_submit_button("Guardar nota", use_container_width=True)
    if ok:
        insert_row("plans", {"date": str(dt.date.today()), "title": "Recuperación", "details": note})
        st.success("Nota guardada en planificación ✅")
        st.cache_data.clear()

# ---------------------------- Chat ---------------------------- #

elif section_key == "Chat":
    st.markdown("## 💬 Chat atleta ↔ entrenador")

    with st.form("chat_form"):
        c1, c2 = st.columns([1,3])
        sender = c1.selectbox("Remitente", ["Atleta", "Entrenador"]) 
        message = c2.text_input("Mensaje")
        ok = st.form_submit_button("Enviar", use_container_width=True)
    if ok and message.strip():
        insert_row("chat", {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "sender": sender,
            "message": message.strip(),
        })
        st.cache_data.clear()

    df = load_table("chat")
    if len(df) == 0:
        st.info("No hay mensajes aún.")
    else:
        for _, r in df.sort_values("id").iterrows():
            st.markdown(f"**{r['timestamp']} — {r['sender']}:** {r['message']}")

# ---------------------------- Ajustes ---------------------------- #

elif section_key == "Ajustes":
    st.markdown("## ⚙️ Ajustes y utilidades")

    with st.expander("Exportar datos (.csv)", expanded=True):
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
        tables = ["throws", "fatigue", "gym_logs", "injuries", "plans", "goals", "chat", "best_marks"]
        buttons = [c1, c2, c3, c4, c5, c6, c7, c8]
        for t, col in zip(tables, buttons):
            with col:
                df = load_table(t)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=t+".csv",
                    data=csv,
                    file_name=f"{t}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    with st.expander("Borrar registros (usar con cuidado)"):
        target_table = st.selectbox("Tabla", ["throws", "fatigue", "gym_logs", "injuries", "plans", "goals", "chat", "best_marks"])
        df = load_table(target_table)
        if len(df) > 0:
            rid = st.number_input("ID a borrar", min_value=int(df["id"].min()), max_value=int(df["id"].max()))
            if st.button("Borrar por ID", type="secondary"):
                delete_row(target_table, int(rid))
                st.success("Eliminado ✅")
                st.cache_data.clear()
        else:
            st.info("No hay filas en esta tabla.")