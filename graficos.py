"""
graficos.py — Generación automática de gráficos Plotly según el tipo de resultado.
Detecta el tipo de DataFrame y elige el gráfico más apropiado.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import COLORES_SUC


def grafico_auto(df: pd.DataFrame, pregunta: str = "") -> go.Figure | None:
    """
    Genera el gráfico más apropiado para el DataFrame recibido.
    Prioridad:
      1. Precio de compra → barras horizontales (rojo=caro, verde=barato)
      2. Comparación por sucursal → barras verticales con colores
      3. Tendencia temporal pura (sin descripcion) → línea
      4. Ranking por descripcion/proveedor → barras horizontales
      5. Scatter margen vs ventas → scatter
    """
    if df is None or df.empty or len(df) < 2:
        return None

    try:
        cols    = [c.lower() for c in df.columns]
        col_map = {c.lower(): c for c in df.columns}  # lowercase → original

        # ── 1. PRECIO DE COMPRA ──────────────────────────────
        col_precio = _buscar_col(cols, ["precio_compra", "ultimo_precio", "precio_unit"])
        col_desc   = _buscar_col(cols, ["descripcion", "articulo"])

        if col_precio and col_desc:
            col_p = col_map[col_precio]
            col_d = col_map[col_desc]
            df_p  = df.head(20).copy()
            df_p["_label"] = df_p[col_d].astype(str).str.strip().str[:40]

            max_v = df_p[col_p].max()
            min_v = df_p[col_p].min()
            colores = [
                "#dc2626" if v == max_v else
                "#16a34a" if v == min_v else
                "#3b82f6"
                for v in df_p[col_p]
            ]

            fig = go.Figure(go.Bar(
                x=df_p[col_p],
                y=df_p["_label"],
                orientation="h",
                marker_color=colores,
                text=[f"${v:,.0f}" for v in df_p[col_p]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Precio: $%{x:,.0f}<extra></extra>"
            ))
            fig.update_layout(
                title="💰 Precio de Compra por Artículo",
                yaxis=dict(autorange="reversed"),
                xaxis_title="$ Precio de Compra",
                showlegend=False,
            )
            return fig

        # ── 2. COMPARACIÓN POR SUCURSAL ──────────────────────
        if "sucursal" in cols:
            col_v = _buscar_col(cols, ["ventas", "total", "utilidad", "monto", "unidades"])
            if col_v:
                col_val = col_map[col_v]
                colores = [
                    COLORES_SUC.get(str(s).lower(), "#3b82f6")
                    for s in df["sucursal"]
                ]
                fig = go.Figure(go.Bar(
                    x=df["sucursal"], y=df[col_val],
                    marker_color=colores,
                    text=[f"${v:,.0f}" if v > 1000 else str(int(v))
                          for v in df[col_val]],
                    textposition="outside"
                ))
                fig.update_layout(
                    title=col_val.replace("_", " ").title(),
                    showlegend=False,
                    xaxis_title="Sucursal",
                )
                return fig

        # ── 3. TENDENCIA TEMPORAL (SIN descripcion) ──────────
        col_fecha = _buscar_col(cols, ["fecha"])
        if col_fecha and not col_desc:
            col_v = _buscar_col(cols, ["ventas", "utilidad", "precio", "total",
                                        "monto", "unidades", "cantidad"])
            if col_v:
                col_f   = col_map[col_fecha]
                col_val = col_map[col_v]
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df[col_f], y=df[col_val],
                    mode="lines+markers",
                    line=dict(color="#3b82f6", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(59,130,246,0.1)",
                    hovertemplate="Fecha: %{x}<br>Valor: $%{y:,.0f}<extra></extra>"
                ))
                fig.update_layout(
                    title=col_val.replace("_", " ").title(),
                    xaxis_title="Fecha",
                )
                return fig

        # ── 4. RANKING HORIZONTAL (descripcion + valor) ──────
        if col_desc:
            col_v = _buscar_col(cols, ["ventas", "total", "utilidad", "unidades",
                                        "cantidad", "monto", "precio", "margen",
                                        "cobertura", "pct"])
            if col_v:
                col_d   = col_map[col_desc]
                col_val = col_map[col_v]
                df_p    = df.head(20).copy()
                df_p["_label"] = df_p[col_d].astype(str).str.strip().str[:35]

                # Color por margen si existe
                if "margen" in col_v:
                    colores_rank = [
                        "#dc2626" if v < 0 else
                        "#f97316" if v < 10 else
                        "#16a34a"
                        for v in df_p[col_val]
                    ]
                else:
                    colores_rank = "#3b82f6"

                fig = px.bar(
                    df_p, x=col_val, y="_label", orientation="h",
                    title=col_val.replace("_", " ").title(),
                    color_discrete_sequence=["#3b82f6"]
                )
                if isinstance(colores_rank, list):
                    fig.update_traces(marker_color=colores_rank)
                fig.update_layout(
                    yaxis=dict(autorange="reversed", title=""),
                    xaxis_title=col_val.replace("_", " "),
                )
                return fig

        # ── 5. SCATTER MARGEN vs VENTAS ──────────────────────
        col_x = _buscar_col(cols, ["margen"])
        col_y = _buscar_col(cols, ["ventas", "total"])
        if col_x and col_y:
            hover = [c for c in df.columns if "desc" in c.lower()]
            fig = px.scatter(
                df.head(50),
                x=col_map[col_x], y=col_map[col_y],
                hover_data=hover if hover else None,
                title="Margen vs Ventas",
                color_discrete_sequence=["#3b82f6"]
            )
            return fig

    except Exception as e:
        print(f"   [graficos] Error: {e}")

    return None


def _buscar_col(cols: list[str], terminos: list[str]) -> str | None:
    """Busca la primera columna que contenga alguno de los términos."""
    for termino in terminos:
        for col in cols:
            if termino in col:
                return col
    return None


# ─── GRÁFICOS DEL PANEL FIJO ─────────────────────────────────

def grafico_ventas_sucursal(df: pd.DataFrame) -> go.Figure | None:
    """Barras de ventas del mes por sucursal."""
    if df is None or df.empty:
        return None
    fig = go.Figure()
    for _, row in df.iterrows():
        color = COLORES_SUC.get(str(row["sucursal"]).lower(), "#3b82f6")
        fig.add_trace(go.Bar(
            name=row["sucursal"],
            x=[row["sucursal"]],
            y=[row["ventas_m"]],
            marker_color=color,
            text=[f"${row['ventas_m']:.1f}M<br>{row['margen_pct']}%"],
            textposition="outside"
        ))
    fig.update_layout(showlegend=False, height=220,
                      margin=dict(l=0,r=0,t=10,b=0),
                      plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#e2e8f0", size=10),
                      yaxis=dict(showgrid=False, showticklabels=False),
                      xaxis=dict(showgrid=False))
    return fig


def grafico_utilidad_diaria(df: pd.DataFrame) -> go.Figure | None:
    """Barras de utilidad diaria del mes."""
    if df is None or df.empty:
        return None
    promedio = df["utilidad_m"].mean()
    colores  = ["#f97316" if v >= promedio else "#3b82f6"
                for v in df["utilidad_m"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["fecha"].astype(str).str[-2:],
        y=df["utilidad_m"],
        marker_color=colores,
        text=[f"${v:.0f}M" for v in df["utilidad_m"]],
        textposition="outside",
        textfont=dict(size=7)
    ))
    fig.add_hline(y=promedio, line_dash="dot",
                  line_color="#d97706", line_width=1.5)
    fig.update_layout(showlegend=False, height=200,
                      margin=dict(l=0,r=0,t=10,b=0),
                      plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#e2e8f0", size=9),
                      yaxis=dict(showgrid=False, showticklabels=False),
                      xaxis=dict(showgrid=False,
                                 title=dict(text="día",
                                            font=dict(color="#e2e8f0"))))
    return fig


def grafico_utilidad_mensual(df: pd.DataFrame) -> go.Figure | None:
    """Barras agrupadas de utilidad mensual 2024/2025/2026."""
    if df is None or df.empty:
        return None
    MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
              7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
    COLORES_ANIO = {2024:"#3b82f6", 2025:"#22c55e", 2026:"#f97316"}
    fig = go.Figure()
    for anio in sorted(df["anio"].unique()):
        df_a = df[df["anio"] == anio].copy()
        df_a["mes_nom"] = df_a["mes"].map(MESES)
        fig.add_trace(go.Bar(
            name=str(int(anio)),
            x=df_a["mes_nom"],
            y=df_a["utilidad_m"],
            marker_color=COLORES_ANIO.get(int(anio), "#94a3b8"),
            text=[f"{v:.2f}M" for v in df_a["utilidad_m"]],
            textposition="outside",
            textfont=dict(size=7),
        ))
    fig.update_layout(
        barmode="group", height=280,
        margin=dict(l=0,r=0,t=10,b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", size=9),
        legend=dict(orientation="h", y=1.08, x=0,
                    font=dict(size=9, color="#e2e8f0"),
                    bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(showgrid=True, gridcolor="#2e4a7a",
                   showticklabels=False, zeroline=False),
        xaxis=dict(showgrid=False),
    )
    return fig
