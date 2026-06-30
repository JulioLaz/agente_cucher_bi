'''
Agente Cucher BI — Streamlit + NVIDIA NIM + MotherDuck
Dashboard híbrido: KPIs fijos + panel dinámico + chat con agente metacognitivo.
=============================================================
Versión: 5.0.0
Cambios:
  5.0.0 - Refactorización completa en módulos:
          config, catalogo, enriquecedor, templates, ejecutor,
          llm, interprete, procesador, graficos, kpis, notificaciones
  4.x.x - Versiones anteriores monolíticas
=============================================================
'''
import sys
import os
import json

# Asegurar path del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── INYECTAR SECRETS COMO ENV VARS ANTES DE CUALQUIER IMPORT LOCAL ──
# Esto evita que streamlit confunda módulos locales con keys de secrets
import streamlit as st

def _inject_secrets():
    """Copia st.secrets a os.environ para que los módulos locales los lean."""
    keys = ["TOKEN_MATHERDUCK", "key_nvidia", "token_bot_telegram"]
    for k in keys:
        try:
            val = st.secrets[k]
            os.environ[k] = str(val)
        except Exception:
            pass
    # Usuarios
    try:
        usuarios = dict(st.secrets["usuarios"])
        os.environ["USUARIOS_JSON"] = json.dumps(usuarios)
    except Exception:
        pass

_inject_secrets()

import time
import plotly.graph_objects as go
from datetime import date

# Módulos del proyecto — DESPUÉS de inyectar secrets
from config import HISTORIAL_PATH, COLORES_SUC
from procesador import procesar
from interprete import interpretar
from graficos import (grafico_auto, grafico_ventas_sucursal,
                      grafico_utilidad_diaria, grafico_utilidad_mensual)
from kpis import (cargar_kpis_header, cargar_kpis_alertas,
                  cargar_ventas_sucursal_mes,
                  cargar_utilidad_diaria, cargar_utilidad_mensual,
                  cargar_familias, cargar_subfamilias, cargar_proveedores)
from notificaciones import (enviar_telegram, guardar_historial,
                             notificar_capacidad_faltante)


# ─── CONFIGURACIÓN UI ─────────────────────────────────────────
st.set_page_config(
    page_title="Cucher BI Agent",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)


def aplicar_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background-color:#fdf6e3;color:#1a1a2e;}

