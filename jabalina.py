# app.py
# --------------------------------------------------------------
# App básica (Streamlit) para atleta y entrenador de jabalina — DISEÑO MEJORADO (Tema claro)
# --------------------------------------------------------------
# - Registro de lanzamientos (distancia, notas, vídeo)
# - Análisis simple de vídeo + extracción de fotogramas
# - Comparación lado a lado de dos vídeos/fotogramas
# - Mejores marcas por temporada (Top 3 y resumen histórico)
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
  --muted: #475569;     /* texto secundario (slate-600) */
  --brand: #1d4ed8;     /* azul 700 */
  --accent: #16a34a;    /* verde 600 */
  --warn: #d97706;      /* amber-600 */
  --danger: #dc2626;    /* red-600 */
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

@st.cache_data(show_spinner=False)
def load_table(table: str) -> pd.DataFrame:
    with get_conn() as con:
        return pd.read_sql_query(f"SELECT * FROM {table} ORDER BY id DESC", con)


def insert_row(table: str, data: dict):
    keys = ",".join(data.keys())
    placeholders = ",".join([":" + k for k in data.keys()])
    with get_conn() as con:
        con.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", data)
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

st.sidebar.title("🏹 Jabalina Coach")
section = st.sidebar.radio(
    "Navegación",
    [
        "🏠 Lanzamientos",
        "🆚 Comparación",
        "🏆 Mejores marcas",
        "📈 Rendimiento",
        "🗓️ Planificación",
        "🩹 Lesiones",
        "🧊 Recuperación",
        "💬 Chat",
        "⚙️ Ajustes",
    ],
)

st.sidebar.caption("MVP — Streamlit + SQLite")

# Normalizar sección (sin emoji para condiciones)
section_key = section.split(" ", 1)[1]

# ---------------------------- Lanzamientos ---------------------------- #

if section_key == "Lanzamientos":
    st.markdown("## Registro de lanzamientos")

    tab1, tab2 = st.tabs(["✍️ Registrar", "🗂️ Histórico & Vídeo"])

    with tab1:
        with st.container():
            c1, c2, c3 = st.columns([1,1,1])
            date = c1.date_input("Fecha", value=dt.date.today())
            session = c2.text_input("Sesión / lugar", placeholder="Pista, playa, etc.")
            distance = c3.number_input("Distancia (m)", min_value=0.0, step=0.1)
            notes = st.text_area("Notas técnicas (penúltimo paso, separación cadera-hombro, etc.)")
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
                    },
                )
                st.success("Lanzamiento guardado ✅")
                st.cache_data.clear()

    with tab2:
        df = load_table("throws")
        if len(df) == 0:
            st.info("Aún no hay lanzamientos registrados.")
        else:
            cA, cB = st.columns([2, 1])
            with cA:
                st.markdown("#### Historial")
                st.dataframe(df, use_container_width=True)
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
                else:
                    st.warning("Este registro no tiene vídeo adjunto.")

# ---------------------------- Comparación ---------------------------- #

elif section_key == "Comparación":
    st.markdown("## Comparación lado a lado")
    df = load_table("throws")
    if len(df) < 1:
        st.info("Registra al menos un lanzamiento en la sección 'Lanzamientos'.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Lado A")
            id1 = st.selectbox("Selecciona A", df["id"].tolist(), index=0, key="cmpA")
            r1 = df[df.id == id1].iloc[0]
            if pd.notna(r1.get("video_path")) and str(r1["video_path"]).strip():
                st.video(r1["video_path"])
                if cv2 is not None:
                    total1 = video_frame_count(r1["video_path"]) or 1
                    idx1 = st.slider("Frame A", 0, max(0, total1 - 1), 0)
                    f1 = extract_frame(r1["video_path"], idx1)
                    if f1 is not None:
                        st.image(f1, caption=f"A — Frame {idx1}")
            else:
                st.warning("Sin vídeo en A")
        with c2:
            st.markdown("#### Lado B")
            id2 = st.selectbox("Selecciona B", df["id"].tolist(), index=min(1, len(df)-1), key="cmpB")
            r2 = df[df.id == id2].iloc[0]
            if pd.notna(r2.get("video_path")) and str(r2["video_path"]).strip():
                st.video(r2["video_path"])
                if cv2 is not None:
                    total2 = video_frame_count(r2["video_path"]) or 1
                    idx2 = st.slider("Frame B", 0, max(0, total2 - 1), 0)
                    f2 = extract_frame(r2["video_path"], idx2)
                    if f2 is not None:
                        st.image(f2, caption=f"B — Frame {idx2}")
            else:
                st.warning("Sin vídeo en B")

    st.caption("Tip: usa el mismo índice de frame para comparar posturas clave.")

