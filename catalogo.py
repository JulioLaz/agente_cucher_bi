"""
catalogo.py — Catálogo de categorías, marcas, medidas y sinónimos.
Fuente de verdad para el enriquecedor — sin LLM, Python puro.
Verificado contra my_db.tickets_all y my_db.proveedores de Cucher.
"""

# ─── CATEGORÍAS CON SUBFAMILIA EXACTA Y SINÓNIMOS ────────────
CATEGORIAS = {
    "cervezas": {
        "subfamilia": "Cervezas",
        "familia":    "Bebidas",
        "sinonimos":  ["cerveza", "cervezas", "birra", "beer"],
        "marcas":     ["quilmes", "schneider", "andes", "brahma", "isenbeck",
                       "heineken", "corona", "stella", "budweiser", "imperial",
                       "miller", "fernet", "branca", "michelob", "patagonia"],
        "medidas": {
            "grande":   ["940", "960", "1l", "1 l", "1000", "litro", "litr"],
            "personal": ["473", "354", "355", "330"],
            "chica":    ["250", "220"],
            "lata":     ["473", "lata"],
        }
    },
    "yerbas": {
        "subfamilia": "Yerbas",
        "familia":    "Alimentos",
        "sinonimos":  ["yerba", "yerbas", "mate"],
        "marcas":     ["rosamonte", "taragui", "taragüi", "playadito", "amanda",
                       "cbse", "cbsé", "canarias", "nobleza", "cachamai", "romance",
                       "la virginia", "mañanita", "cachamate", "kurupi", "union",
                       "unión", "cruz de malta", "la merced"],
        "medidas": {
            "kg":    ["1kg", "1 kg", "x1kg", "x 1kg"],
            "medio": ["500g", "500 g", "x500", "500gr"],
            "250":   ["250g", "250 g", "x250"],
            "2kg":   ["2kg", "2 kg"],
        }
    },
    "gaseosas": {
        "subfamilia": "Gaseosas",
        "familia":    "Bebidas",
        "sinonimos":  ["gaseosa", "gaseosas", "refresco", "cola", "soda"],
        "marcas":     ["coca", "pepsi", "7up", "sprite", "fanta", "manaos",
                       "cunnington", "paso de los toros", "pritty"],
        "medidas": {
            "grande":   ["2.25", "2.5", "3l", "2l", "2 l"],
            "personal": ["500", "600", "354", "473"],
            "chica":    ["237", "330"],
        }
    },
    "aguas": {
        "subfamilia": "Aguas minerales",
        "familia":    "Bebidas",
        "sinonimos":  ["agua", "aguas", "mineral"],
        "marcas":     ["villa del sur", "bonafont", "eco de los andes",
                       "glaciar", "ser", "villavicencio"],
        "medidas": {
            "grande":   ["2l", "2 l", "1.5l", "1.5 l"],
            "personal": ["500", "600"],
        }
    },
    "jugos": {
        "subfamilia": "Jugos en polvo",
        "familia":    "Bebidas",
        "sinonimos":  ["jugo", "jugos", "bebida en polvo", "polvo"],
        "marcas":     ["clight", "tang", "verao", "ades", "zuko"],
        "medidas": {}
    },
    "whisky": {
        "subfamilia": "Whisky",
        "familia":    "Bebidas",
        "sinonimos":  ["whisky", "whiskey", "whiskis", "whiskeys", "bourbon",
                       "scotch", "blend", "blended"],
        "marcas":     ["johnnie walker", "j.walker", "jack daniel", "chivas",
                       "ballantine", "old smuggler", "gloucester", "breeders",
                       "hiram walker", "doble v", "blender", "pride",
                       "white horse", "something special"],
        "medidas": {
            "litro":   ["1lt", "1l", "1000cc", "x1lt"],
            "750":     ["750cc", "750ml", "x750"],
            "700":     ["700cc", "700ml", "x700"],
        }
    },
    "vinos": {
        "subfamilia": "Vinos Finos",
        "familia":    "Bebidas",
        "sinonimos":  ["vino", "vinos", "tinto", "blanco", "rosado", "malbec"],
        "marcas":     ["norton", "trapiche", "santa julia", "finca", "navarro"],
        "medidas": {
            "botella": ["750", "375"],
            "tetrabrik": ["1l", "1 l"],
        }
    },
    "aceites": {
        "subfamilia": "Aceite de girasol",
        "familia":    "Alimentos",
        "sinonimos":  ["aceite", "aceites", "girasol", "maiz", "maíz", "oliva"],
        "marcas":     ["cocinero", "natura", "lira", "marolio", "cañuelas"],
        "medidas": {
            "litro": ["1l", "1 l", "900", "1000"],
            "medio": ["500", "450"],
        }
    },
    "leches": {
        "subfamilia": "Leches Larga Vida",
        "familia":    "Alimentos",
        "sinonimos":  ["leche", "leches", "larga vida", "uht"],
        "marcas":     ["serenísima", "sancor", "ilolay", "la serenísima",
                       "milkaut", "tremblay"],
        "medidas": {
            "litro": ["1l", "1 l", "1000"],
            "medio": ["500", "0.5l"],
        }
    },
    "cafe": {
        "subfamilia": "Café soluble",
        "familia":    "Alimentos",
        "sinonimos":  ["cafe", "café", "cafes", "cafés", "molido", "tostado",
                       "soluble", "instantaneo", "instantáneo"],
        "marcas":     ["la virginia", "nescafe", "nestle", "dolca", "cabrales",
                       "lm", "torrado"],
        "medidas": {
            "kg":    ["1kg", "1 kg", "x1kg"],
            "medio": ["500g", "500 g", "x500"],
            "chico": ["200g", "100g", "50g"],
        }
    },
    "quesos": {
        "subfamilia": "Quesos",
        "familia":    "Frescos",
        "sinonimos":  ["queso", "quesos", "cremoso", "cuartirolo", "reggianito",
                       "parmesano", "barra", "horma"],
        "marcas":     ["iloyal", "tremblay", "sancor", "la serenísima"],
        "medidas": {}
    },
    "carnes": {
        "subfamilia": "Carnes",
        "familia":    "Frescos",
        "sinonimos":  ["carne", "carnes", "vacuno", "novillo", "ternera",
                       "asado", "costilla", "bife", "cuadril", "nalga"],
        "marcas":     [],
        "medidas": {}
    },
    "harinas": {
        "subfamilia": "Harinas",
        "familia":    "Alimentos",
        "sinonimos":  ["harina", "harinas", "0000", "000", "integral", "leudante"],
        "marcas":     ["blancaflor", "cañuelas", "pureza", "morixe"],
        "medidas": {
            "kg":    ["1kg", "1 kg"],
            "medio": ["500g", "500 g"],
        }
    },
    "galletitas": {
        "subfamilia": "Galletitas",
        "familia":    "Alimentos",
        "sinonimos":  ["galletita", "galletitas", "galleta", "galletas",
                       "bizcochos", "crackers"],
        "marcas":     ["arcor", "bagley", "oreo", "triton", "toddy", "rumba"],
        "medidas": {}
    },
    "pañales": {
        "subfamilia": "Pañales descartables",
        "familia":    "Tocador y cosmética",
        "sinonimos":  ["pañal", "pañales", "panal", "panales"],
        "marcas":     ["babysec", "huggies", "pampers", "mimitos"],
        "medidas": {}
    },
    "shampoo": {
        "subfamilia": "Shampoo y Acondicionador",
        "familia":    "Tocador y cosmética",
        "sinonimos":  ["shampoo", "champú", "champu", "acondicionador"],
        "marcas":     ["sedal", "head", "pantene", "dove", "elseve"],
        "medidas": {}
    },
    "alimentos": {
        "subfamilia": None,  # categoría general — filtrar por familia
        "familia":    "Alimentos",
        "sinonimos":  ["alimento", "alimentos", "comestible", "comestibles",
                       "viveres", "víveres", "secos", "almacen", "almacén",
                       "groceries"],
        "marcas":     [],
        "medidas":    {}
    },
    "bebidas": {
        "subfamilia": None,
        "familia":    "Bebidas",
        "sinonimos":  ["bebida", "bebidas", "liquido", "líquido", "liquidos"],
        "marcas":     [],
        "medidas":    {}
    },
    "arroz": {
        "subfamilia": "Arroz",
        "familia":    "Alimentos",
        "sinonimos":  ["arroz"],
        "marcas":     ["gallo", "marolio", "dos hermanos", "la campagnola"],
        "medidas": {
            "kg":    ["1kg", "1 kg", "500g"],
        }
    },
    "azucar": {
        "subfamilia": "Azucar",
        "familia":    "Alimentos",
        "sinonimos":  ["azucar", "azúcar"],
        "marcas":     ["ledesma", "chango"],
        "medidas": {
            "kg":    ["1kg", "1 kg", "2kg"],
        }
    },
    "fideos": {
        "subfamilia": "Pastas secas comunes",
        "familia":    "Alimentos",
        "sinonimos":  ["fideo", "fideos", "pasta", "pastas", "spaghetti",
                       "tallarines", "mostacholes"],
        "marcas":     ["marolio", "don vicente", "matarazzo", "lucchetti"],
        "medidas": {
            "kg":    ["500g", "400g", "250g"],
        }
    },
    "te": {
        "subfamilia": "Té",
        "familia":    "Alimentos",
        "sinonimos":  ["te", "té", "infusion", "infusión", "saquito"],
        "marcas":     ["la virginia", "taragui", "lipton", "ser"],
        "medidas": {}
    },
    "detergentes": {
        "subfamilia": "Detergentes",
        "familia":    "Hogar",
        "sinonimos":  ["detergente", "detergentes", "lavavajilla", "lava"],
        "marcas":     ["magistral", "ayudin", "cif", "vim"],
        "medidas": {}
    },
    "jabones": {
        "subfamilia": "Jabón en polvo",
        "familia":    "Limpieza",
        "sinonimos":  ["jabon", "jabón", "polvo", "lavandina"],
        "marcas":     ["ala", "skip", "ariel", "ace", "drive"],
        "medidas": {}
    },
}

