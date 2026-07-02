"""
exportar_excel.py — Generación de archivos Excel con formato profesional
para los detalles de alertas del agente Cucher BI.

Reglas de formato aplicadas:
  - Primera fila (encabezados) inmovilizada y con color tenue de fondo.
  - Ancho de columna ajustado al contenido máximo de cada una.
  - Orden descendente por presupuesto_compra (ya viene ordenado desde SQL).
  - presupuesto_compra formateado con separador de miles.
  - Bloques de columnas (texto, stock, abastecer, ventas/$) con color
    de fondo tenue distinto por grupo, para lectura rápida.
"""
import io
import pandas as pd

# Paleta de colores tenues por tipo de columna
_COLOR_TEXTO     = "#EAF1FB"   # descripcion, familia, subfamilia, proveedor
_COLOR_STOCK     = "#FFF6E5"   # stk_*, stock_total
_COLOR_ABASTECER = "#E9F8EF"   # *_abastecer
_COLOR_NUM       = "#F3EAFB"   # ventas, dias_cobertura, uxb, exceso, perdido
_COLOR_MONEY     = "#FDEAEA"   # presupuesto_compra, valor_perdido

# Colores de accion_sugerida se aplican dinámicamente por valor
_COLOR_ACCION = {
    "🔴 Comprar ya":         "#FFD7D7",
    "🟠 OC próximos días":   "#FFE8CC",
    "🟡 Monitorear":         "#FFF8CC",
    "🟢 Sin urgencia":       "#D7F5D7",
}

_GRUPOS = {
    "indice_urgencia": _COLOR_MONEY, "accion_sugerida": _COLOR_MONEY,
    "descripcion": _COLOR_TEXTO, "familia": _COLOR_TEXTO,
    "subfamilia": _COLOR_TEXTO, "proveedor": _COLOR_TEXTO,

    "stk_hiper": _COLOR_STOCK, "stk_corrientes": _COLOR_STOCK,
    "stk_sabin": _COLOR_STOCK, "stk_formosa": _COLOR_STOCK,
    "stk_express": _COLOR_STOCK, "stk_tirol": _COLOR_STOCK,
    "stk_central": _COLOR_STOCK, "stock_total": _COLOR_STOCK,

    "cor_abastecer": _COLOR_ABASTECER, "exp_abastecer": _COLOR_ABASTECER,
    "for_abastecer": _COLOR_ABASTECER, "sab_abastecer": _COLOR_ABASTECER,
    "hip_abastecer": _COLOR_ABASTECER, "total_abastecer": _COLOR_ABASTECER,

    "dias_cobertura": _COLOR_NUM, "uxb": _COLOR_NUM,
    "ventas_90d": _COLOR_NUM, "exceso_stock": _COLOR_NUM,
    "unidades_perdidas": _COLOR_NUM,

    "presupuesto_compra": _COLOR_MONEY, "valor_perdido": _COLOR_MONEY,
}

_COLOR_DEFAULT = "#F2F2F2"

# Columnas que llevan formato de miles ($ separado por punto)
_COLS_MILES = {"presupuesto_compra", "valor_perdido"}


def generar_excel_detalle(df: pd.DataFrame, nombre_hoja: str = "Detalle") -> io.BytesIO:
    """
    Genera un buffer .xlsx con formato profesional a partir de un DataFrame.
    - Encabezado inmovilizado con color tenue.
    - Columnas agrupadas por tipo de dato con color de fondo distinto.
    - presupuesto_compra / valor_perdido con separador de miles.
    - Ancho de columna ajustado al contenido.
    - Mantiene el orden de filas recibido (ya viene DESC por presupuesto).
    """
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        sheet_name = nombre_hoja[:31] if nombre_hoja else "Detalle"
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=0)

        workbook  = writer.book
        worksheet = writer.sheets[sheet_name]

        # ── Formato base de encabezado ──
        fmt_header_base = {
            "bold": True, "valign": "vcenter", "align": "center",
            "border": 1, "border_color": "#D9D9D9",
            "text_wrap": True,
        }

        # ── Formatos de celda por grupo (cuerpo) ──
        fmt_body_cache = {}

        def _get_body_format(color: str, es_miles: bool = False):
            cache_key = (color, es_miles)
            if cache_key not in fmt_body_cache:
                props = {"bg_color": color, "border": 1, "border_color": "#E5E5E5"}
                if es_miles:
                    props["num_format"] = "#,##0"
                fmt_body_cache[cache_key] = workbook.add_format(props)
            return fmt_body_cache[cache_key]

        def _get_header_format(color: str):
            key = ("header", color)
            if key not in fmt_body_cache:
                props = dict(fmt_header_base)
                props["bg_color"] = color
                fmt_body_cache[key] = workbook.add_format(props)
            return fmt_body_cache[key]

        # ── Escribir encabezados con color por grupo + recalcular ancho ──
        for col_idx, col_name in enumerate(df.columns):
            color = _GRUPOS.get(col_name, _COLOR_DEFAULT)
            header_fmt = _get_header_format(color)
            worksheet.write(0, col_idx, col_name, header_fmt)

            es_miles = col_name in _COLS_MILES
            body_fmt = _get_body_format(color, es_miles)

            # Reescribir la columna completa con su formato de cuerpo
            serie = df[col_name]
            for row_idx, valor in enumerate(serie, start=1):
                if pd.isna(valor):
                    worksheet.write_blank(row_idx, col_idx, None, body_fmt)
                elif col_name == "accion_sugerida" and isinstance(valor, str):
                    # Color dinámico según el nivel de urgencia
                    color_acc = _COLOR_ACCION.get(valor, _COLOR_MONEY)
                    fmt_acc = workbook.add_format({
                        "bg_color": color_acc, "border": 1,
                        "border_color": "#E5E5E5", "bold": True
                    })
                    worksheet.write(row_idx, col_idx, valor, fmt_acc)
                else:
                    worksheet.write(row_idx, col_idx, valor, body_fmt)

            # Ancho de columna = máximo entre header y contenido (+ margen)
            try:
                max_contenido = serie.astype(str).map(len).max()
            except Exception:
                max_contenido = 10
            max_contenido = 0 if pd.isna(max_contenido) else max_contenido
            ancho = max(len(str(col_name)), int(max_contenido)) + 3
            ancho = min(ancho, 45)  # tope razonable
            worksheet.set_column(col_idx, col_idx, ancho)

        # ── Inmovilizar primera fila ──
        worksheet.freeze_panes(1, 0)

        # ── Autofiltro en el encabezado ──
        n_filas = len(df)
        n_cols  = len(df.columns) - 1
        if n_filas > 0:
            worksheet.autofilter(0, 0, n_filas, n_cols)

    buffer.seek(0)
    return buffer