# ---------------------------- Mejores marcas ---------------------------- #

elif section_key == "Mejores marcas":
    st.markdown("## 🏆 Mejores marcas por temporada")

    df_throws = load_table("throws")
    df_gym = load_table("gym_logs")

    if len(df_throws) > 0 and "date" in df_throws.columns:
        df_throws["season"] = pd.to_datetime(df_throws["date"], errors="coerce").dt.year
    if len(df_gym) > 0 and "date" in df_gym.columns:
        df_gym["season"] = pd.to_datetime(df_gym["date"], errors="coerce").dt.year

    seasons = set()
    if len(df_throws) > 0 and "season" in df_throws.columns:
        seasons.update(df_throws["season"].dropna().unique().tolist())
    if len(df_gym) > 0 and "season" in df_gym.columns:
        seasons.update(df_gym["season"].dropna().unique().tolist())
    seasons = sorted([int(s) for s in seasons], reverse=True)

    if len(seasons) == 0:
        st.info("No hay datos registrados para mostrar mejores marcas.")
    else:
        selected_season = st.selectbox("Selecciona temporada", seasons)
        st.markdown(":blue[Resumen de la temporada]")
        st.write(" ")

        def _top_n(df: pd.DataFrame, value_col: str, n: int = 3):
            if len(df) == 0 or value_col not in df.columns:
                return pd.DataFrame()
            d = df.dropna(subset=[value_col]).copy()
            if len(d) == 0:
                return pd.DataFrame()
            d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
            d = d.dropna(subset=[value_col])
            d = d.sort_values(value_col, ascending=False).head(n)
            return d

        # Métricas rápidas (tarjetas)
        cards = st.columns(4)
        if len(df_throws) > 0 and "season" in df_throws.columns and "distance" in df_throws.columns:
            ej = df_throws[df_throws["season"] == selected_season]
            best = ej["distance"].max() if len(ej) else None
            with cards[0]:
                metric_card("Mejor jabalina", f"{best:.2f} m" if pd.notna(best) else "—", "máxima distancia")
        if len(df_gym) > 0 and "season" in df_gym.columns and "exercise" in df_gym.columns:
            gym_temp = df_gym[df_gym["season"] == selected_season]
            def _best_kw(df, pattern):
                s = df[df["exercise"].str.contains(pattern, case=False, na=False)]
                return float(s["weight"].max()) if len(s) and not s["weight"].dropna().empty else None
            with cards[1]:
                v = _best_kw(gym_temp, "sentadilla")
                metric_card("Sentadilla", f"{v:.0f} kg" if v else "—", "récord temporada")
            with cards[2]:
                v = _best_kw(gym_temp, "pectoral|press banca|bench")
                metric_card("Pectoral", f"{v:.0f} kg" if v else "—", "récord temporada")
            with cards[3]:
                v = _best_kw(gym_temp, "balon medicinal")
                metric_card("Balón medicinal", f"{v:.0f} kg" if v else "—", "récord temporada")

        st.write(" ")
        st.markdown("### Top 3 por categoría (con fecha)")

        rows = []
        if len(df_throws) > 0 and "season" in df_throws.columns:
            jdf = df_throws[df_throws["season"] == selected_season].copy()
            if "distance" in jdf.columns:
                jdf = jdf.rename(columns={"distance": "valor"})
                top = _top_n(jdf, "valor", 3)
                for _, r in top.iterrows():
                    rows.append({
                        "Categoría": "Jabalina",
                        "Valor": f"{float(r['valor']):.2f} m",
                        "Fecha": r.get("date", ""),
                        "Detalle": r.get("session", "")
                    })
        if len(df_gym) > 0 and "season" in df_gym.columns:
            gym_df = df_gym[df_gym["season"] == selected_season].copy()
            ejercicios = {
                "Balón medicinal": ["balon", "medicinal", "med ball"],
                "Sentadilla": ["sentadilla", "squat"],
                "Pectoral": ["pector", "press banca", "bench"],
                "Pull Over": ["pull over"],
            }
            if "exercise" in gym_df.columns:
                col = gym_df["exercise"].astype(str).str.lower()
                for nombre, kws in ejercicios.items():
                    mask = np.logical_or.reduce([col.str.contains(k, na=False) for k in kws]) if len(kws)>1 else col.str_contains(kws[0], na=False)
                    sub = gym_df[mask].copy()
                    if "weight" in sub.columns:
                        sub = sub.rename(columns={"weight": "valor"})
                        top = _top_n(sub, "valor", 3)
                        for _, r in top.iterrows():
                            rows.append({
                                "Categoría": nombre,
                                "Valor": (f"{float(r['valor']):.1f} kg" if pd.notna(r.get('valor')) else ""),
                                "Fecha": r.get("date", ""),
                                "Detalle": r.get("exercise", "")
                            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar un Top 3 detallado.")

        st.divider()
        st.markdown("### Resumen histórico (por temporada)")
        resumen_data = []
        for temporada in seasons:
            fila = {"Temporada": temporada}
            if len(df_throws) > 0 and "season" in df_throws.columns and "distance" in df_throws.columns:
                temp_j = df_throws[df_throws["season"] == temporada]
                fila["Jabalina (m)"] = float(temp_j["distance"].max()) if len(temp_j) and not temp_j["distance"].dropna().empty else None
            if len(df_gym) > 0 and "season" in df_gym.columns and "exercise" in df_gym.columns and "weight" in df_gym.columns:
                temp_g = df_gym[df_gym["season"] == temporada]
                def _best_kw2(df, pattern):
                    sub = df[df["exercise"].str.contains(pattern, case=False, na=False)]
                    return float(sub["weight"].max()) if len(sub) and not sub["weight"].dropna().empty else None
                fila["Balón medicinal (kg)"] = _best_kw2(temp_g, "balon medicinal")
                fila["Sentadilla (kg)"] = _best_kw2(temp_g, "sentadilla")
                fila["Pectoral (kg)"] = _best_kw2(temp_g, "pectoral|press banca|bench")
                fila["Pull Over (kg)"] = _best_kw2(temp_g, "pull over")
            resumen_data.append(fila)
        st.dataframe(pd.DataFrame(resumen_data), use_container_width=True)

# ---------------------------- Rendimiento ---------------------------- #

elif section_key == "Rendimiento":
    st.markdown("## 📈 Rendimiento y carga")

    # Encabezado de KPIs
    colK1, colK2, colK3 = st.columns(3)
    df_t = load_table("throws")
    df_f = load_table("fatigue")
    best = float(df_t["distance"].max()) if len(df_t) and not df_t["distance"].dropna().empty else None
    avg_rpe = float(df_f["rpe"].mean()) if len(df_f) and not df_f["rpe"].dropna().empty else None
    with colK1:
        metric_card("Mejor jabalina histórico", f"{best:.2f} m" if best else "—")
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
        })
        st.success("Fatiga registrada ✅")
        st.cache_data.clear()

    cA, cB = st.columns(2)
    with cA:
        st.markdown("#### Progresión de distancias")
        if len(df_t) > 0:
            plot_df = df_t.dropna(subset=["distance"]).copy()
            if len(plot_df) > 0:
                plot_df["date"] = pd.to_datetime(plot_df["date"]).sort_values()
                fig, ax = plt.subplots()
                ax.plot(plot_df["date"], plot_df["distance"], marker="o")
                ax.set_xlabel("Fecha")
                ax.set_ylabel("Distancia (m)")
                ax.set_title("Distancia por sesión")
                st.pyplot(fig)
            else:
                st.info("Añade distancias para ver la gráfica.")
        else:
            st.info("Sin datos de lanzamientos.")
    with cB:
        st.markdown("#### Carga percibida (RPE)")
        if len(df_f) > 0:
            plot_df = df_f.copy()
            plot_df["date"] = pd.to_datetime(plot_df["date"]).sort_values()
            fig, ax = plt.subplots()
            ax.plot(plot_df["date"], plot_df["rpe"], marker="o")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("RPE (1-10)")
            ax.set_title("Percepción de esfuerzo")
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
        })
        st.success("Sesión de fuerza guardada ✅")
        st.cache_data.clear()

    st.dataframe(load_table("gym_logs"), use_container_width=True)

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
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        tables = ["throws", "fatigue", "gym_logs", "injuries", "plans", "goals", "chat"]
        buttons = [c1, c2, c3, c4, c5, c6, c7]
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
        target_table = st.selectbox("Tabla", ["throws", "fatigue", "gym_logs", "injuries", "plans", "goals", "chat"])
        df = load_table(target_table)
        if len(df) > 0:
            rid = st.number_input("ID a borrar", min_value=int(df["id"].min()), max_value=int(df["id"].max()))
            if st.button("Borrar por ID"):
                delete_row(target_table, int(rid))
                st.success("Eliminado ✅")
                st.cache_data.clear()
        else:
            st.info("No hay filas en esta tabla.")

# ---------------------------- Footer ---------------------------- #

st.sidebar.markdown("---")
st.sidebar.caption("Consejo: para extraer fotogramas instala OpenCV: `pip install opencv-python`.Para usarla como PWA en iPhone: Safari → Compartir → *Añadir a pantalla de inicio*.")
