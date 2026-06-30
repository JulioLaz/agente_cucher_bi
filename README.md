# 🛒 Cucher Agente BI

Agente conversacional de Business Intelligence para **Cucher Mercados**, una cadena de supermercados con sucursales en Chaco, Corrientes y Formosa (Argentina). Permite consultar ventas, stock, precios de compra y alertas de reabastecimiento en lenguaje natural, con respuestas respaldadas por datos reales en tiempo real.

🔗 **App en producción:** [agentecucherbi.streamlit.app](https://agentecucherbi-j9hzzxdnw7oegxc8ixr2ce.streamlit.app)

---

## ✨ Características

- **Chat en lenguaje natural** — preguntá sobre ventas, stock, precios o proveedores sin escribir SQL.
- **Metacognición** — el agente confirma cómo interpretó tu pregunta antes de ejecutarla, y avisa cuando algo está fuera de su alcance actual (notificando al equipo por Telegram).
- **Arquitectura híbrida** — combina *templates* SQL pre-verificados (respuesta en segundos) con generación de SQL libre vía LLM para consultas complejas o nuevas.
- **Catálogo real embebido** — 363 combinaciones familia/subfamilia y +150 marcas mapeadas directamente desde los datos de Cucher, evitando que el modelo "adivine" categorías.
- **Tarjetas de alerta interactivas** — KPIs de stock crítico, exceso de stock, valor perdido por quiebres y presupuesto de compra, con detalle descargable en Excel con un clic.
- **Multiusuario con login** — acceso restringido vía Streamlit Secrets (sin credenciales en el código).
- **Notificaciones a Telegram** — cada consulta y cada capacidad faltante quedan registradas para seguimiento del equipo.

---

## 🏗️ Arquitectura

```
agente_cucher_bi/
├── app.py             # UI Streamlit — login, KPIs, chat, panel lateral
├── config.py          # Constantes y lectura de secrets (runtime, sin hardcodeo)
├── catalogo.py         # Familias/subfamilias/marcas reales + sinónimos
├── conexion.py         # Conexión a MotherDuck (singleton)
├── enriquecedor.py     # Pre-procesamiento NLP en Python puro (sin LLM)
├── templates.py        # Queries SQL pre-verificadas para consultas frecuentes
├── ejecutor.py          # Ejecución SQL segura (whitelist, validación)
├── llm.py               # Llamadas a NVIDIA NIM con fallback entre modelos
├── interprete.py        # Metacognición: qué puede/no puede responder el agente
├── procesador.py        # Orquesta: enriquecer → template → LLM → retry → análisis
├── graficos.py          # Generación automática de visualizaciones Plotly
├── kpis.py               # KPIs de header, panel lateral y detalle de alertas
├── notificaciones.py     # Telegram + historial local
└── requirements.txt
```

### Flujo de una consulta

```
Pregunta del usuario
        │
        ▼
 Interpretación (LLM liviano) → ¿puede responder? → confirmación del usuario
        │
        ▼
 Enriquecimiento (Python puro: categoría, marca, medida, período, sucursal)
        │
        ▼
 ¿Coincide con un template verificado? ──Sí──► Ejecuta SQL pre-armado (⚡ rápido)
        │No
        ▼
 LLM genera SQL libre → ejecuta → si falla, reintenta con el error
        │
        ▼
 LLM analiza el resultado → respuesta en lenguaje natural + gráfico automático
```

---

## 🗄️ Fuentes de datos (MotherDuck)

| Tabla | Contenido |
|---|---|
| `tickets_all` | ~5,6M registros de ventas históricas (2024–2026) |
| `proveedores` | Catálogo de artículos, stock por sucursal y proveedor |
| `result_final_alert_all` | Alertas de stock, riesgo, estacionalidad, presupuesto de compra |
| `ultimos_precios` | Último precio de compra (OC) por artículo |

---

## ⚙️ Stack técnico

- **Frontend / runtime:** Streamlit
- **Base de datos:** DuckDB + MotherDuck
- **LLM:** NVIDIA NIM (Mistral, DeepSeek, GLM, Llama como fallback en cascada)
- **Visualización:** Plotly
- **Notificaciones:** Telegram Bot API
- **Exportación:** XlsxWriter

---

## 🔐 Configuración de secretos

La app no contiene credenciales en el código. En **Streamlit Cloud → Settings → Secrets**:

```toml
TOKEN_MATHERDUCK   = "..."
key_nvidia         = "..."
token_bot_telegram = "..."

[usuarios]
cristina = "..."
horacio  = "..."
julio    = "..."
```

Para desarrollo local, copiar `secrets.toml.example` a `.streamlit/secrets.toml` (excluido de git vía `.gitignore`).

---

## 🚀 Ejecutar localmente

```bash
git clone https://github.com/JulioLaz/agente_cucher_bi.git
cd agente_cucher_bi
pip install -r requirements.txt
streamlit run app.py
```

---

## 👤 Autor

**Julio Alberto Lazarte**
Data Scientist · BI Lead

🌐 [Portfolio](https://juliolaz.github.io) · 💼 [LinkedIn](https://www.linkedin.com/in/juliolazarte)

© 2026 Julio Alberto Lazarte. Todos los derechos reservados.

###  CORRER EL COD EN LOCAL:

C:\JulioPrograma\CUCHER-MERCADOS\cuchermercados-main\cuchermercados-main\.venv\Scripts\Activate.ps1

cd C:\JulioPrograma\AGENTE_CUCHER_DASHBOARD
streamlit run app.py

"""
    <a href="https://juliolaz.github.io" target="_blank">🌐 Portfolio</a>
    <a href="https://www.linkedin.com/in/juliolazarte" target="_blank">💼 LinkedIn</a>
"""
