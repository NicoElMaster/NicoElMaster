#!/usr/bin/env python3
"""Genera las imágenes del README del perfil (carpeta assets/).

Todo lo que se ve en el perfil sale de aquí: la cabecera animada, el
separador, las tarjetas de cada sección y el pie. Son SVG escritos a mano que
comparten el mismo cielo nocturno y el mismo mar; los textos se convierten a
trazos para que se vean igual en cualquier equipo, sin depender de las fuentes
que tenga instaladas quien visita el perfil.

Necesita fontTools (pip install fonttools). Las rutas de las fuentes son las
de Arch Linux; cámbialas en FUENTES si hace falta.

    python scripts/generar.py            # regenera todo lo que se dibuja aquí
    python scripts/generar.py cabecera   # solo una pieza
    python scripts/generar.py iconos     # vuelve a descargar los iconos del stack
    python scripts/generar.py textos     # imprime los textos alternativos para el README
"""

import html
import random
import re
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
FUENTES = Path("/usr/share/fonts")

# ── Paleta: Catppuccin Mocha, más los azules del mar ─────────────────────────

CRUST, MANTLE, BASE = "#11111b", "#181825", "#1e1e2e"
SURFACE0, SURFACE1, OVERLAY = "#313244", "#45475a", "#6c7086"
TEXTO, SUBTEXTO = "#cdd6f4", "#a6adc8"
ROJO, DURAZNO, AMARILLO, VERDE = "#f38ba8", "#fab387", "#f9e2af", "#a6e3a1"
CIELO, ZAFIRO, AZUL, LAVANDA, MALVA = "#89dceb", "#74c7ec", "#89b4fa", "#b4befe", "#cba6f7"
MAR = ("#3b5488", "#2b4070", "#1c2b4e", "#141d36")
PAJA, PAJA_OSCURA, PAJA_BORDE = "#f9e2af", "#e2c178", "#7a5a2b"


# ── Lo que cambia con más frecuencia ─────────────────────────────────────────

NOMBRE = ("NICOLAS", "MORENO")
LUGAR = "BOGOTÁ, COLOMBIA"
FRASES = [
    "Desarrollador Full Stack",
    "Agentes de IA, web y apps móviles",
    "¡Voy a ser el Rey del Código!",
]
ETIQUETAS = "TypeScript · Next.js · React Native · PostgreSQL · IA"

TITULO_STACK = "Mi tripulación"
FRASE_STACK = "Ningún capitán navega solo. Con esta tripulación construyo un producto de punta a punta:"
COLUMNAS_STACK = ("PUESTO", "TRIPULANTES")


def icono(archivo, nombre):
    """Tecnología con icono de skillicons.dev, guardado en assets/iconos/."""
    return {"icono": archivo, "nombre": nombre}


def etiqueta(nombre, color):
    """Tecnología sin icono: se dibuja como una etiqueta con su nombre."""
    return {"nombre": nombre, "color": color}


# Cada fila: (puesto, aclaración, glifo de la Nerd Font, color, tecnologías).
STACK = [
    ("Lenguajes", "", 0xF04E5, ROJO, [
        icono("ts", "TypeScript"), icono("js", "JavaScript"), icono("java", "Java"), icono("py", "Python"),
        icono("html", "HTML"), icono("css", "CSS"), icono("bash", "Bash"),
        etiqueta("SQL", AZUL), etiqueta("PL/pgSQL", ZAFIRO)]),
    ("Cubierta", "frontend", 0xF03D8, DURAZNO, [
        icono("react", "React"), icono("nextjs", "Next.js"), icono("tailwind", "Tailwind CSS"),
        icono("vite", "Vite"), icono("threejs", "Three.js"),
        etiqueta("shadcn/ui", TEXTO), etiqueta("Zustand", DURAZNO), etiqueta("Framer Motion", "#f5c2e7")]),
    ("Botes", "móvil", 0xF10B, AMARILLO, [
        etiqueta("React Native", CIELO), etiqueta("Expo", TEXTO),
        icono("androidstudio", "Android Studio"), icono("firebase", "Firebase")]),
    ("Sala de máquinas", "backend", 0xF085, VERDE, [
        icono("nodejs", "Node.js"), icono("express", "Express"), icono("flask", "Flask"),
        etiqueta("Fastify", TEXTO), etiqueta("Zod", AZUL), etiqueta("WebSockets", VERDE)]),
    ("Bodega", "datos", 0xF487, ZAFIRO, [
        icono("postgres", "PostgreSQL"), icono("supabase", "Supabase"), icono("prisma", "Prisma"),
        icono("sqlite", "SQLite"),
        etiqueta("Drizzle ORM", VERDE), etiqueta("pgvector", ZAFIRO)]),
    ("Frutas del diablo", "inteligencia artificial", 0xF1042, MALVA, [
        etiqueta("Claude API", DURAZNO), etiqueta("OpenAI API", VERDE), etiqueta("Hugging Face", AMARILLO),
        etiqueta("RAG", MALVA), etiqueta("Bots de WhatsApp", VERDE)]),
    ("Astillero", "herramientas", 0xF09AC, LAVANDA, [
        icono("git", "Git"), icono("github", "GitHub"), icono("docker", "Docker"), icono("gcp", "Google Cloud"),
        icono("arch", "Arch Linux"), icono("vscode", "VS Code"), icono("vitest", "Vitest"), icono("maven", "Maven"),
        etiqueta("Playwright", VERDE)]),
]

ROTULO_BANDERA = "BANDERA PÚBLICA"
FRASE_BANDERA = ("Y este es el barco que navega con bandera pública: mi VS Code, "
                 "empaquetado para que cualquiera lo instale con un comando.")
PROYECTO = "vscode-setup"
DATOS_PROYECTO = [("Catppuccin Mocha", MALVA), ("40 extensiones", VERDE), ("Mascotas", DURAZNO),
                  ("Terminal a juego", ZAFIRO)]
LLAMADA = "Ver el repositorio"

DESPEDIDA = "¡Gracias por subir a bordo!"
DESPEDIDA_2 = "Nos vemos en el Grand Line"

# ── Texto convertido a trazos ────────────────────────────────────────────────