/* Sidebar azul marino */
section[data-testid="stSidebar"]{background-color:#1a2744;border-right:none;}
section[data-testid="stSidebar"] *{color:#e2e8f0 !important;}
section[data-testid="stSidebar"] .stSelectbox>div>div{
    background:#253356 !important;border-color:#3a4f7a !important;}

/* KPI cards */
.kpi-card{border-radius:10px;padding:14px 16px;text-align:center;
  box-shadow:0 2px 8px rgba(0,0,0,0.12);border:none;}
.kpi-card-venta {background:linear-gradient(135deg,#1a2744,#2e4a8a);}
.kpi-card-util  {background:linear-gradient(135deg,#14532d,#16a34a);}
.kpi-card-margen{background:linear-gradient(135deg,#92400e,#d97706);}
.kpi-card-presu {background:linear-gradient(135deg,#4a1942,#9333ea);}
.kpi-card-dias  {background:linear-gradient(135deg,#1e3a5f,#0ea5e9);}
.kpi-val{font-size:1.2rem;font-weight:700;color:#ffffff !important;}
.kpi-lbl{font-size:0.68rem;color:rgba(255,255,255,0.75)!important;
  margin-top:3px;font-weight:500;text-transform:uppercase;letter-spacing:0.04em;}
.kpi-delta-pos{font-size:0.70rem;color:#86efac !important;font-weight:600;}
.kpi-delta-neg{font-size:0.70rem;color:#fca5a5 !important;font-weight:600;}

/* Badges */
.skill-badge{display:inline-block;background:#1a2744;color:#93c5fd !important;
  border-radius:5px;padding:2px 10px;font-size:0.72rem;font-weight:600;
  margin-bottom:4px;border:1px solid #3a4f7a;}
.time-badge{display:inline-block;background:#14532d;color:#86efac !important;
  border-radius:5px;padding:2px 10px;font-size:0.72rem;
  margin-left:6px;border:1px solid #166534;}

/* Panel títulos */
.panel-title{font-size:0.78rem;font-weight:700;color:#f0f4ff !important;
  text-transform:uppercase;letter-spacing:0.06em;
  margin-bottom:6px;border-bottom:2px solid #d97706;padding-bottom:3px;}
.panel-azul{background-color:#1a2744;border-radius:12px;padding:14px 12px;}
/* Panel derecho fondo azul via selector de columna */
[data-testid="column"]:last-child {
    background-color: #1a2744 !important;
    border-radius: 12px;
    padding: 12px 10px;
}
[data-testid="column"]:last-child * {
    color: #e2e8f0 !important;
}

/* Chat */
[data-testid="stChatMessage"]{background:#ffffff !important;
  border-radius:10px !important;border:1px solid #e8d5a3 !important;
  margin-bottom:6px !important;box-shadow:0 1px 4px rgba(0,0,0,0.07)!important;}
[data-testid="stChatInput"] textarea{background:#ffffff !important;
  color:#1a1a2e !important;border:2px solid #1a2744 !important;
  border-radius:10px !important;}
[data-testid="stChatInput"] textarea:focus{border-color:#d97706 !important;}
.stChatFloatingInputContainer{background:#fdf6e3 !important;
  border-top:1px solid #e8d5a3 !important;}

/* Botones */
.stButton>button{background:#1a2744 !important;color:#ffffff !important;
  border:none !important;border-radius:8px !important;
  font-weight:600 !important;transition:background 0.2s;}
.stButton>button:hover{background:#d97706 !important;}

/* Card interpretación */
.card-interp{background:#e8f4fd;border:2px solid #1a2744;
  border-radius:12px;padding:16px 20px;margin-bottom:12px;}
.card-no-puede{background:#fef2f2;border:2px solid #dc2626;
  border-radius:12px;padding:16px 20px;margin-bottom:12px;}

div[data-testid="stPlotlyChart"]{border-radius:10px;overflow:hidden;}

/* ── LOGIN FORM ── */
[data-testid="stForm"]{
    background:#fdf6e3;
    border-radius:16px;
    padding:32px 40px;
    max-width:400px;
    margin:80px auto;
    box-shadow:0 20px 60px rgba(0,0,0,0.15);
    border:2px solid #e8d5a3;
}
[data-testid="stForm"] h4{
    text-align:center;color:#1a2744;margin-bottom:20px;
}
[data-testid="stForm"] .stButton>button{
    background:#1a2744 !important;color:#fff !important;
    font-size:1rem !important;padding:10px !important;
    border-radius:8px !important;margin-top:8px;
}
[data-testid="stForm"] .stButton>button:hover{
    background:#d97706 !important;
}
</style>
""", unsafe_allow_html=True)


# ─── AUTENTICACIÓN — PRIMERO QUE TODO ────────────────────────
from config import get_usuarios
USUARIOS_VALIDOS = get_usuarios()

def mostrar_login():
    """Pantalla de login simple y funcional."""
    # Fondo completo azul marino
    st.markdown("""
<style>
.stApp { background-color: #1a2744 !important; }
section[data-testid="stSidebar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

    # Centrar con columnas
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
<div style="text-align:center;margin-bottom:24px;">
  <div style="font-size:3.5rem;">🛒</div>
  <div style="font-size:1.6rem;font-weight:700;color:#ffffff;margin-top:8px;">
    Cucher · Agente BI
  </div>
  <div style="font-size:0.85rem;color:#94a3b8;margin-top:6px;">
    Ingresá tus credenciales para continuar
  </div>
</div>
""", unsafe_allow_html=True)

        with st.form("login_form"):
            usuario  = st.text_input("👤 Usuario", placeholder="cristina / horacio / julio")
            password = st.text_input("🔑 Contraseña", type="password",
                                     placeholder="••••••••••••")
            submitted = st.form_submit_button("→ Ingresar",
                                              width="stretch")
            if submitted:
                u = usuario.strip().lower()
                if u in USUARIOS_VALIDOS and password == USUARIOS_VALIDOS[u]:
                    st.session_state["usuario_actual"] = u
                    st.session_state["autenticado"]    = True
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos. Intentá de nuevo.")

# Inicializar estado de auth
if "autenticado"    not in st.session_state:
    st.session_state["autenticado"]    = False
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = ""

# Mostrar login si no está autenticado — ANTES de cargar el dashboard
if not st.session_state["autenticado"]:
    mostrar_login()
    st.stop()

# Solo llegar acá si está autenticado
aplicar_css()

# ─── ESTADO ──────────────────────────────────────────────────
KEYS_DEFAULT = {
    "messages":                [],
    "historial":               [],
    "ultimo_df":               None,
    "ultimo_modo":             None,
    "interpretacion_pendiente":None,
    "pregunta_pendiente":      "",
    "dfs_guardados":           {},
}
for k, v in KEYS_DEFAULT.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── SIDEBAR ─────────────────────────────────────────────────
with st.sidebar:
    usuario_actual = st.session_state.get("usuario_actual","").capitalize()
    st.markdown(f"### 🛒 Cucher · Agente BI")
    st.markdown(f"👤 **{usuario_actual}** · "
                f"<span style='font-size:0.75rem;color:#94a3b8;cursor:pointer;' "
                f"onclick=''>Salir</span>", unsafe_allow_html=True)
    if st.button("🚪 Cerrar sesión", width="stretch", key="btn_logout"):
        st.session_state["autenticado"]    = False
        st.session_state["usuario_actual"] = ""
        st.rerun()
    st.markdown("---")
    st.markdown("**📖 Catálogo — solo referencia**")
    st.caption("Usá estos valores para formular mejor tus preguntas")

    try:
        familias_lst = cargar_familias()
        familia_sel  = st.selectbox(f"Familia ({len(familias_lst)})",
                                    ["Todas"] + familias_lst)
    except Exception:
        familia_sel = "Todas"
        st.selectbox("Familia", ["Todas"])

    try:
        subfamilias_lst = cargar_subfamilias(familia_sel)
        subfamilia_sel  = st.selectbox(f"Subfamilia ({len(subfamilias_lst)})",
                                        ["Todas"] + subfamilias_lst)
    except Exception:
        subfamilia_sel = "Todas"
        st.selectbox("Subfamilia", ["Todas"])

    try:
        proveedores_lst = cargar_proveedores(familia_sel, subfamilia_sel)
        st.selectbox(f"Proveedor ({len(proveedores_lst)})",
                     ["Todos"] + proveedores_lst)
    except Exception:
        st.selectbox("Proveedor", ["Todos"])

    st.markdown("---")

    with st.expander("ℹ️ ¿Para qué sirvo?", expanded=False):
        st.markdown("""
| | Capacidad |
|---|---|
| 📊 | Ventas por sucursal, artículo, familia, período |
| 🏆 | Top artículos más vendidos y comparaciones de marcas |
| 📈 | Tendencia diaria y mensual |
| 📦 | Stock actual por sucursal |
| 🚨 | Alertas de reabastecimiento y quiebre |
| 🌡️ | Artículos en su mejor momento estacional |
| 💰 | Último precio de compra OC |
| 📉 | Margen real vs costo de compra |
| 🏭 | Ranking y comparación de proveedores |

**💡 Tips:**
- Mencioná sucursal, marca, medida o período en la pregunta
- *"Cervezas de más de 900cc más vendidas en Hiper"*
- *"Precios de compra de yerba 500g"*
- *"Comparar Quilmes vs Schneider en junio"*
""")

    st.markdown("---")
    if st.button("🗑️ Limpiar chat", width="stretch"):
        for k, v in KEYS_DEFAULT.items():
            st.session_state[k] = v
        st.rerun()

    if os.path.exists(HISTORIAL_PATH):
        with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
            _hist = json.load(f)
        st.download_button(
            "📥 Descargar historial",
            data=json.dumps(_hist, ensure_ascii=False, indent=2),
            file_name=f"historial_{date.today()}.json",
            mime="application/json",
            width="stretch"
        )


# ─── LAYOUT: CHAT | PANEL DERECHO ────────────────────────────
col_chat, col_panel = st.columns([3, 1.1], gap="medium")

with col_chat:

    # ── KPIs HEADER ──────────────────────────────────────────
    kpis = cargar_kpis_header()
    if kpis:
        mes_nom = date.today().strftime("%B %Y")
        st.markdown(f"##### 🛒 Cucher Mercados · {mes_nom}")

        venta_m   = kpis.get("venta_m", 0)
        venta_ant = kpis.get("venta_m_ant", 1) or 1
        util_m    = kpis.get("util_m", 0)
        util_ant  = kpis.get("util_m_ant", 1) or 1
        margen    = kpis.get("margen_pct", 0)
        presu_m   = kpis.get("presu_m", 0)
        art_count = kpis.get("art_count", 0)
        dias      = kpis.get("dias", 0)

        delta_v   = round((venta_m - venta_ant) / venta_ant * 100, 1)
        delta_u   = round((util_m  - util_ant)  / util_ant  * 100, 1)
        cls_v     = "kpi-delta-pos" if delta_v >= 0 else "kpi-delta-neg"
        cls_u     = "kpi-delta-pos" if delta_u >= 0 else "kpi-delta-neg"
        arr_v     = "▲" if delta_v >= 0 else "▼"
        arr_u     = "▲" if delta_u >= 0 else "▼"

        def fmt_m(v):
            return "$" + f"{v*1e6:,.0f}".replace(",", ".") + " M"

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.markdown(
                f'<div class="kpi-card kpi-card-venta">'
                f'<div class="kpi-val">{fmt_m(venta_m)}</div>'
                f'<div class="kpi-lbl">💰 Venta Total</div>'
                f'<div class="{cls_v}">{arr_v} {abs(delta_v)}% vs mes ant</div></div>',
                unsafe_allow_html=True)
        with k2:
            st.markdown(
                f'<div class="kpi-card kpi-card-util">'
                f'<div class="kpi-val">{fmt_m(util_m)}</div>'
                f'<div class="kpi-lbl">📈 Utilidad</div>'
                f'<div class="{cls_u}">{arr_u} {abs(delta_u)}% vs mes ant</div></div>',
                unsafe_allow_html=True)
        with k3:
            cls_m  = "kpi-delta-neg" if margen < 18 else "kpi-delta-pos"
            ref_m  = "↔ Obj >18%" if margen < 18 else "✓ Sobre objetivo"
            st.markdown(
                f'<div class="kpi-card kpi-card-margen">'
                f'<div class="kpi-val">{margen:.1f}%</div>'
                f'<div class="kpi-lbl">📊 Margen Real</div>'
                f'<div class="{cls_m}">{ref_m}</div></div>',
                unsafe_allow_html=True)
        with k4:
            st.markdown(
                f'<div class="kpi-card kpi-card-presu">'
                f'<div class="kpi-val">{fmt_m(presu_m)}</div>'
                f'<div class="kpi-lbl">🛒 Presupuesto 30d</div>'
                f'<div class="kpi-delta-pos">~{int(art_count):,} artículos</div></div>',
                unsafe_allow_html=True)
        with k5:
            vd = round(venta_m / dias, 1) if dias else 0
            st.markdown(
                f'<div class="kpi-card kpi-card-dias">'
                f'<div class="kpi-val">{int(dias)}</div>'
                f'<div class="kpi-lbl">📅 Días con venta</div>'
                f'<div class="kpi-delta-pos">{fmt_m(vd)}/día</div></div>',
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── FILA DE ALERTAS ─────────────────────────────────
        alertas = cargar_kpis_alertas()
        if alertas:
            ss = alertas.get("sin_stock", 0)
            cr = alertas.get("criticos", 0)
            ur = alertas.get("urgentes", 0)
            ex = alertas.get("exceso_stock", 0)
            vp = alertas.get("valor_perdido_m", 0)
            pm = alertas.get("presupuesto_m", 0)

            a1, a2, a3, a4, a5, a6 = st.columns(6)
            alerta_items = [
                (a1, f"🔴 {int(ss)}", "Sin stock", "#dc2626"),
                (a2, f"🟠 {int(cr)}", "Stock crítico ≤3d", "#ea580c"),
                (a3, f"🟡 {int(ur)}", "Urgente ≤7d", "#ca8a04"),
                (a4, f"📦 {int(ex)}", "Exceso stock", "#0284c7"),
                (a5, f"💸 ${vp}M", "Valor perdido", "#7c3aed"),
                (a6, f"🛒 ${pm}M", "Presupuesto 30d", "#059669"),
            ]
            for col, val, lbl, color in alerta_items:
                with col:
                    st.markdown(
                        f'<div style="background:{color}22;border:1px solid {color}55;'                        f'border-radius:8px;padding:6px 10px;text-align:center;">'                        f'<div style="font-size:1rem;font-weight:700;color:{color};">{val}</div>'                        f'<div style="font-size:0.65rem;color:#6b7280;">{lbl}</div></div>',
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("ℹ️ ¿Para qué sirvo? — capacidades del agente",
                         expanded=False):
            st.markdown("""
| Categoría | Qué podés preguntar |
|---|---|
| 📊 **Ventas** | Sucursales, top artículos, tendencia, antes/después de un evento |
| 🗂️ **Catálogo** | Explorar familias, subfamilias con métricas |
| 📦 **Stock** | Quiebre, reabastecimiento, sobrestock |
| 🌡️ **Estacionalidad** | Mejor momento del año cruzado con stock crítico |
| 🏭 **Proveedores** | Ranking, artículos por proveedor, comparar precios |
| 💲 **Precio OC** | Último precio de compra, margen real vs precio venta |
| 🔍 **Artículo** | Detalle ventas + stock + alertas + precio compra |

**💡 Tips:**
- *"Cervezas de más de 900cc más vendidas"*
- *"Precios de cafe 1kg a proveedores"*
- *"Comparar Rosamonte vs Taragüi en junio"*
- *"Stock crítico de lácteos en Hiper"*
""")

    st.markdown("---")

    # ── PANEL DE INTERPRETACIÓN/CONFIRMACIÓN ─────────────────
    if st.session_state.interpretacion_pendiente:
        interp       = st.session_state.interpretacion_pendiente
        pregunta_pend = st.session_state.pregunta_pendiente
        puede        = interp.get("puede_responder", True)
        reformul     = interp.get("reformulacion", "")
        filtros_d    = interp.get("filtros_detectados", {})
        tablas       = interp.get("tablas_necesarias", [])
        limitacion   = interp.get("limitacion", "")

        if puede:
            filtros_str = " · ".join(
                f"**{k}:** {v}" for k,v in filtros_d.items() if v
            )
            tablas_str = ", ".join(f"`{t}`" for t in tablas) if tablas else ""
            st.markdown(f"""
<div class="card-interp">
<div style="font-size:0.85rem;color:#1a2744;font-weight:700;margin-bottom:8px;">
  🤖 Entendí tu pregunta — confirmá antes de ejecutar:
</div>
<div style="font-size:0.95rem;color:#1a1a2e;margin-bottom:10px;">{reformul}</div>
{f'<div style="font-size:0.78rem;color:#4b5563;margin-bottom:6px;">🔍 {filtros_str}</div>' if filtros_str else ''}
{f'<div style="font-size:0.75rem;color:#6b7280;">📋 Tablas: {tablas_str}</div>' if tablas_str else ''}
</div>""", unsafe_allow_html=True)

            col_si, col_no = st.columns([1, 1])
            with col_si:
                if st.button("✅ Sí, ejecutar", width="stretch",
                             key="btn_confirmar"):
                    with st.spinner("🤖 Consultando datos..."):
                        t0 = time.time()
                        try:
                            respuesta, df_r, modo = procesar(
                                pregunta_pend, st.session_state.historial)
                        except Exception as e:
                            respuesta, df_r, modo = f"❌ Error: {e}", None, "error"
                        t_total = time.time() - t0

                    iconos = {"template":"⚡","sql_libre":"🔧",
                              "sql_retry":"🔄","error_sql":"❌","sql_vacio":"🔧"}
                    icono = iconos.get(modo, "🔧")
                    respuesta_completa = (
                        f'<span class="skill-badge">{icono} {modo}</span>'
                        f'<span class="time-badge">⏱ {t_total:.1f}s</span>\n\n'
                        f'{respuesta}'
                    )

                    df_key = f"df_{len(st.session_state.messages)}"
                    if df_r is not None and not df_r.empty:
                        if "dfs_guardados" not in st.session_state:
                            st.session_state["dfs_guardados"] = {}
                        st.session_state["dfs_guardados"][df_key] = df_r
                    st.session_state.messages.append({
                        "role": "assistant", "content": respuesta_completa,
                        "tiene_grafico": df_r is not None and not df_r.empty,
                        "df_key": df_key if df_r is not None and not df_r.empty else None,
                        "pregunta": pregunta_pend
                    })
                    st.session_state.historial.append(
                        {"role":"user","content":pregunta_pend})
                    st.session_state.historial.append(
                        {"role":"assistant","content":respuesta})
                    st.session_state.ultimo_df   = df_r
                    st.session_state.ultimo_modo = modo
                    st.session_state.interpretacion_pendiente = None
                    st.session_state.pregunta_pendiente = ""
                    guardar_historial(pregunta_pend, respuesta, modo, t_total)
                    enviar_telegram(pregunta_pend, respuesta, modo, t_total,
                                    usuario=st.session_state.get("usuario_actual",""))
                    st.rerun()

            with col_no:
                if st.button("✏️ Corregir pregunta", width="stretch",
                             key="btn_corregir"):
                    st.session_state.interpretacion_pendiente = None
                    st.session_state.pregunta_pendiente = ""
                    st.rerun()
        else:
            # No puede responder
            st.markdown(f"""
<div class="card-no-puede">
<div style="font-size:0.85rem;color:#dc2626;font-weight:700;margin-bottom:8px;">
  ⛔ Fuera de mi alcance actual
</div>
<div style="font-size:0.95rem;color:#1a1a2e;margin-bottom:10px;">{reformul}</div>
<div style="font-size:0.85rem;color:#7f1d1d;margin-bottom:6px;">⚠️ {limitacion}</div>
<div style="font-size:0.78rem;color:#6b7280;">
  📋 Para ampliar capacidad necesitaría: {interp.get('datos_faltantes','')}
</div>
</div>""", unsafe_allow_html=True)

            st.info("📱 Notifiqué al equipo por Telegram para evaluar agregar esta capacidad.")
            notificar_capacidad_faltante(pregunta_pend, interp)

            respuesta_no = (
                f"⛔ **Fuera de alcance:** {reformul}\n\n"
                f"{limitacion}\n\n"
                f"📱 Notifiqué al equipo por Telegram."
            )
            st.session_state.messages.append({
                "role":"assistant","content":respuesta_no,
                "tiene_grafico":False,"pregunta":pregunta_pend
            })
            st.session_state.historial.append({"role":"user","content":pregunta_pend})
            st.session_state.historial.append({"role":"assistant","content":respuesta_no})
            st.session_state.interpretacion_pendiente = None
            st.session_state.pregunta_pendiente = ""
            st.rerun()

    # ── HISTORIAL DEL CHAT ───────────────────────────────────
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)
            if (msg.get("tiene_grafico")
                    and msg.get("df_key")
                    and msg["df_key"] in st.session_state.get("dfs_guardados", {})):
                df_msg = st.session_state["dfs_guardados"][msg["df_key"]]
                fig = grafico_auto(df_msg, msg.get("pregunta",""))
                if fig:
                    fig.update_layout(height=300,
                        margin=dict(l=0,r=0,t=30,b=0),
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#1a1a2e",size=10))
                    st.plotly_chart(fig, key=f"hist_{i}",
                                    width="stretch",
                                    config={"displayModeBar":False})

    # ── INPUT ────────────────────────────────────────────────
    st.markdown("##### 💬 Consultá al agente de datos")
    if pregunta := st.chat_input(
            "Preguntá sobre ventas, precios, stock, proveedores..."):

        st.session_state.messages.append({"role":"user","content":pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        # Paso 1: interpretar antes de ejecutar
        with st.chat_message("assistant"):
            with st.spinner("🧠 Analizando tu pregunta..."):
                t0    = time.time()
                interp = interpretar(pregunta)
                t_int  = time.time() - t0
                print(f"   [interp] {t_int:.1f}s → puede={interp.get('puede_responder')} "
                      f"| {interp.get('reformulacion','')[:80]}")

        st.session_state.interpretacion_pendiente = interp
        st.session_state.pregunta_pendiente = pregunta
        st.rerun()


# ─── PANEL DERECHO ───────────────────────────────────────────
with col_panel:
    # Panel con fondo via CSS aplicado al contenedor nativo de Streamlit

    mes_label = date.today().strftime("%B %Y")

    # Ventas del mes
    st.markdown(f'<div class="panel-title">📊 Ventas {mes_label} · % = Margen</div>',
                unsafe_allow_html=True)
    df_suc = cargar_ventas_sucursal_mes()
    if not df_suc.empty:
        fig = grafico_ventas_sucursal(df_suc)
        if fig:
            st.plotly_chart(fig, key="panel_suc",
                            width="stretch",
                            config={"displayModeBar":False})

    # Utilidad diaria
    st.markdown(f'<div class="panel-title">📈 Utilidad Diaria · {mes_label}</div>',
                unsafe_allow_html=True)
    df_util = cargar_utilidad_diaria()
    if not df_util.empty:
        fig = grafico_utilidad_diaria(df_util)
        if fig:
            st.plotly_chart(fig, key="panel_util",
                            width="stretch",
                            config={"displayModeBar":False})

    # Utilidad mensual comparativa
    st.markdown('<div class="panel-title">📊 Utilidad Mensual 2024 · 2025 · 2026</div>',
                unsafe_allow_html=True)
    df_mens = cargar_utilidad_mensual()
    if not df_mens.empty:
        fig = grafico_utilidad_mensual(df_mens)
        if fig:
            st.plotly_chart(fig, key="panel_mens",
                            width="stretch",
                            config={"displayModeBar":False})


# ─── FOOTER PROFESIONAL ───────────────────────────────────────
st.markdown("""
<style>
.footer-cucher{
    margin-top:32px;padding:18px 24px;
    border-top:1px solid #e8d5a3;
    text-align:center;
}
.footer-cucher .name{font-size:0.85rem;font-weight:700;color:#1a2744;}
.footer-cucher .role{font-size:0.72rem;color:#6b7280;margin-top:2px;}
.footer-cucher .links{font-size:0.72rem;margin-top:8px;}
.footer-cucher .links a{color:#1a2744;text-decoration:none;margin:0 10px;font-weight:600;}
.footer-cucher .links a:hover{color:#d97706;text-decoration:underline;}
.footer-cucher .copy{font-size:0.68rem;color:#9ca3af;margin-top:10px;}
</style>
<div class="footer-cucher">
  <div class="name">🛒 Cucher Agente BI</div>
  <div class="role">Desarrollado por Julio Alberto Lazarte — Data Scientist · BI Lead</div>
  <div class="links">
    <a href="https://juliolaz.github.io" target="_blank">🌐 Portfolio</a>
    <a href="https://www.linkedin.com/in/juliolazarte" target="_blank">💼 LinkedIn</a>
  </div>
  <div class="copy">© 2026 Julio Alberto Lazarte. Todos los derechos reservados.</div>
</div>
""", unsafe_allow_html=True)