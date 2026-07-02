"""
enriquecedor.py — Pre-procesamiento de la pregunta en Python puro.
Detecta categorías, marcas, medidas, rangos y sucursales
SIN llamar al LLM. Devuelve hints estructurados para el procesador.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from catalogo import (CATEGORIAS, SINONIMO_A_CATEGORIA, MARCA_A_CATEGORIA,
                      UNIDADES_VOLUMEN, UNIDADES_PESO)
from config import SUC_VENTAS, SUC_DEPOSITOS, SUC_ESPECIAL


@dataclass
class Contexto:
    """Contexto extraído de la pregunta por Python puro."""
    # Categoría detectada
    categoria_key:  Optional[str] = None   # ej: "cervezas"
    subfamilia:     Optional[str] = None   # ej: "Cervezas"
    familia:        Optional[str] = None   # ej: "Bebidas"

    # Marcas detectadas
    marcas:         list[str] = field(default_factory=list)

    # Medidas
    medida_str:     Optional[str] = None   # ej: "1 kg"
    medida_tipo:    Optional[str] = None   # ej: "kg"

    # Rango de tamaño (para "más de 900cc")
    rango_min_cc:   Optional[int] = None
    rango_max_cc:   Optional[int] = None
    rango_min_g:    Optional[int] = None
    rango_max_g:    Optional[int] = None

    # Sucursales
    sucursales:     list[str] = field(default_factory=list)

    # Intención
    pide_precio:    bool = False
    pide_ranking:   bool = False
    pide_stock:     bool = False
    pide_alerta:    bool = False
    pide_estacion:  bool = False

    # Top N
    top_n:          int = 10

    # Período
    fecha_desde:    Optional[str] = None
    fecha_hasta:    Optional[str] = None

    # Texto libre residual para el LLM
    texto_libre:    str = ""
    proveedor_nombre: str = ""  # nombre de proveedor detectado en la pregunta


def enriquecer(pregunta: str) -> Contexto:
    """
    Analiza la pregunta y devuelve un Contexto con todo lo detectado.
    Python puro — sin LLM.
    """
    ctx = Contexto()
    p   = pregunta.lower().strip()
    ctx.texto_libre = pregunta

    # ── 1. CATEGORÍA ─────────────────────────────────────────
    import re as _re2

    # Primero buscar frases compuestas (más específicas) para evitar
    # que "alimentos" en "alimentos para mascotas" gane antes que "mascotas"
    # Ordenar sinónimos de más largo a más corto para que las frases
    # específicas ganen sobre las palabras genéricas
    sinonimos_ordenados = sorted(
        SINONIMO_A_CATEGORIA.items(),
        key=lambda x: len(x[0]),
        reverse=True  # más largo primero = más específico
    )
    for sinonimo, cat_key in sinonimos_ordenados:
        if _re2.search(r'\b' + _re2.escape(sinonimo) + r'\b', p):
            ctx.categoria_key = cat_key
            cat = CATEGORIAS[cat_key]
            ctx.subfamilia = cat["subfamilia"]
            ctx.familia    = cat["familia"]
            break

    # ── 2. MARCAS ────────────────────────────────────────────
    cat_data = CATEGORIAS.get(ctx.categoria_key, {}) if ctx.categoria_key else {}
    todas_las_marcas = cat_data.get("marcas", [])
    # También chequear marcas de otras categorías si no hubo match de categoría
    if not ctx.categoria_key:
        from itertools import chain
        todas_las_marcas = list(set(
            m for c in CATEGORIAS.values() for m in c.get("marcas", [])
        ))
    ctx.marcas = [m for m in todas_las_marcas if m in p]

    # ── 3. MEDIDAS SIMPLES ────────────────────────────────────
    medidas_cat = cat_data.get("medidas", {})
    for tipo, variantes in medidas_cat.items():
        for v in variantes:
            if v in p:
                ctx.medida_str  = v
                ctx.medida_tipo = tipo
                break
        if ctx.medida_str:
            break

    # ── 4. RANGO DE VOLUMEN (más de X cc / menos de X ml) ────
    # Patrones: "más de 900cc", "mayor a 1 litro", "menos de 500ml"
    patron_mayor = r'(m[aá]s\s*de|mayor\s*(a|que)|superior\s*(a|que))\s*(\d+[\.,]?\d*)\s*(cc|ml|l|litro|litros)'
    patron_menor = r'(m[ae]nos\s*de|menor\s*(a|que)|inferior\s*(a|que))\s*(\d+[\.,]?\d*)\s*(cc|ml|l|litro|litros)'

    m_mayor = re.search(patron_mayor, p)
    m_menor = re.search(patron_menor, p)

    if m_mayor:
        valor = float(m_mayor.group(4).replace(",", "."))
        unidad = m_mayor.group(5)
        factor = UNIDADES_VOLUMEN.get(unidad, 1)
        ctx.rango_min_cc = int(valor * factor)

    if m_menor:
        valor = float(m_menor.group(4).replace(",", "."))
        unidad = m_menor.group(5)
        factor = UNIDADES_VOLUMEN.get(unidad, 1)
        ctx.rango_max_cc = int(valor * factor)

    # Rango de peso
    patron_mayor_g = r'(m[aá]s\s*de|mayor\s*(a|que))\s*(\d+[\.,]?\d*)\s*(g|gr|kg|kilo|kilos|gramos)'
    patron_menor_g = r'(m[ae]nos\s*de|menor\s*(a|que))\s*(\d+[\.,]?\d*)\s*(g|gr|kg|kilo|kilos|gramos)'

    m_mayor_g = re.search(patron_mayor_g, p)
    m_menor_g = re.search(patron_menor_g, p)

    if m_mayor_g:
        valor  = float(m_mayor_g.group(3).replace(",", "."))
        unidad = m_mayor_g.group(4)
        factor = UNIDADES_PESO.get(unidad, 1)
        ctx.rango_min_g = int(valor * factor)

    if m_menor_g:
        valor  = float(m_menor_g.group(3).replace(",", "."))
        unidad = m_menor_g.group(4)
        factor = UNIDADES_PESO.get(unidad, 1)
        ctx.rango_max_g = int(valor * factor)

    # ── 5. SUCURSALES ─────────────────────────────────────────
    for suc in SUC_VENTAS + SUC_DEPOSITOS + SUC_ESPECIAL:
        if suc in p:
            ctx.sucursales.append(suc)

    # ── 6. INTENCIÓN ─────────────────────────────────────────
    ctx.pide_precio  = any(x in p for x in [
        "precio compra", "precio de compra", "precios de compra", "precios a proveedor",
        "precio proveedor", "cuanto cuesta", "cuánto cuesta", "cuanto sale",
        "precio oc", "ultima oc", "último precio", "ultimo precio", "oc"])

    ctx.pide_ranking = any(x in p for x in [
        "mas vendido", "más vendido", "mayor venta", "top", "ranking",
        "mas vendida", "más vendida", "mejor vendido", "mayor cantidad",
        "mas unidades", "más unidades"])

    ctx.pide_stock   = any(x in p for x in [
        "stock", "quiebre", "cobertura", "dias cobertura", "días cobertura",
        "faltante", "disponibilidad", "clasificar", "clasificacion",
        "clasificación", "necesitan stock", "bajo stock", "sin stock",
        "riesgo", "riesgo de quiebre", "pueden faltar", "van a faltar",
        "quiebre de stock", "reposicion", "reposición", "reabastecer"])

    ctx.pide_alerta  = any(x in p for x in [
        "alerta", "alertas", "critico", "crítico", "reponer", "reabastecer",
        "reposicion", "reposición", "quiebre", "falta", "faltan",
        "clasificar critico", "clasificar crítico", "productos criticos",
        "productos críticos", "criticos segun", "críticos según"])

    ctx.pide_estacion = any(x in p for x in [
        "estacion", "estación", "temporada", "temporada", "estacional",
        "invierno", "verano", "otoño", "primavera", "mejor momento"])

    # ── 7. TOP N ─────────────────────────────────────────────
    match_n = re.search(r'\b(\d+)\b', p)
    if match_n:
        n = int(match_n.group(1))
        if 2 <= n <= 50:
            ctx.top_n = n

    # ── 8. PERÍODO ───────────────────────────────────────────
    from datetime import date, timedelta
    hoy = date.today()

    if "hoy" in p:
        ctx.fecha_desde = ctx.fecha_hasta = str(hoy)
    elif "esta semana" in p:
        ctx.fecha_desde = str(hoy - timedelta(days=7))
        ctx.fecha_hasta = str(hoy)
    elif "este mes" in p or "mes actual" in p:
        ctx.fecha_desde = str(hoy.replace(day=1))
        ctx.fecha_hasta = str(hoy)
    elif "ultimo mes" in p or "último mes" in p:
        ctx.fecha_desde = str(hoy - timedelta(days=30))
        ctx.fecha_hasta = str(hoy)
    elif "ultimos 90" in p or "últimos 90" in p or "90 dias" in p:
        ctx.fecha_desde = str(hoy - timedelta(days=90))
        ctx.fecha_hasta = str(hoy)
    elif "2026" in p and "mayo" in p:
        ctx.fecha_desde = "2026-05-01"
        ctx.fecha_hasta = str(hoy)
    elif "junio" in p and "2026" in p:
        ctx.fecha_desde = "2026-06-01"
        ctx.fecha_hasta = str(hoy)
    elif "mayo" in p:
        ctx.fecha_desde = f"{hoy.year}-05-01"
        ctx.fecha_hasta = str(hoy)
    elif "desde apertura" in p or "apertura sabin" in p:
        ctx.fecha_desde = "2026-06-06"
        ctx.fecha_hasta = str(hoy)

    return ctx


def construir_hint(ctx: Contexto) -> str:
    """Convierte el Contexto en un string de hint para el LLM."""
    hints = []

    if ctx.subfamilia:
        hints.append(
            f"subfamilia exacta='{ctx.subfamilia}' → "
            f"filtrar: LOWER(subfamilia) LIKE '%{ctx.subfamilia}%'"
        )

    if ctx.marcas:
        filtro_marcas = " OR ".join(
            f"LOWER(descripcion) LIKE '%{m}%'" for m in ctx.marcas
        )
        hints.append(f"marcas detectadas: {ctx.marcas} → ({filtro_marcas})")

    if ctx.medida_str:
        hints.append(
            f"medida='{ctx.medida_str}' → "
            f"LOWER(descripcion) LIKE '%{ctx.medida_str}%'"
        )

    if ctx.rango_min_cc:
        variantes = _variantes_volumen_mayor(ctx.rango_min_cc)
        hints.append(
            f"volumen > {ctx.rango_min_cc}cc → "
            f"buscar en descripcion: ({' OR '.join(variantes)})"
        )

    if ctx.rango_max_cc:
        variantes = _variantes_volumen_menor(ctx.rango_max_cc)
        hints.append(
            f"volumen < {ctx.rango_max_cc}cc → "
            f"buscar en descripcion: ({' OR '.join(variantes)})"
        )

    if ctx.rango_min_g:
        variantes = _variantes_peso_mayor(ctx.rango_min_g)
        hints.append(
            f"peso > {ctx.rango_min_g}g → "
            f"buscar en descripcion: ({' OR '.join(variantes)})"
        )

    if ctx.sucursales:
        hints.append(
            f"sucursales: {ctx.sucursales} → "
            f"LOWER(sucursal) IN ({', '.join(repr(s) for s in ctx.sucursales)})"
        )

    if ctx.fecha_desde:
        hints.append(
            f"período: {ctx.fecha_desde} → {ctx.fecha_hasta} → "
            f"CAST(fecha_comprobante AS DATE) BETWEEN '{ctx.fecha_desde}' AND '{ctx.fecha_hasta}'"
        )

    if not hints:
        return ""
    return " [HINTS PYTHON: " + " | ".join(hints) + "]"


def _variantes_volumen_mayor(min_cc: int) -> list[str]:
    """Genera variantes de descripcion para volumen mayor a X cc."""
    variantes = []
    for cc, labels in [
        (940,  ["940", "940cc", "940 cc"]),
        (960,  ["960", "960cc"]),
        (1000, ["1000", "1000cc", "1l", "1 l", "1000ml", "litro"]),
        (1500, ["1.5l", "1.5 l", "1500"]),
        (2000, ["2l", "2 l", "2000"]),
        (3000, ["3l", "3 l"]),
    ]:
        if cc >= min_cc:
            variantes.extend(
                f"LOWER(descripcion) LIKE '%{lbl}%'" for lbl in labels
            )
    return variantes or [f"LOWER(descripcion) LIKE '%{min_cc}%'"]


def _variantes_volumen_menor(max_cc: int) -> list[str]:
    """Genera variantes de descripcion para volumen menor a X cc."""
    variantes = []
    for cc, labels in [
        (220,  ["220", "220cc"]),
        (250,  ["250", "250cc"]),
        (330,  ["330", "330cc"]),
        (354,  ["354", "354cc"]),
        (355,  ["355", "355cc"]),
        (473,  ["473", "473cc"]),
    ]:
        if cc < max_cc:
            variantes.extend(
                f"LOWER(descripcion) LIKE '%{lbl}%'" for lbl in labels
            )
    return variantes or [f"LOWER(descripcion) LIKE '%{max_cc}%'"]


def _variantes_peso_mayor(min_g: int) -> list[str]:
    variantes = []
    for g, labels in [
        (500,  ["500g", "500 g", "x500"]),
        (1000, ["1kg", "1 kg", "x1kg", "1000g"]),
        (2000, ["2kg", "2 kg"]),
    ]:
        if g >= min_g:
            variantes.extend(
                f"LOWER(descripcion) LIKE '%{lbl}%'" for lbl in labels
            )
    return variantes or [f"LOWER(descripcion) LIKE '%{min_g}g%'"]