def _numero(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _pct(v):
    """Porcentaje para @keyframes, con más decimales que una coordenada."""
    return ("%.3f" % v).rstrip("0").rstrip(".") + "%"


class Fuente:
    def __init__(self, ruta, ejes=None):
        fuente = TTFont(str(FUENTES / ruta))
        if "fvar" in fuente:
            posicion = {eje.axisTag: eje.defaultValue for eje in fuente["fvar"].axes}
            posicion.update(ejes or {})
            fuente = instancer.instantiateVariableFont(fuente, posicion)
        self.glifos = fuente.getGlyphSet()
        self.mapa = fuente.getBestCmap()
        self.avances = fuente["hmtx"]
        self.upm = fuente["head"].unitsPerEm
        self.altura_mayusculas = getattr(fuente["OS/2"], "sCapHeight", 0) or self.upm * 0.7

    def trazo(self, texto, tam, x=0, y=0, espaciado=0, ancla="inicio"):
        """Devuelve (d, ancho): el trazo SVG del texto y lo que ocupa."""
        escala = tam / self.upm
        ancho = self.ancho(texto, tam, espaciado)
        if ancla == "centro":
            x -= ancho / 2
        elif ancla == "fin":
            x -= ancho
        pluma = SVGPathPen(self.glifos, ntos=_numero)
        cursor = x
        for letra in texto:
            glifo = self.mapa.get(ord(letra), ".notdef")
            self.glifos[glifo].draw(TransformPen(pluma, (escala, 0, 0, -escala, cursor, y)))
            cursor += self.avances[glifo][0] * escala + espaciado
        return pluma.getCommands(), ancho

    def ancho(self, texto, tam, espaciado=0):
        escala = tam / self.upm
        total = sum(self.avances[self.mapa.get(ord(l), ".notdef")][0] * escala for l in texto)
        return total + espaciado * max(len(texto) - 1, 0)

    def alto(self, tam):
        return self.altura_mayusculas * tam / self.upm

    def centrado(self, letra, tam, cx, cy):
        """El trazo de un solo glifo (un icono de la Nerd Font) centrado en un punto."""
        glifo = self.mapa.get(ord(letra), ".notdef")
        caja = BoundsPen(self.glifos)
        self.glifos[glifo].draw(caja)
        x0, y0, x1, y1 = caja.bounds
        escala = tam / self.upm
        pluma = SVGPathPen(self.glifos, ntos=_numero)
        self.glifos[glifo].draw(TransformPen(pluma, (
            escala, 0, 0, -escala, cx - (x0 + x1) / 2 * escala, cy + (y0 + y1) / 2 * escala)))
        return pluma.getCommands()


_cache = {}


def fuente(nombre):
    """Las fuentes se cargan solo cuando una pieza las necesita."""
    if nombre not in _cache:
        _cache[nombre] = {
            "titulo": lambda: Fuente("Adwaita/AdwaitaSans-Italic.ttf", {"wght": 900}),
            "mono": lambda: Fuente("TTF/JetBrainsMonoNerdFont-Bold.ttf"),
            "mono_fina": lambda: Fuente("TTF/JetBrainsMonoNerdFont-Medium.ttf"),
        }[nombre]()
    return _cache[nombre]


# ── Piezas de dibujo que se repiten ──────────────────────────────────────────

REDUCIR_MOVIMIENTO = "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }"


def ola(y, amplitud, periodo, ancho=1200, fondo=400):
    """Una ola con un periodo de sobra a cada lado, para moverla sin que se vea el corte."""
    tramos = int(ancho / periodo) + 3
    d = ["M%s,%s" % (_numero(-periodo), _numero(y))]
    for i in range(tramos * 2):
        subida = -amplitud if i % 2 == 0 else amplitud
        d.append("q%s,%s %s,0" % (_numero(periodo / 4), _numero(subida), _numero(periodo / 2)))
    d.append("V%s H%s Z" % (_numero(fondo), _numero(-periodo)))
    return " ".join(d)


def linea_ola(y, amplitud, periodo, ancho=1200):
    tramos = int(ancho / periodo) + 3
    d = ["M%s,%s" % (_numero(-periodo), _numero(y))]
    for i in range(tramos * 2):
        subida = -amplitud if i % 2 == 0 else amplitud
        d.append("q%s,%s %s,0" % (_numero(periodo / 4), _numero(subida), _numero(periodo / 2)))
    return " ".join(d)


def sombrero(escala=1.0):
    """Un sombrero de paja con cinta roja, dibujado alrededor del origen."""
    return f"""<g transform="scale({escala})" stroke="{PAJA_BORDE}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
      <ellipse cx="0" cy="0" rx="62" ry="17" fill="{PAJA_OSCURA}"/>
      <ellipse cx="0" cy="-3" rx="60" ry="15" fill="{PAJA}"/>
      <path d="M-34,-6 C-36,-50 36,-50 34,-6 C20,3 -20,3 -34,-6 Z" fill="{PAJA}"/>
      <path d="M-34,-8 C-20,1 20,1 34,-8 L34.6,-19 C20,-10 -20,-10 -34.6,-19 Z" fill="{ROJO}"/>
      <g fill="none" stroke="{PAJA_OSCURA}" stroke-width="1.6" opacity="0.9">
        <path d="M-22,-36 C-10,-41 10,-41 22,-36"/>
        <path d="M-27,-27 C-12,-33 12,-33 27,-27"/>
        <path d="M-48,3 C-30,10 30,10 48,3"/>
        <path d="M-40,-6 C-44,-4 -50,-3 -54,-2"/>
        <path d="M40,-6 C44,-4 50,-3 54,-2"/>
      </g>
    </g>"""


def barco():
    """Un velero de tres palos en silueta, con la línea de flotación en y=0."""
    return f"""<g fill="{CRUST}">
      <path d="M-58,-13 L-40,-9 L44,-9 L66,-15 L58,-1 C50,13 34,19 0,19 C-32,19 -48,13 -54,1 Z"/>
      <path d="M58,-12 L88,-24 L88,-21 L60,-8 Z"/>
      <rect x="-31.5" y="-78" width="3" height="70"/>
      <rect x="-1.5" y="-104" width="3" height="96"/>
      <rect x="26.5" y="-74" width="3" height="66"/>
      <g fill="{MANTLE}" stroke="{CRUST}" stroke-width="1.2" stroke-linejoin="round">
        <path d="M-46,-44 Q-30,-39 -14,-44 L-12,-16 Q-30,-10 -48,-16 Z"/>
        <path d="M-41,-70 Q-30,-66 -19,-70 L-17,-49 Q-30,-45 -43,-49 Z"/>
        <path d="M-19,-62 Q0,-56 19,-62 L21,-18 Q0,-11 -21,-18 Z"/>
        <path d="M-14,-94 Q0,-90 14,-94 L16,-67 Q0,-62 -16,-67 Z"/>
        <path d="M14,-42 Q28,-37 42,-42 L44,-16 Q28,-10 12,-16 Z"/>
        <path d="M18,-66 Q28,-62 38,-66 L40,-47 Q28,-43 16,-47 Z"/>
        <path d="M60,-12 L86,-23 L62,-46 Z"/>
      </g>
      <path class="bandera" d="M1.5,-104 q5,-4 10,0 t10,0 v9 q-5,4 -10,0 t-10,0 Z" fill="{ROJO}"/>
    </g>"""


def estrellas(cantidad, ancho, alto, semilla, evitar=None):
    azar = random.Random(semilla)
    puntos, intentos = [], 0
    while len(puntos) < cantidad and intentos < cantidad * 200:
        intentos += 1
        x, y = azar.uniform(20, ancho - 20), azar.uniform(14, alto)
        if evitar and evitar(x, y):
            continue
        radio = azar.choice((0.7, 0.9, 1.1, 1.1, 1.4, 1.8))
        color = azar.choice((TEXTO, TEXTO, LAVANDA, AMARILLO))
        clase = "e%d" % azar.randint(1, 5)
        puntos.append('<circle class="%s" cx="%s" cy="%s" r="%s" fill="%s"/>' % (
            clase, _numero(x), _numero(y), radio, color))
    return "\n      ".join(puntos)


CSS_ESTRELLAS = """
    @keyframes brillo { 0%, 100% { opacity: .95; } 50% { opacity: .2; } }
    .e1 { animation: brillo 3.1s ease-in-out infinite; }
    .e2 { animation: brillo 4.3s ease-in-out -1.2s infinite; }
    .e3 { animation: brillo 5.7s ease-in-out -2.6s infinite; }
    .e4 { animation: brillo 3.7s ease-in-out -0.7s infinite; }
    .e5 { animation: brillo 6.4s ease-in-out -3.9s infinite; }"""


# ── Cabecera ─────────────────────────────────────────────────────────────────

def cabecera(movil=False):
    """La cabecera. En la versión para pantallas estrechas el texto va arriba
    y el barco debajo, en vez de uno al lado del otro."""
    if movil:
        ancho, alto, horizonte = 640, 560, 468
        sol_x, sol_y, sol_r = 462, 470, 96
        tam, x0, y1, y2 = 82, 30, 158, 238
        lugar_y, caja_y, tam_frase, etiquetas_y, tam_etiquetas = 70, 262, 21, 344, 13.5
        gaviotas, reposo = (392, 414, 376), (120, 250, 40)
    else:
        ancho, alto, horizonte = 1200, 400, 304
        sol_x, sol_y, sol_r = 968, 306, 118
        tam, x0, y1, y2 = 88, 74, 166, 250
        lugar_y, caja_y, tam_frase, etiquetas_y, tam_etiquetas = 74, 276, 23, 362, 15
        gaviotas, reposo = (96, 132, 64), (690, 1090, 800)
    titulo, mono, mono_fina = fuente("titulo"), fuente("mono"), fuente("mono_fina")

    # Título en dos líneas, con sombra de color al estilo de una portada de manga.
    linea1, ancho1 = titulo.trazo(NOMBRE[0], tam, x0, y1, espaciado=1)
    linea2, _ = titulo.trazo(NOMBRE[1], tam, x0 + 20, y2, espaciado=1)
    letras = linea1 + " " + linea2

    lugar_x = x0 + 128
    lugar, ancho_lugar = mono.trazo(LUGAR, 15, lugar_x, lugar_y, espaciado=3.2)

    # Frases que se escriben solas: el texto está fijo y una tapa del color del
    # fondo se retira letra a letra. El borde de la tapa hace de cursor.
    caja_x, caja_alto = x0, 46
    avance = mono.ancho("M", tam_frase)
    texto_x = caja_x + 20 + avance * 2
    base_y = caja_y + caja_alto / 2 + mono.alto(tam_frase) / 2
    caja_ancho = (texto_x - caja_x) + avance * max(len(f) for f in FRASES) + 26
    simbolo, _ = mono.trazo("❯", tam_frase, caja_x + 20, base_y)

    ciclo = 4.2 * len(FRASES)
    parte = 100 / len(FRASES)
    frases_svg, frases_css = [], []
    for i, frase in enumerate(FRASES):
        d, w = mono.trazo(frase, tam_frase, texto_x, base_y)
        inicio = parte * i
        escribir, mantener, borrar = inicio + parte * 0.30, inicio + parte * 0.80, inicio + parte * 0.94
        pasos = len(frase)
        # Fuera de su turno la frase es invisible; el estado sin animación deja
        # la primera frase escrita entera.
        visible = "1" if i == 0 else "0"
        tapa_base = w if i == 0 else 0
        # step-end mantiene cada valor hasta el fotograma clave siguiente: la
        # frase aparece y desaparece de golpe, sin fundidos.
        antes = "" if i == 0 else "0% { opacity: 0; } "
        frases_css.append(f"""
    @keyframes ver{i} {{ {antes}{_pct(inicio)} {{ opacity: 1; }} {_pct(inicio + parte)} {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
    @keyframes tapa{i} {{
      0%, {_pct(inicio)} {{ transform: translateX(0); animation-timing-function: steps({pasos}, end); }}
      {_pct(escribir)} {{ transform: translateX({_numero(w)}px); }}
      {_pct(mantener)} {{ transform: translateX({_numero(w)}px); animation-timing-function: steps({pasos}, end); }}
      {_pct(borrar)}, 100% {{ transform: translateX(0); }}
    }}
    .frase{i} {{ opacity: {visible}; animation: ver{i} {ciclo}s step-end infinite; }}
    .tapa{i} {{ transform: translateX({_numero(tapa_base)}px); animation: tapa{i} {ciclo}s linear infinite; }}""")
        frases_svg.append(f"""<g class="frase{i}">
        <path d="{d}" fill="{TEXTO}"/>
        <g class="tapa{i}">
          <rect x="{_numero(texto_x - 1)}" y="{caja_y + 2}" width="{_numero(caja_ancho)}" height="{caja_alto - 4}" fill="{CRUST}"/>
          <rect class="cursor" x="{_numero(texto_x + 2)}" y="{_numero(base_y - mono.alto(tam_frase) - 5)}" width="3" height="{_numero(mono.alto(tam_frase) + 10)}" fill="{AMARILLO}"/>
        </g>
      </g>""")

    etiquetas, _ = mono_fina.trazo(ETIQUETAS, tam_etiquetas, x0 + 4, etiquetas_y, espaciado=0.6)

    def cerca_del_sol(x, y):
        en_texto = (40 < y < etiquetas_y + 14) if movil else (x < 700 and 40 < y < 280)
        return (x - sol_x) ** 2 + (y - sol_y) ** 2 < (sol_r + 70) ** 2 or en_texto

    rayos = "".join(
        '<path d="M0,0 L%s,-330 L%s,-330 Z" transform="rotate(%s)"/>' % (-13, 13, angulo)
        for angulo in range(0, 360, 30))
    reflejos = "".join(
        '<rect class="r%d" x="%s" y="%s" width="%s" height="2.4" rx="1.2"/>' % (
            i % 3 + 1, _numero(sol_x - w / 2), horizonte + 18 + i * 11, w)
        for i, w in enumerate((120, 84, 104, 56, 76, 38)))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" role="img" aria-labelledby="t d">
  <title id="t">Nicolas Moreno, desarrollador full stack</title>
  <desc id="d">Un velero navega de noche frente a un sol naciente. Sobre el nombre descansa un sombrero de paja, y debajo se escriben solas tres frases: {'; '.join(FRASES)}.</desc>
  <style>{CSS_ESTRELLAS}
    @keyframes olas-izq {{ to {{ transform: translateX(-160px); }} }}
    @keyframes olas-der {{ to {{ transform: translateX(220px); }} }}
    @keyframes mecer {{ 0%, 100% {{ transform: rotate(-2.2deg) translateY(0); }} 50% {{ transform: rotate(2.2deg) translateY(-3px); }} }}
    @keyframes girar {{ to {{ transform: rotate(360deg); }} }}
    @keyframes balanceo {{ 0%, 100% {{ transform: rotate(-3deg); }} 50% {{ transform: rotate(3deg); }} }}
    @keyframes parpadeo {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
    @keyframes volar {{ from {{ transform: translateX(-80px); }} to {{ transform: translateX({ancho + 100}px); }} }}
    @keyframes destello {{ 0%, 100% {{ opacity: .08; }} 50% {{ opacity: .34; }} }}
    @keyframes ondear {{ 0%, 100% {{ transform: skewY(0deg); }} 50% {{ transform: skewY(-9deg); }} }}
    .ola1 {{ animation: olas-der 16s linear infinite; }}
    .ola2 {{ animation: olas-izq 11s linear infinite; }}
    .ola3 {{ animation: olas-der 8s linear infinite; }}
    .ola4 {{ animation: olas-izq 6s linear infinite; }}
    .barco {{ transform-box: fill-box; transform-origin: 50% 88%; animation: mecer 5.5s ease-in-out infinite; }}
    .bandera {{ transform-box: fill-box; transform-origin: 0% 50%; animation: ondear 1.6s ease-in-out infinite; }}
    .rayos {{ transform-box: fill-box; transform-origin: 50% 50%; animation: girar 120s linear infinite; }}
    .sombrero {{ transform-box: fill-box; transform-origin: 50% 90%; animation: balanceo 4.5s ease-in-out infinite; }}
    .cursor {{ animation: parpadeo 0.9s steps(1, end) infinite; }}
    .g1 {{ transform: translateX({reposo[0]}px); animation: volar 46s linear -24s infinite; }}
    .g2 {{ transform: translateX({reposo[1]}px); animation: volar 58s linear -49s infinite; }}
    .g3 {{ transform: translateX({reposo[2]}px); animation: volar 52s linear -33s infinite; }}
    .r1 {{ opacity: .3; animation: destello 2.6s ease-in-out infinite; }}
    .r2 {{ opacity: .16; animation: destello 3.4s ease-in-out -1.1s infinite; }}
    .r3 {{ opacity: .24; animation: destello 2.9s ease-in-out -2s infinite; }}{''.join(frases_css)}
    {REDUCIR_MOVIMIENTO}
  </style>
  <defs>
    <clipPath id="marco"><rect width="{ancho}" height="{alto}" rx="26"/></clipPath>
    <clipPath id="caja"><rect x="{caja_x}" y="{caja_y}" width="{_numero(caja_ancho)}" height="{caja_alto}" rx="12"/></clipPath>
    <linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0b0b14"/>
      <stop offset="0.5" stop-color="{BASE}"/>
      <stop offset="0.76" stop-color="#3a2c4d"/>
      <stop offset="1" stop-color="#3a2c4d"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{DURAZNO}" stop-opacity="0.55"/>
      <stop offset="0.45" stop-color="{ROJO}" stop-opacity="0.2"/>
      <stop offset="1" stop-color="{ROJO}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="sol" cx="0.5" cy="0.42" r="0.6">
      <stop offset="0" stop-color="#fff6dd"/>
      <stop offset="0.5" stop-color="{AMARILLO}"/>
      <stop offset="1" stop-color="{DURAZNO}"/>
    </radialGradient>
    <linearGradient id="letras" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="{LAVANDA}"/>
    </linearGradient>
    <linearGradient id="velo" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{CRUST}" stop-opacity="0.82"/>
      <stop offset="0.5" stop-color="{CRUST}" stop-opacity="0.5"/>
      <stop offset="0.72" stop-color="{CRUST}" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <g clip-path="url(#marco)">
    <rect width="{ancho}" height="{alto}" fill="url(#cielo)"/>
    <g>
      {estrellas(22 if movil else 64, ancho, horizonte - 22 if movil else 250, 11, cerca_del_sol)}
    </g>

    <circle cx="{sol_x}" cy="{sol_y}" r="330" fill="url(#halo)"/>
    <g transform="translate({sol_x} {sol_y})">
      <g class="rayos" fill="{AMARILLO}" opacity="0.055">{rayos}</g>
    </g>
    <circle cx="{sol_x}" cy="{sol_y}" r="{sol_r}" fill="url(#sol)"/>

    <g fill="none" stroke="{TEXTO}" stroke-width="2" stroke-linecap="round" opacity="0.55">
      <path class="g1" d="M0,{gaviotas[0]} q7,-8 14,0 q7,-8 14,0"/>
      <path class="g2" d="M0,{gaviotas[1]} q5,-6 10,0 q5,-6 10,0"/>
      <path class="g3" d="M0,{gaviotas[2]} q6,-7 12,0 q6,-7 12,0"/>
    </g>

    <path class="ola1" d="{ola(horizonte, 5, 220, ancho, alto)}" fill="{MAR[0]}"/>
    <g transform="translate({sol_x - 22} {horizonte + 6})">
      <g class="barco">{barco()}</g>
    </g>
    <path class="ola2" d="{ola(horizonte + 20, 7, 160, ancho, alto)}" fill="{MAR[1]}"/>
    <path class="ola3" d="{ola(horizonte + 44, 8, 220, ancho, alto)}" fill="{MAR[2]}"/>
    <path class="ola4" d="{ola(horizonte + 70, 7, 160, ancho, alto)}" fill="{MAR[3]}"/>
    <g fill="#fff6dd">{reflejos}</g>

    <rect width="{ancho}" height="{alto}" fill="url(#velo)" opacity="{0 if movil else 1}"/>

    <g fill="{ZAFIRO}">
      <path d="{lugar}"/>
    </g>
    <g transform="translate({_numero(lugar_x + ancho_lugar + 16)} {lugar_y - 5.5})">
      <circle r="5" fill="#fcd116"/><circle cx="14" r="5" fill="#2f6fde"/><circle cx="28" r="5" fill="#e0344b"/>
    </g>

    <path d="{letras}" transform="translate(6 6)" fill="{ROJO}" stroke="{CRUST}" stroke-width="9" stroke-linejoin="round" paint-order="stroke"/>
    <path d="{letras}" fill="url(#letras)" stroke="{CRUST}" stroke-width="9" stroke-linejoin="round" paint-order="stroke"/>

    <g transform="translate({x0 + 24} {_numero(y1 - titulo.alto(tam) + 5)}) rotate(-13)">
      <g class="sombrero">{sombrero(0.92)}</g>
    </g>

    <rect x="{caja_x}" y="{caja_y}" width="{_numero(caja_ancho)}" height="{caja_alto}" rx="12" fill="{CRUST}" stroke="{SURFACE0}" stroke-width="1.5"/>
    <path d="{simbolo}" fill="{VERDE}"/>
    <g clip-path="url(#caja)">
      {''.join(frases_svg)}
    </g>

    <path d="{etiquetas}" fill="{SUBTEXTO}"/>
  </g>
  <rect x="1" y="1" width="{ancho - 2}" height="{alto - 2}" rx="25" fill="none" stroke="{SURFACE0}" stroke-width="2"/>
</svg>
"""


# ── Separador ────────────────────────────────────────────────────────────────

def separador():
    ancho, alto = 1200, 44
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" role="img" aria-label="Olas">
  <style>
    @keyframes izq {{ to {{ transform: translateX(-120px); }} }}
    @keyframes der {{ to {{ transform: translateX(160px); }} }}
    @keyframes flotar {{ 0%, 100% {{ transform: translateY(0) rotate(-4deg); }} 50% {{ transform: translateY(-3px) rotate(4deg); }} }}
    .a {{ animation: izq 7s linear infinite; }}
    .b {{ animation: der 10s linear infinite; }}
    .hat {{ transform-box: fill-box; transform-origin: 50% 80%; animation: flotar 4s ease-in-out infinite; }}
    {REDUCIR_MOVIMIENTO}
  </style>
  <defs>
    <linearGradient id="tinta" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{AZUL}" stop-opacity="0"/>
      <stop offset="0.18" stop-color="{AZUL}"/>
      <stop offset="0.5" stop-color="{MALVA}"/>
      <stop offset="0.82" stop-color="{ZAFIRO}"/>
      <stop offset="1" stop-color="{ZAFIRO}" stop-opacity="0"/>
    </linearGradient>
    <mask id="desvanecer"><rect width="{ancho}" height="{alto}" fill="url(#m)"/></mask>
    <linearGradient id="m" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#000"/><stop offset="0.15" stop-color="#fff"/>
      <stop offset="0.85" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
    </linearGradient>
  </defs>
  <g mask="url(#desvanecer)" fill="none" stroke-linecap="round">
    <path class="b" d="{linea_ola(30, 5, 160, ancho)}" stroke="{AZUL}" stroke-width="2" opacity="0.35"/>
    <path class="a" d="{linea_ola(24, 6, 120, ancho)}" stroke="url(#tinta)" stroke-width="3"/>
  </g>
  <g transform="translate(600 20)"><g class="hat">{sombrero(0.3)}</g></g>
</svg>
"""


# ── Pie ──────────────────────────────────────────────────────────────────────

def pie(movil=False):
    if movil:
        ancho, alto, horizonte, tam, tam_2 = 640, 236, 156, 37, 14.5
        y_1, y_2, grosor, sombra, hat = 82, 118, 5.5, 3, 0.62
    else:
        ancho, alto, horizonte, tam, tam_2 = 1200, 190, 112, 40, 15
        y_1, y_2, grosor, sombra, hat = 62, 92, 6, 3, 0.62
    titulo, mono = fuente("titulo"), fuente("mono")
    gracias, _ = titulo.trazo(DESPEDIDA, tam, ancho / 2, y_1, espaciado=0.5, ancla="centro")
    adios, _ = mono.trazo(DESPEDIDA_2, tam_2, ancho / 2, y_2, espaciado=2.4, ancla="centro")

    def junto_al_texto(x, y):
        return (y_1 - tam < y < y_2 + 10) if movil else (330 < x < 870)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" role="img" aria-labelledby="t">
  <title id="t">{DESPEDIDA} {DESPEDIDA_2}.</title>
  <style>{CSS_ESTRELLAS}
    @keyframes izq {{ to {{ transform: translateX(-160px); }} }}
    @keyframes der {{ to {{ transform: translateX(220px); }} }}
    @keyframes flotar {{ 0%, 100% {{ transform: translateY(0) rotate(-5deg); }} 50% {{ transform: translateY(-5px) rotate(5deg); }} }}
    .o1 {{ animation: der 15s linear infinite; }}
    .o2 {{ animation: izq 10s linear infinite; }}
    .o3 {{ animation: der 7s linear infinite; }}
    .hat {{ transform-box: fill-box; transform-origin: 50% 80%; animation: flotar 5s ease-in-out infinite; }}
    {REDUCIR_MOVIMIENTO}
  </style>
  <defs>
    <clipPath id="marco"><rect width="{ancho}" height="{alto}" rx="26"/></clipPath>
    <linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0b0b14"/><stop offset="0.6" stop-color="{BASE}"/><stop offset="1" stop-color="#2d2540"/>
    </linearGradient>
    <linearGradient id="letras" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{LAVANDA}"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#marco)">
    <rect width="{ancho}" height="{alto}" fill="url(#cielo)"/>
    <g>
      {estrellas(20 if movil else 46, ancho, horizonte - 16, 23, junto_al_texto)}
    </g>
    <path d="{gracias}" transform="translate({sombra} {sombra})" fill="{ROJO}" stroke="{CRUST}" stroke-width="{grosor}" stroke-linejoin="round" paint-order="stroke"/>
    <path d="{gracias}" fill="url(#letras)" stroke="{CRUST}" stroke-width="{grosor}" stroke-linejoin="round" paint-order="stroke"/>
    <path d="{adios}" fill="{ZAFIRO}"/>
    <path class="o1" d="{ola(horizonte, 5, 220, ancho, alto)}" fill="{MAR[0]}"/>
    <path class="o2" d="{ola(horizonte + 20, 7, 160, ancho, alto)}" fill="{MAR[1]}"/>
    <g transform="translate({ancho / 2} {horizonte + 30})"><g class="hat">{sombrero(hat)}</g></g>
    <path class="o3" d="{ola(horizonte + 44, 8, 220, ancho, alto)}" fill="{MAR[2]}"/>
  </g>
  <rect x="1" y="1" width="{ancho - 2}" height="{alto - 2}" rx="25" fill="none" stroke="{SURFACE0}" stroke-width="2"/>
</svg>
"""


# ── Tarjetas: el mismo cielo y el mismo mar que la cabecera ───────────────────

CSS_MAR = """
    @keyframes izq { to { transform: translateX(-160px); } }
    @keyframes der { to { transform: translateX(220px); } }
    @keyframes flotar { 0%, 100% { transform: translateY(0) rotate(-5deg); } 50% { transform: translateY(-5px) rotate(5deg); } }
    @keyframes mecer { 0%, 100% { transform: rotate(-2.2deg) translateY(0); } 50% { transform: rotate(2.2deg) translateY(-3px); } }
    @keyframes ondear { 0%, 100% { transform: skewY(0deg); } 50% { transform: skewY(-9deg); } }
    .o1 { animation: der 15s linear infinite; }
    .o2 { animation: izq 10s linear infinite; }
    .o3 { animation: der 7s linear infinite; }
    .hat { transform-box: fill-box; transform-origin: 50% 80%; animation: flotar 5s ease-in-out infinite; }
    .barco { transform-box: fill-box; transform-origin: 50% 88%; animation: mecer 5.5s ease-in-out infinite; }
    .bandera { transform-box: fill-box; transform-origin: 0% 50%; animation: ondear 1.6s ease-in-out infinite; }
    @keyframes destello { 0%, 100% { opacity: .08; } 50% { opacity: .34; } }
    .r1 { opacity: .3; animation: destello 2.6s ease-in-out infinite; }
    .r2 { opacity: .16; animation: destello 3.4s ease-in-out -1.1s infinite; }
    .r3 { opacity: .24; animation: destello 2.9s ease-in-out -2s infinite; }"""


def tarjeta(ancho, alto, descripcion, contenido, semilla, horizonte, ocupado, cantidad,
            cielo="", tras_primera_ola="", tras_segunda_ola=""):
    """Envuelve el contenido en el cielo nocturno con estrellas y el mar al pie.

    `ocupado(x, y)` dice dónde no deben caer estrellas (detrás de un texto
    restan legibilidad). Los tres huecos permiten colocar algo en el cielo o
    entre las olas.
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {ancho} {_numero(alto)}" width="{ancho}" height="{_numero(alto)}" role="img" aria-labelledby="t">
  <title id="t">{html.escape(descripcion)}</title>
  <style>{CSS_ESTRELLAS}{CSS_MAR}
    {REDUCIR_MOVIMIENTO}
  </style>
  <defs>
    <clipPath id="marco"><rect width="{ancho}" height="{_numero(alto)}" rx="26"/></clipPath>
    <linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0b0b14"/><stop offset="0.6" stop-color="{BASE}"/><stop offset="1" stop-color="#2d2540"/>
    </linearGradient>
    <linearGradient id="letras" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{LAVANDA}"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#marco)">
    <rect width="{ancho}" height="{_numero(alto)}" fill="url(#cielo)"/>
    <g>
      {estrellas(cantidad, ancho, horizonte - 24, semilla, ocupado)}
    </g>
    {cielo}
    <path class="o1" d="{ola(horizonte, 5, 220, ancho, alto)}" fill="{MAR[0]}"/>
    {tras_primera_ola}
    <path class="o2" d="{ola(horizonte + 20, 7, 160, ancho, alto)}" fill="{MAR[1]}"/>
    {tras_segunda_ola}
    <path class="o3" d="{ola(horizonte + 44, 8, 220, ancho, alto)}" fill="{MAR[2]}"/>
    {contenido}
  </g>
  <rect x="1" y="1" width="{ancho - 2}" height="{_numero(alto - 2)}" rx="25" fill="none" stroke="{SURFACE0}" stroke-width="2"/>
</svg>
"""


def letrero(texto, tam, x, y, ancla="inicio"):
    """Un título con la misma letra, contorno y sombra que el nombre de la cabecera."""
    d, ancho = fuente("titulo").trazo(texto, tam, x, y, espaciado=0.5, ancla=ancla)
    grosor, sombra = max(4, tam * 0.13), max(2.5, tam * 0.065)
    comun = f'stroke="{CRUST}" stroke-width="{_numero(grosor)}" stroke-linejoin="round" paint-order="stroke"'
    return (f'<path d="{d}" transform="translate({_numero(sombra)} {_numero(sombra)})" fill="{ROJO}" {comun}/>'
            f'<path d="{d}" fill="url(#letras)" {comun}/>'), ancho


def envolver(texto, maximo):
    """Parte un texto en líneas de como mucho `maximo` letras, sin cortar palabras."""
    lineas, actual = [], ""
    for palabra in texto.split():
        if actual and len(actual) + 1 + len(palabra) > maximo:
            lineas.append(actual)
            actual = palabra
        else:
            actual = (actual + " " + palabra).strip()
    if actual:
        lineas.append(actual)
    return lineas


def parrafo(texto, tam, x, y, maximo, interlinea=1.45, color=TEXTO):
    """Varias líneas de texto. Devuelve (svg, y de la última línea)."""
    mono = fuente("mono_fina")
    piezas = []
    for i, linea in enumerate(envolver(texto, maximo)):
        d, _ = mono.trazo(linea, tam, x, y + i * tam * interlinea, espaciado=0.2)
        piezas.append(f'<path d="{d}" fill="{color}"/>')
    return "".join(piezas), y + (len(piezas) - 1) * tam * interlinea


# ── Tecnologías: iconos y etiquetas ──────────────────────────────────────────

_iconos = {}


def _interior_icono(archivo):
    """El dibujo de un icono de skillicons, con sus identificadores renombrados
    para que no choquen con los de otro icono dentro de la misma imagen."""
    if archivo not in _iconos:
        ruta = ASSETS / "iconos" / (archivo + ".svg")
        if not ruta.exists():
            sys.exit("Falta %s. Descárgalo con: python scripts/generar.py iconos" % ruta)
        texto = ruta.read_text(encoding="utf-8")
        inicio = texto.index("<svg", texto.index("<g transform"))
        interior = texto[inicio:texto.rindex("</g>")].strip()
        interior = re.sub(r'\bid="([^"]+)"', r'id="%s-\1"' % archivo, interior)
        interior = re.sub(r'url\(#([^)]+)\)', r'url(#%s-\1)' % archivo, interior)
        interior = re.sub(r'href="#([^"]+)"', r'href="#%s-\1"' % archivo, interior)
        _iconos[archivo] = interior
    return _iconos[archivo]


def ancho_tecnologia(tecnologia, alto):
    if "icono" in tecnologia:
        return alto
    k = alto / 48
    return (15 + 18 + 15) * k + fuente("mono").ancho(tecnologia["nombre"], 15 * k, 0.3 * k)


def dibujar_tecnologia(tecnologia, x, y, alto):
    if "icono" in tecnologia:
        return '<svg x="%s" y="%s" width="%s" height="%s" viewBox="0 0 256 256">%s</svg>' % (
            _numero(x), _numero(y), alto, alto, _interior_icono(tecnologia["icono"]))
    return pastilla(tecnologia["nombre"], tecnologia["color"], x, y, alto)


def pastilla(texto, color, x, y, alto, fondo="#242938", tinta=TEXTO):
    """Una etiqueta redondeada con un punto de color, del alto de un icono."""
    mono = fuente("mono")
    k = alto / 48
    ancho = (15 + 18 + 15) * k + mono.ancho(texto, 15 * k, 0.3 * k)
    d, _ = mono.trazo(texto, 15 * k, x + 33 * k, y + alto / 2 + mono.alto(15 * k) / 2, espaciado=0.3 * k)
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>'
            '<circle cx="%s" cy="%s" r="%s" fill="%s"/><path d="%s" fill="%s"/>') % (
        _numero(x), _numero(y), _numero(ancho), alto, _numero(11.25 * k), fondo,
        _numero(x + 19.5 * k), _numero(y + alto / 2), _numero(4.5 * k), color, d, tinta)


def fluir(tecnologias, x0, y0, ancho_max, alto, hueco=8):
    """Coloca las tecnologías una tras otra y salta de línea cuando no caben.
    Devuelve (svg, alto ocupado)."""
    x, y, piezas = x0, y0, []
    for tecnologia in tecnologias:
        ancho = ancho_tecnologia(tecnologia, alto)
        if x > x0 and x + ancho > x0 + ancho_max:
            x, y = x0, y + alto + hueco
        piezas.append(dibujar_tecnologia(tecnologia, x, y, alto))
        x += ancho + hueco
    return "".join(piezas), y + alto - y0


def insignia(glifo, color, cx, cy, lado=40):
    """El icono de cada puesto, dentro de un cuadro teñido de su color."""
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" fill-opacity="0.16" stroke="%s" stroke-opacity="0.35"/>'
            '<path d="%s" fill="%s"/>') % (
        _numero(cx - lado / 2), _numero(cy - lado / 2), lado, lado, _numero(lado * 0.28), color, color,
        fuente("mono").centrado(chr(glifo), lado * 0.58, cx, cy), color)


def texto_stack():
    """El contenido de la tarjeta en palabras, para lectores de pantalla."""
    filas = []
    for puesto, aclaracion, _, _, tecnologias in STACK:
        nombre = puesto + (" (%s)" % aclaracion if aclaracion else "")
        filas.append("%s: %s." % (nombre, ", ".join(t["nombre"] for t in tecnologias)))
    return "%s. %s %s" % (TITULO_STACK, FRASE_STACK, " ".join(filas))


# ── Mi tripulación ───────────────────────────────────────────────────────────

def tripulacion():
    ancho, margen = 1200, 56
    mono, titulo = fuente("mono"), fuente("titulo")
    piezas = []

    piezas.append('<path d="%s" fill="%s"/>' % (mono.centrado(chr(0xF0787), 42, margen + 22, 76), AMARILLO))
    rotulo, _ = letrero(TITULO_STACK, 46, margen + 60, 92)
    piezas.append(rotulo)
    frase, _ = parrafo(FRASE_STACK, 18.5, margen + 2, 136, 120)
    piezas.append(frase)

    # La tabla: una columna para el puesto y otra para sus tripulantes. La
    # primera mide lo que el nombre más largo, y cada fila crece si sus
    # tecnologías no caben en una sola línea.
    tx, ty, tw = margen, 164, ancho - 2 * margen
    cabecera_alto, icono_alto = 44, 48
    columna = 74 + max(titulo.ancho(puesto, 22, 0.3) for puesto, *_ in STACK) + 22
    flujos = [fluir(tecnologias, tx + columna + 22, 0, tw - columna - 40, icono_alto)
              for *_, tecnologias in STACK]
    altos = [alto_flujo + 26 for _, alto_flujo in flujos]
    tabla_alto = cabecera_alto + sum(altos)
    piezas.append(f'<clipPath id="tabla"><rect x="{tx}" y="{ty}" width="{tw}" height="{_numero(tabla_alto)}" rx="18"/></clipPath>')
    filas = [f'<rect x="{tx}" y="{ty}" width="{tw}" height="{_numero(tabla_alto)}" fill="{CRUST}" fill-opacity="0.72"/>',
             f'<rect x="{tx}" y="{ty}" width="{tw}" height="{cabecera_alto}" fill="{SURFACE0}" fill-opacity="0.55"/>']
    for i, encabezado in enumerate(COLUMNAS_STACK):
        d, _ = mono.trazo(encabezado, 13, tx + 20 + (columna + 2) * i, ty + cabecera_alto / 2 + mono.alto(13) / 2, espaciado=3)
        filas.append(f'<path d="{d}" fill="{ZAFIRO}"/>')

    y = ty + cabecera_alto
    for i, (puesto, aclaracion, glifo, color, tecnologias) in enumerate(STACK):
        fila_alto = altos[i]
        cy = y + fila_alto / 2
        if i % 2:
            filas.append(f'<rect x="{tx}" y="{_numero(y)}" width="{tw}" height="{_numero(fila_alto)}" fill="{MANTLE}" fill-opacity="0.55"/>')
        filas.append(f'<rect x="{tx}" y="{_numero(y)}" width="{tw}" height="1" fill="{SURFACE0}"/>')
        filas.append(insignia(glifo, color, tx + 40, cy))
        base = cy - 3 if aclaracion else cy + titulo.alto(22) / 2
        d, _ = titulo.trazo(puesto, 22, tx + 74, base, espaciado=0.3)
        filas.append(f'<path d="{d}" fill="#eef1ff"/>')
        if aclaracion:
            d, _ = fuente("mono_fina").trazo(aclaracion, 13, tx + 75, cy + 17, espaciado=0.4)
            filas.append(f'<path d="{d}" fill="{SUBTEXTO}"/>')
        dibujo, _ = fluir(tecnologias, tx + columna + 22, y + 13, tw - columna - 40, icono_alto)
        filas.append(dibujo)
        y += fila_alto
    filas.append(f'<rect x="{_numero(tx + columna)}" y="{ty}" width="1" height="{_numero(tabla_alto)}" fill="{SURFACE0}"/>')
    piezas.append('<g clip-path="url(#tabla)">%s</g>' % "".join(filas))
    piezas.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{_numero(tabla_alto)}" rx="18" fill="none" stroke="{SURFACE1}" stroke-width="1.5"/>')

    horizonte = ty + tabla_alto + 50
    alto = horizonte + 70

    def ocupado(x, y):
        return y > 112 or (x < 470 and y > 36)

    sombrero_flotando = f'<g transform="translate({ancho / 2} {horizonte + 30})"><g class="hat">{sombrero(0.6)}</g></g>'
    return tarjeta(ancho, alto, texto_stack(), "".join(piezas), 31, horizonte, ocupado, 34,
                   tras_segunda_ola=sombrero_flotando)


def tripulacion_movil():
    """La misma tarjeta para pantallas estrechas: cada puesto en su propio
    recuadro, con el nombre arriba y las tecnologías debajo."""
    ancho, margen = 640, 26
    mono, titulo = fuente("mono"), fuente("titulo")
    piezas = []

    piezas.append('<path d="%s" fill="%s"/>' % (mono.centrado(chr(0xF0787), 36, margen + 18, 60), AMARILLO))
    rotulo, _ = letrero(TITULO_STACK, 38, margen + 50, 73)
    piezas.append(rotulo)
    frase, y = parrafo(FRASE_STACK, 17.5, margen + 2, 112, 54)
    piezas.append(frase)

    y += 26
    inicio = y
    for puesto, aclaracion, glifo, color, tecnologias in STACK:
        dibujo, alto_flujo = fluir(tecnologias, margen + 16, y + 68, ancho - 2 * margen - 32, 46)
        alto_recuadro = 68 + alto_flujo + 16
        piezas.append(f'<rect x="{margen}" y="{_numero(y)}" width="{ancho - 2 * margen}" height="{_numero(alto_recuadro)}" rx="18" '
                      f'fill="{CRUST}" fill-opacity="0.72" stroke="{SURFACE1}" stroke-width="1.5"/>')
        piezas.append(insignia(glifo, color, margen + 36, y + 36))
        d, w = titulo.trazo(puesto, 23, margen + 68, y + 36 + titulo.alto(23) / 2, espaciado=0.3)
        piezas.append(f'<path d="{d}" fill="#eef1ff"/>')
        if aclaracion:
            d, _ = fuente("mono_fina").trazo(aclaracion, 13, margen + 68 + w + 12, y + 36 + titulo.alto(23) / 2, espaciado=0.4)
            piezas.append(f'<path d="{d}" fill="{SUBTEXTO}"/>')
        piezas.append(dibujo)
        y += alto_recuadro + 12

    horizonte = y + 38
    alto = horizonte + 66

    def ocupado(x, y_):
        return y_ > 88 or (x < 400 and y_ > 30)

    sombrero_flotando = f'<g transform="translate({ancho / 2} {_numero(horizonte + 30)})"><g class="hat">{sombrero(0.55)}</g></g>'
    return tarjeta(ancho, alto, texto_stack(), "".join(piezas), 37, horizonte, ocupado, 16,
                   tras_segunda_ola=sombrero_flotando)


# ── El barco de bandera pública ──────────────────────────────────────────────

def _luna(cx, cy, radio):
    """Una luna llena que asoma tras el horizonte; el barco se recorta contra ella."""
    cx, cy = round(cx, 1), round(cy, 1)
    crateres = "".join(
        '<circle cx="%s" cy="%s" r="%s"/>' % (_numero(cx + dx * radio), _numero(cy + dy * radio), _numero(r * radio))
        for dx, dy, r in ((-0.38, -0.32, 0.16), (0.3, -0.5, 0.09), (0.42, 0.02, 0.12), (-0.5, 0.2, 0.08), (0.02, -0.12, 0.06)))
    return f"""<defs>
      <radialGradient id="halo-luna" cx="0.5" cy="0.5" r="0.5">
        <stop offset="0" stop-color="{AMARILLO}" stop-opacity="0.34"/>
        <stop offset="0.5" stop-color="{LAVANDA}" stop-opacity="0.12"/>
        <stop offset="1" stop-color="{LAVANDA}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="luna" cx="0.42" cy="0.36" r="0.72">
        <stop offset="0" stop-color="#fffaf0"/><stop offset="0.72" stop-color="{AMARILLO}"/><stop offset="1" stop-color="#e9cf9a"/>
      </radialGradient>
    </defs>
    <circle cx="{cx}" cy="{cy}" r="{_numero(radio * 2.5)}" fill="url(#halo-luna)"/>
    <circle cx="{cx}" cy="{cy}" r="{radio}" fill="url(#luna)"/>
    <g fill="{PAJA_OSCURA}" opacity="0.32">{crateres}</g>"""


def _reflejo(cx, y, ancho_max):
    """Destellos de la luna sobre el agua."""
    return '<g fill="#fff6dd">%s</g>' % "".join(
        '<rect class="r%d" x="%s" y="%s" width="%s" height="2.4" rx="1.2"/>' % (
            i % 3 + 1, _numero(cx - ancho_max * f / 2), _numero(y + i * 11), _numero(ancho_max * f))
        for i, f in enumerate((1, 0.7, 0.86, 0.46, 0.6)))


def _datos_proyecto(x0, y0, ancho_max, alto=40):
    """Las etiquetas del proyecto. Devuelve (svg, y donde terminan)."""
    mono = fuente("mono")
    k = alto / 48
    x, y, piezas = x0, y0, []
    for texto, color in DATOS_PROYECTO:
        ancho = (15 + 18 + 15) * k + mono.ancho(texto, 15 * k, 0.3 * k)
        if x > x0 and x + ancho > x0 + ancho_max:
            x, y = x0, y + alto + 9
        piezas.append(pastilla(texto, color, x, y, alto))
        x += ancho + 9
    return "".join(piezas), y + alto


def _boton(x, cy, alto=46):
    """El botón amarillo que invita a entrar al repositorio."""
    mono = fuente("mono")
    k = alto / 48
    d, w = mono.trazo(LLAMADA, 16 * k, x + 20 * k, cy + mono.alto(16 * k) / 2, espaciado=0.3 * k)
    ancho = 20 * k + w + 40 * k
    flecha = mono.centrado(chr(0xF061), 18 * k, x + 20 * k + w + 20 * k, cy)
    return (f'<rect x="{_numero(x)}" y="{_numero(cy - alto / 2)}" width="{_numero(ancho)}" height="{alto}" rx="{_numero(13 * k)}" fill="{AMARILLO}"/>'
            f'<path d="{d}" fill="{CRUST}"/><path d="{flecha}" fill="{CRUST}"/>'), ancho


def _texto_bandera():
    return "%s %s: %s." % (FRASE_BANDERA, PROYECTO, ", ".join(texto for texto, _ in DATOS_PROYECTO))


def bandera():
    ancho, alto, margen, horizonte = 1200, 372, 56, 300
    mono, titulo = fuente("mono"), fuente("titulo")
    piezas = []

    piezas.append('<path d="%s" fill="%s"/>' % (mono.centrado(chr(0xF024), 17, margen + 9, 54), ROJO))
    d, _ = mono.trazo(ROTULO_BANDERA, 13, margen + 28, 54 + mono.alto(13) / 2, espaciado=3)
    piezas.append(f'<path d="{d}" fill="{ZAFIRO}"/>')
    frase, y = parrafo(FRASE_BANDERA, 18.5, margen + 2, 96, 62)
    piezas.append(frase)
    rotulo, ancho_rotulo = letrero(PROYECTO, 56, margen, y + 74)
    piezas.append(rotulo)
    boton, _ = _boton(margen + ancho_rotulo + 30, y + 74 - titulo.alto(56) / 2)
    piezas.append(boton)
    datos, _ = _datos_proyecto(margen, y + 100, 760)
    piezas.append(datos)

    barco_x, luna_y, luna_r = 1000, horizonte - 66, 104
    navio = (_reflejo(barco_x, horizonte + 22, 120)
             + f'<g transform="translate({barco_x} {horizonte + 8}) scale(1.45)"><g class="barco">{barco()}</g></g>')

    def ocupado(x, y_):
        en_texto = x < 800 and 30 < y_ < 272
        en_luna = (x - barco_x) ** 2 + (y_ - luna_y) ** 2 < (luna_r + 44) ** 2
        return en_texto or en_luna

    return tarjeta(ancho, alto, _texto_bandera(), "".join(piezas), 43, horizonte, ocupado, 34,
                   cielo=_luna(barco_x - 6, luna_y, luna_r), tras_primera_ola=navio)


def bandera_movil():
    ancho, margen = 640, 26
    mono, titulo = fuente("mono"), fuente("titulo")
    piezas = []

    piezas.append('<path d="%s" fill="%s"/>' % (mono.centrado(chr(0xF024), 17, margen + 9, 50), ROJO))
    d, _ = mono.trazo(ROTULO_BANDERA, 13, margen + 28, 50 + mono.alto(13) / 2, espaciado=3)
    piezas.append(f'<path d="{d}" fill="{ZAFIRO}"/>')
    frase, y = parrafo(FRASE_BANDERA, 17.5, margen + 2, 90, 54)
    piezas.append(frase)
    rotulo, _ = letrero(PROYECTO, 48, margen, y + 66)
    piezas.append(rotulo)
    datos, fin = _datos_proyecto(margen, y + 90, ancho - 2 * margen)
    piezas.append(datos)
    boton, _ = _boton(margen, fin + 40)
    piezas.append(boton)
    fin += 64

    horizonte = fin + 150
    alto = horizonte + 70
    barco_x, luna_y, luna_r = 462, horizonte - 52, 84
    navio = (_reflejo(barco_x, horizonte + 22, 100)
             + f'<g transform="translate({barco_x} {_numero(horizonte + 8)}) scale(1.2)"><g class="barco">{barco()}</g></g>')

    def ocupado(x, y_):
        en_luna = (x - barco_x) ** 2 + (y_ - luna_y) ** 2 < (luna_r + 36) ** 2
        return y_ < fin + 12 or en_luna

    return tarjeta(ancho, alto, _texto_bandera(), "".join(piezas), 47, horizonte, ocupado, 20,
                   cielo=_luna(barco_x - 5, luna_y, luna_r), tras_primera_ola=navio)


# ── Iconos y textos ──────────────────────────────────────────────────────────

def iconos():
    """Descarga los iconos de skillicons.dev (licencia MIT) a assets/iconos/."""
    import urllib.request
    carpeta = ASSETS / "iconos"
    carpeta.mkdir(exist_ok=True)
    for _, _, _, _, tecnologias in STACK:
        for tecnologia in tecnologias:
            if "icono" in tecnologia:
                peticion = urllib.request.Request(
                    "https://skillicons.dev/icons?theme=dark&i=" + tecnologia["icono"],
                    headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                    (carpeta / (tecnologia["icono"] + ".svg")).write_bytes(respuesta.read())


def textos():
    """Imprime los textos alternativos de las tarjetas, para copiarlos al README."""
    print("tripulacion:\n" + texto_stack() + "\n")
    print("bandera-publica:\n" + _texto_bandera())


# ── Programa ─────────────────────────────────────────────────────────────────

PIEZAS = {
    "cabecera": lambda: (escribir("cabecera", cabecera()), escribir("cabecera-movil", cabecera(movil=True))),
    "separador": lambda: escribir("separador", separador()),
    "tripulacion": lambda: (escribir("tripulacion", tripulacion()), escribir("tripulacion-movil", tripulacion_movil())),
    "bandera": lambda: (escribir("bandera-publica", bandera()), escribir("bandera-publica-movil", bandera_movil())),
    "pie": lambda: (escribir("pie", pie()), escribir("pie-movil", pie(movil=True))),
}
# No se ejecutan solas: una depende de la red y la otra solo imprime texto.
EXTRA = {"iconos": iconos, "textos": textos}


def escribir(nombre, svg):
    (ASSETS / (nombre + ".svg")).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    pedidas = sys.argv[1:] or list(PIEZAS)
    todas = dict(PIEZAS, **EXTRA)
    for nombre in pedidas:
        if nombre not in todas:
            sys.exit("No conozco la pieza '%s'. Opciones: %s" % (nombre, ", ".join(todas)))
        todas[nombre]()
        if nombre != "textos":
            print("lista:", nombre)