# ─── ÍNDICES INVERTIDOS (para búsqueda rápida) ───────────────
SINONIMO_A_CATEGORIA: dict[str, str] = {}
MARCA_A_CATEGORIA:    dict[str, str] = {}

for cat_key, cat_data in CATEGORIAS.items():
    for sin in cat_data["sinonimos"]:
        SINONIMO_A_CATEGORIA[sin] = cat_key
    for marca in cat_data.get("marcas", []):
        MARCA_A_CATEGORIA[marca] = cat_key

# ─── CAPACIDADES DEL AGENTE ───────────────────────────────────
CAPACIDADES_SI = [
    "Ventas por sucursal, artículo, familia, subfamilia y período",
    "Top artículos más vendidos (unidades, ventas, margen, utilidad)",
    "Comparar marcas, categorías o sucursales entre sí",
    "Tendencia diaria o mensual de ventas (2024-2026)",
    "Stock actual por sucursal",
    "Alertas de reabastecimiento y días de cobertura",
    "Estacionalidad: artículos en su mejor/peor momento del año",
    "Último precio de compra OC por artículo o categoría",
    "Comparar precios de compra entre proveedores",
    "Margen real (precio venta vs último precio OC)",
    "Artículos con precio bajo costo o margen crítico",
    "Presupuesto de compra estimado",
    "Artículos nuevos (últimos 30 días)",
    "Análisis de exceso de stock",
]

CAPACIDADES_NO = [
    "Historial de precios OC (solo tengo el último precio, no la evolución)",
    "Datos de clientes individuales o programas de fidelización",
    "Rentabilidad neta (no tengo gastos operativos, sueldos ni alquileres)",
    "Precios de la competencia",
    "Pedidos o recepciones pendientes de mercadería",
    "Datos de sucursal Sabin antes del 6-jun-2026",
    "Devoluciones o notas de crédito detalladas",
    "Información de empleados o RRHH",
]

# ─── MEDIDAS Y RANGOS ────────────────────────────────────────
# Para parsear "más de 900cc", "menor a 500g", etc.
UNIDADES_VOLUMEN = {
    "cc": 1, "ml": 1, "l": 1000, "litro": 1000, "litros": 1000,
}
UNIDADES_PESO = {
    "g": 1, "gr": 1, "kg": 1000, "kilo": 1000, "kilos": 1000,
}
