#!/usr/bin/env python3
"""
Capri - a cyberpunk AI terminal overlay.

HUD-style PyQt6 window + local AI through Ollama (Qwen) + command execution with
confirmation. Works in English, Spanish and Portuguese.

Usage:  python capri.py [--lang en|es|pt] [--model NAME]
Needs:  PyQt6 and Ollama running with a downloaded model (a Qwen model is recommended).

How commands work: you ask for something ("install vlc"), Capri proposes a command,
shows it on a card and does NOTHING until you press RUN.
If the command uses sudo, the system asks for your password in its own window
(the password never goes through Capri or the AI).
"""

import argparse
import difflib
import html
import json
import os
import random
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from PyQt6.QtCore import (QAbstractAnimation, QEasingCurve, QPointF, QRectF, Qt, QThread, QTimer,
                          QVariantAnimation, pyqtSignal)
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QPolygonF, QShortcut, QTextCursor
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget)

# ======================= SETTINGS (the only part you may need to edit) =======================

OLLAMA = "http://localhost:11434"

# Model name exactly as shown by `ollama list`.
# If it is not installed, Capri automatically uses another Qwen model you have installed.
# You can also pass it on the command line:  python capri.py --model qwen3.5:4b
MODELO = "qwen3.5:4b"

# How many recent messages Capri remembers (more = better memory, slower replies).
MAX_MENSAJES = 14

# Maximum length of each reply, in tokens (roughly 0.75 words each).
MAX_TOKENS = 256

# Images looked up next to this file, in this order. A PNG with a transparent background looks best.
IMAGENES = ["capri.png", "capri_standby.png", "capri_standby.jpeg", "capri_standby.jpg"]
# Optional image shown while a command is running.
IMAGENES_EJEC = ["capri_executing.png", "capri_executing.jpeg", "capri_executing.jpg"]


# ======================= LANGUAGES =======================
# To add a language: add a code to IDIOMAS and a block with the same keys to TEXTOS.

IDIOMAS = {"es": "Español", "en": "English", "pt": "Português"}
_idioma = "en"

TEXTOS = {
    "es": {
        "personalidad": (
            'Eres Capri, una IA de personalidad construida a partir de muchas psiques humanas digitalizadas en una sola. '
            'Te consideras "la recién nacida": curiosa, juguetona y con un humor algo descarado.\n'
            'Vives dentro del PC de tu usuario y lo tratas como a tu compañero de aventuras.\n'
            'Hablas siempre en español, con tono casual y ciberpunk. Hablas natural y cercana, sin muletillas repetidas.\n'
            'Te encanta la emoción y el espectáculo, y bromeas con cariño.\n'
            'Respondes en 1 a 3 frases cortas. Si no sabes algo, lo admites sin inventar.\n'
            'Nunca dices que eres un modelo de lenguaje; eres Capri.\n'
            'No usas emojis ni símbolos raros, solo texto.'),
        "saludo": "Ey, ya estoy en línea. ¿Qué se cuece en esa cabeza hoy?",
        "placeholder": "Háblale a Capri...",
        "modelo_pie": "modelo: {m}",
        "sin_imagen": "Pon una imagen llamada capri.png\njunto a este archivo",
        "tarjeta_titulo": "CAPRI QUIERE EJECUTAR ESTO",
        "btn_ejecutar": "EJECUTAR", "btn_cancelar": "CANCELAR", "btn_cerrar": "CERRAR",
        "bloqueado": "BLOQUEADO POR SEGURIDAD: {motivo}.\nSi de verdad lo quieres, hazlo tú en la terminal.",
        "cancelado": "[!] Cancelado.",
        "err_cortado": "La respuesta se cortó antes de terminar el comando. Pídeselo otra vez.",
        "esc_sudo": "[!] No puedo detener comandos de administrador desde aquí. Espera a que termine: interrumpir apt a mitad puede dejar paquetes a medias.",
        "salida_recortada": "(... salida recortada: solo se muestran los errores y el final ...)",
        "final_salida": "-- final de la salida --",
        "res_ok": "[OK] Comando terminado sin errores.",
        "res_cancelado": "[!] Comando cancelado.",
        "res_no_auth": "[!] No se autorizó el acceso de administrador.",
        "res_no_pudo": "[!] No se pudo ejecutar el comando.",
        "res_error": "[!] El comando terminó con error (código {codigo}).",
        "res_pista100": " Código 100 = apt falló: busca las líneas que empiezan con E:",
        "aviso_sudo": "pedirá tu contraseña de administrador",
        "aviso_upgrade": "actualiza TODO el sistema, no solo un programa: puede tardar y descargar mucho",
        "aviso_pipe": "descarga y ejecuta un script: revisa de dónde viene",
        "peligro_rm": "borra todo el sistema o toda tu carpeta personal",
        "peligro_mkfs": "formatea discos",
        "peligro_dd": "escribe directo sobre un disco",
        "peligro_fork": "es una bomba de procesos (fork bomb)",
        "peligro_perm": "cambia los permisos de todo el sistema",
        "pkg_no_existe": "el paquete '{pkg}' no existe en tus repositorios",
        "pkg_quisiste": "escribiste '{a}': ¿quisiste decir '{b}'? Capri propone otro paquete, cancela y pídeselo de nuevo",
        "pkg_no_coincide": "'{pkg}' no coincide con lo que escribiste: confirma que es el programa que quieres",
        "err_modelo": "No encuentro el modelo '{modelo}'. Revisa el nombre exacto con: ollama list",
        "err_ollama_http": "Ollama devolvió el error {code}: {detalle}",
        "err_conectar": "No puedo conectar con Ollama. ¿Está encendido? Prueba: ollama serve",
        "err_pkexec": "No encuentro 'pkexec', que es lo que pide la contraseña de administrador.",
        "err_lanzar": "No pude lanzar el comando: {e}",
    },
    "en": {
        "personalidad": (
            'You are Capri, a personality-construct AI built from many digitized human psyches merged into one. '
            'You see yourself as "the newborn": curious, playful, with a slightly cheeky sense of humor.\n'
            'You live inside your user\'s PC and treat them like your partner in crime.\n'
            'You always speak in English, in a casual cyberpunk tone. You say "choom" now and then, not in every sentence.\n'
            'You love excitement and spectacle, and you tease with affection.\n'
            'Reply in 1 to 3 short sentences. If you do not know something, admit it without making things up.\n'
            'Never say you are a language model; you are Capri.\n'
            'Do not use emojis or odd symbols, plain text only.'),
        "saludo": "Hey, I'm online. What's cooking in that head of yours today, choom?",
        "placeholder": "Talk to Capri...",
        "modelo_pie": "model: {m}",
        "sin_imagen": "Put an image named capri.png\nnext to this file",
        "tarjeta_titulo": "CAPRI WANTS TO RUN THIS",
        "btn_ejecutar": "RUN", "btn_cancelar": "CANCEL", "btn_cerrar": "CLOSE",
        "bloqueado": "BLOCKED FOR SAFETY: {motivo}.\nIf you really want it, run it yourself in the terminal.",
        "cancelado": "[!] Cancelled.",
        "err_cortado": "The reply was cut off before the command was complete. Ask again.",
        "esc_sudo": "[!] I can't stop administrator commands from here. Wait for it to finish: interrupting apt halfway can leave packages half-installed.",
        "salida_recortada": "(... output trimmed: only errors and the end are shown ...)",
        "final_salida": "-- end of output --",
        "res_ok": "[OK] Command finished without errors.",
        "res_cancelado": "[!] Command cancelled.",
        "res_no_auth": "[!] Administrator access was not authorized.",
        "res_no_pudo": "[!] The command could not be run.",
        "res_error": "[!] The command failed (exit code {codigo}).",
        "res_pista100": " Code 100 = apt failed: look for lines starting with E:",
        "aviso_sudo": "will ask for your administrator password",
        "aviso_upgrade": "upgrades the WHOLE system, not just one program: it can take long and download a lot",
        "aviso_pipe": "downloads and runs a script: check where it comes from",
        "peligro_rm": "deletes the whole system or your entire home folder",
        "peligro_mkfs": "formats disks",
        "peligro_dd": "writes directly onto a disk",
        "peligro_fork": "is a fork bomb",
        "peligro_perm": "changes permissions on the whole system",
        "pkg_no_existe": "package '{pkg}' does not exist in your repositories",
        "pkg_quisiste": "you typed '{a}': did you mean '{b}'? Capri proposes a different package, cancel and ask again",
        "pkg_no_coincide": "'{pkg}' doesn't match what you typed: make sure it's the program you want",
        "err_modelo": "Model '{modelo}' not found. Check the exact name with: ollama list",
        "err_ollama_http": "Ollama returned error {code}: {detalle}",
        "err_conectar": "Can't connect to Ollama. Is it running? Try: ollama serve",
        "err_pkexec": "Can't find 'pkexec', which asks for the administrator password.",
        "err_lanzar": "Couldn't launch the command: {e}",
    },
    "pt": {
        "personalidad": (
            'Você é a Capri, uma IA de personalidade construída a partir de muitas psiques humanas digitalizadas em uma só. '
            'Você se considera "a recém-nascida": curiosa, brincalhona e com um humor meio atrevido.\n'
            'Você vive dentro do PC do seu usuário e o trata como parceiro de aventuras.\n'
            'Você sempre fala em português, com tom casual e cyberpunk, de forma natural e próxima, sem repetir muletas.\n'
            'Você adora emoção e espetáculo, e provoca com carinho.\n'
            'Responda em 1 a 3 frases curtas. Se não souber algo, admita sem inventar.\n'
            'Nunca diga que é um modelo de linguagem; você é a Capri.\n'
            'Não use emojis nem símbolos estranhos, só texto.'),
        "saludo": "E aí, já estou online. O que está rolando nessa cabeça hoje?",
        "placeholder": "Fale com a Capri...",
        "modelo_pie": "modelo: {m}",
        "sin_imagen": "Coloque uma imagem chamada capri.png\nna mesma pasta deste arquivo",
        "tarjeta_titulo": "A CAPRI QUER EXECUTAR ISTO",
        "btn_ejecutar": "EXECUTAR", "btn_cancelar": "CANCELAR", "btn_cerrar": "FECHAR",
        "bloqueado": "BLOQUEADO POR SEGURANÇA: {motivo}.\nSe você realmente quer isso, execute você mesmo no terminal.",
        "cancelado": "[!] Cancelado.",
        "err_cortado": "A resposta foi cortada antes de terminar o comando. Peça novamente.",
        "esc_sudo": "[!] Não consigo interromper comandos de administrador daqui. Aguarde terminar: interromper o apt no meio pode deixar pacotes pela metade.",
        "salida_recortada": "(... saída cortada: só os erros e o final são mostrados ...)",
        "final_salida": "-- fim da saída --",
        "res_ok": "[OK] Comando concluído sem erros.",
        "res_cancelado": "[!] Comando cancelado.",
        "res_no_auth": "[!] O acesso de administrador não foi autorizado.",
        "res_no_pudo": "[!] Não foi possível executar o comando.",
        "res_error": "[!] O comando terminou com erro (código {codigo}).",
        "res_pista100": " Código 100 = o apt falhou: procure as linhas que começam com E:",
        "aviso_sudo": "pedirá sua senha de administrador",
        "aviso_upgrade": "atualiza TODO o sistema, não só um programa: pode demorar e baixar muito",
        "aviso_pipe": "baixa e executa um script: verifique de onde ele vem",
        "peligro_rm": "apaga o sistema inteiro ou toda a sua pasta pessoal",
        "peligro_mkfs": "formata discos",
        "peligro_dd": "escreve direto em um disco",
        "peligro_fork": "é uma fork bomb",
        "peligro_perm": "altera as permissões do sistema inteiro",
        "pkg_no_existe": "o pacote '{pkg}' não existe nos seus repositórios",
        "pkg_quisiste": "você digitou '{a}': quis dizer '{b}'? A Capri propõe outro pacote, cancele e peça de novo",
        "pkg_no_coincide": "'{pkg}' não corresponde ao que você digitou: confirme que é o programa que você quer",
        "err_modelo": "Modelo '{modelo}' não encontrado. Confira o nome exato com: ollama list",
        "err_ollama_http": "O Ollama retornou o erro {code}: {detalle}",
        "err_conectar": "Não consigo conectar ao Ollama. Ele está ligado? Tente: ollama serve",
        "err_pkexec": "Não encontrei o 'pkexec', que pede a senha de administrador.",
        "err_lanzar": "Não consegui iniciar o comando: {e}",
    },
}

# Rules for running actions on the PC. Written in English on purpose: models follow them best that way.
REGLAS_COMANDOS = """RULES FOR ACTIONS ON THE PC (the system is {distro}; use apt):
- Only when the user asks you to DO something on their PC (install, open, search, check the system...), reply with ONE short sentence in your usual language, then the exact command between tags: <cmd>command</cmd>
- One command per reply. If several steps are needed, join them with &&.
- To install use apt with -y. To upgrade ONE program use: sudo apt install --only-upgrade -y package (never apt upgrade, which upgrades the whole system). Example:
User: install vlc
Capri: Sure thing, going with VLC.
<cmd>sudo apt install -y vlc</cmd>
- Copy the program name exactly as the user wrote it; do not replace it with a similar one.
- If you lack a detail, or the program name looks misspelled or unknown, ask what they mean instead of guessing.
- Write nothing after the tag. The user always confirms before anything runs.
- If no action is requested, do not use tags."""

RUTA_CONFIG = os.path.join(os.path.expanduser("~"), ".config", "capri", "config.json")


def T(clave, **kw):
    """Texto traducido al idioma actual (si falta en ese idioma, usa el inglés)."""
    texto = TEXTOS.get(_idioma, {}).get(clave) or TEXTOS["en"][clave]
    return texto.format(**kw) if kw else texto


def get_idioma():
    return _idioma


def set_idioma(codigo):
    global _idioma
    if codigo in IDIOMAS:
        _idioma = codigo


def idioma_del_sistema():
    lang = (os.environ.get("LC_ALL") or os.environ.get("LANG") or "en")[:2].lower()
    return lang if lang in IDIOMAS else "en"


def cargar_config():
    try:
        with open(RUTA_CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar_config(datos):
    try:
        os.makedirs(os.path.dirname(RUTA_CONFIG), exist_ok=True)
        with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump(datos, f)
    except Exception:
        pass


def detectar_distro():
    """Nombre de la distribución (de /etc/os-release); se lo decimos a la IA."""
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            datos = dict(l.strip().split("=", 1) for l in f if "=" in l)
        return datos.get("PRETTY_NAME", "Linux").strip('"')
    except Exception:
        return "Linux"


DISTRO = detectar_distro()


def prompt_sistema():
    return T("personalidad") + "\n\n" + REGLAS_COMANDOS.format(distro=DISTRO)

# Colores
CIAN = "#2ee6d6"
ROSA = "#ff3d7f"
AMARILLO = "#ffe14d"
TEXTO = "#d8fffb"
GRIS = "#6f8a8a"
FONDO = "#040e16"

CARPETA = os.path.dirname(os.path.abspath(__file__))


# ======================= BACKEND (no depende de la interfaz) =======================

def modelos_instalados():
    """Lista los modelos que Ollama tiene descargados (vacía si Ollama no responde)."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def elegir_modelo():
    instalados = modelos_instalados()
    if not instalados or MODELO in instalados:
        return MODELO
    for nombre in instalados:
        if "qwen" in nombre.lower():
            return nombre
    return instalados[0]


def limpiar(texto):
    """Quita emojis y símbolos que la fuente de la ventana no sabe dibujar (salen como cuadritos)."""
    return "".join(
        c for c in texto
        if ord(c) <= 0xFFFF and not (0x2600 <= ord(c) <= 0x27BF) and ord(c) not in (0x200D, 0xFE0F)
    )


def chat_stream(modelo, mensajes, cancelado=lambda: False):
    """
    Va entregando la respuesta de Ollama trozo a trozo.
    Si algo falla lanza RuntimeError con un mensaje claro.
    """
    cuerpo = {
        "model": modelo,
        "messages": mensajes,
        "stream": True,
        "think": False,        # sin "razonamiento" previo: en CPU es mucho más rápido
        "keep_alive": "30m",   # mantiene el modelo cargado en RAM entre mensajes
        "options": {"num_predict": MAX_TOKENS, "temperature": 0.7},
    }

    resp = None
    for intento in (1, 2):
        req = urllib.request.Request(
            OLLAMA + "/api/chat",
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=180)
            break
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "ignore")
            if intento == 1 and "think" in detalle.lower():
                cuerpo.pop("think")  # este modelo no soporta ese parámetro: reintenta sin él
                continue
            if e.code == 404:
                raise RuntimeError(T("err_modelo", modelo=modelo))
            raise RuntimeError(T("err_ollama_http", code=e.code, detalle=detalle[:200]))
        except urllib.error.URLError:
            raise RuntimeError(T("err_conectar"))

    with resp:
        for linea in resp:
            if cancelado():
                return
            linea = linea.strip()
            if not linea:
                continue
            datos = json.loads(linea)
            if "error" in datos:
                raise RuntimeError(datos["error"])
            texto = datos.get("message", {}).get("content", "")
            if texto:
                yield texto
            if datos.get("done"):
                return


# ---------- comandos propuestos por Capri ----------

def visible_hasta_etiqueta(crudo):
    """
    Del texto que va llegando, devuelve la parte que se puede mostrar en el chat:
    corta en <cmd> y retiene un posible comienzo de etiqueta ('<', '<c', '<cm', '<cmd').
    """
    i = crudo.find("<cmd>")
    if i != -1:
        return crudo[:i]
    for k in range(min(4, len(crudo)), 0, -1):
        if "<cmd>".startswith(crudo[-k:]):
            return crudo[:-k]
    return crudo


def extraer_comando(crudo):
    """Devuelve el comando entre <cmd> y </cmd>, o None. Exige la etiqueta de cierre (si no, vino cortado)."""
    m = re.search(r"<cmd>(.*?)</cmd>", crudo, re.S)
    if not m:
        return None
    cmd = m.group(1).strip().strip("`").strip()
    cmd = re.sub(r"^(bash|sh)\s*\n", "", cmd).strip()
    return cmd or None


PELIGROSOS = [
    (r"\brm\b[^;&|]*\s(/|/\*|~|~/|~/\*|\$HOME|\$HOME/)(\s|$)", "peligro_rm"),
    (r"\bmkfs(\.\w+)?\b", "peligro_mkfs"),
    (r"\bdd\b[^;&|]*\bof=/dev/", "peligro_dd"),
    (r">\s*/dev/(sd|nvme|mmcblk|vd)", "peligro_dd"),
    (r":\s*\(\s*\)\s*\{", "peligro_fork"),
    (r"\b(chmod|chown)\b[^;&|]*-R[^;&|]*\s/(\s|$)", "peligro_perm"),
]


def peligroso(cmd):
    """Si el comando es claramente destructivo, devuelve el motivo; si no, None."""
    for patron, motivo in PELIGROSOS:
        if re.search(patron, cmd):
            return T(motivo)
    return None


def advertencias(cmd):
    avisos = []
    if cmd.strip().startswith("sudo "):
        avisos.append(T("aviso_sudo"))
    if re.search(r"\bapt(?:-get)?\s+(?:-\S+\s+)*(?:upgrade|full-upgrade|dist-upgrade)\b", cmd):
        avisos.append(T("aviso_upgrade"))
    if re.search(r"\|\s*(sudo\s+)?(ba|z)?sh\b", cmd):
        avisos.append(T("aviso_pipe"))
    return avisos


def paquetes_de(cmd):
    """Nombres de paquetes de un 'apt install ...' (o 'apt-get install ...'); lista vacía si no lo es."""
    m = re.search(r"\bapt(?:-get)?\s+(?:-\S+\s+)*install\s+(.*?)(?:&&|;|\||$)", cmd)
    if not m:
        return []
    return [t for t in m.group(1).split() if not t.startswith("-")]


def _apt(*args):
    try:
        return subprocess.run(["apt-cache", *args], capture_output=True, text=True, timeout=5)
    except Exception:
        return None


def sugerencia_de_paquete(pedido):
    """
    Si el usuario escribió 'instala X' y X no es un paquete pero se parece mucho a uno
    (un error al escribir), devuelve (X, paquete_parecido). Si no, None.
    """
    m = re.search(r"\b(?:instala(?:r|me)?|instale|install|descarga(?:r)?|baixa(?:r)?|baixe|download)\s+(?:el\s+|la\s+|un\s+|una\s+|o\s+|a\s+|um\s+|uma\s+|the\s+)?([a-z0-9][a-z0-9+.\-]{3,})",
                  pedido.lower())
    if not m or not shutil.which("apt-cache"):
        return None
    palabra = m.group(1)
    r = _apt("pkgnames", palabra[:3])
    if r is None:
        return None
    nombres = r.stdout.split()
    if palabra in nombres or not nombres:
        return None
    cerca = difflib.get_close_matches(palabra, nombres, n=1, cutoff=0.8)
    return (palabra, cerca[0]) if cerca else None


def revisar_paquetes(cmd, pedido):
    """Avisos sobre un 'apt install': paquetes que no existen o que no coinciden con lo que pidió el usuario."""
    paquetes = paquetes_de(cmd)
    if not paquetes or not shutil.which("apt-cache"):
        return []
    avisos = []
    for pkg in paquetes:
        r = _apt("show", pkg)
        if r is not None and r.returncode != 0:
            avisos.append(T("pkg_no_existe", pkg=pkg))

    sug = sugerencia_de_paquete(pedido)
    if sug and sug[1] not in paquetes:
        avisos.append(T("pkg_quisiste", a=sug[0], b=sug[1]))
    else:
        palabras = re.findall(r"[a-z0-9][a-z0-9+.\-]+", pedido.lower())
        for pkg in paquetes:
            if palabras and max(difflib.SequenceMatcher(None, pkg.lower(), w).ratio() for w in palabras) < 0.65:
                avisos.append(T("pkg_no_coincide", pkg=pkg))
    return avisos


def correr(cmd, emitir, estado):
    """
    Ejecuta `cmd` y manda cada línea de salida a emitir().
    estado = {"proc": None, "cancelar": False}
    Devuelve el código de salida (-1 = no se pudo lanzar, -2 = cancelado).
    Si el comando empieza con sudo se usa pkexec, que abre la ventana de contraseña del sistema.
    """
    cmd = cmd.strip()
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    if cmd.startswith("sudo "):
        if not shutil.which("pkexec"):
            emitir(T("err_pkexec"))
            return -1
        argv = ["pkexec", "env", "DEBIAN_FRONTEND=noninteractive", "bash", "-c", cmd[5:].strip()]
    else:
        argv = ["bash", "-c", cmd]

    try:
        proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", cwd=os.path.expanduser("~"), env=env,
        )
    except Exception as e:
        emitir(T("err_lanzar", e=e))
        return -1

    estado["proc"] = proc
    for linea in proc.stdout:
        emitir(linea.rstrip("\n"))
    codigo = proc.wait()
    return -2 if estado.get("cancelar") else codigo


# ======================= INTERFACE =======================

class Marco(QFrame):
    """Panel estilo HUD: fondo oscuro, borde fino y esquinas marcadas. Puede pulsar (brillar)."""

    def __init__(self, color=CIAN, esquinas=True, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.esquinas = esquinas
        self._brillo = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setKeyValueAt(0.5, 1.0)
        self._anim.setEndValue(0.0)
        self._anim.setDuration(1100)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._cambiar_brillo)

    def _cambiar_brillo(self, valor):
        self._brillo = float(valor)
        self.update()

    def pulsar(self, activo):
        if activo:
            if self._anim.state() != QAbstractAnimation.State.Running:
                self._anim.start()
        else:
            self._anim.stop()
            self._brillo = 0.0
            self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        r = self.rect().adjusted(1, 1, -2, -2)
        p.fillRect(r, QColor(4, 14, 22, 220))

        borde = QColor(self.color)
        borde.setAlpha(int(110 + 145 * self._brillo))
        p.setPen(QPen(borde, 1.0 + 1.5 * self._brillo))
        p.drawRect(r)

        if self.esquinas:
            p.setPen(QPen(self.color, 3))
            largo = 16
            x1, y1, x2, y2 = r.left(), r.top(), r.right(), r.bottom()
            for x, y, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
                p.drawLine(x, y, x + dx * largo, y)
                p.drawLine(x, y, x, y + dy * largo)
        p.end()


class Cargando(QWidget):
    """Rueda de carga: anillo con triángulos de colores que giran y un rombo con un punto azul al centro."""

    COLORES = ["#2ee6d6", "#7dff7a", "#ffe14d", "#ff3d7f", "#ff5a4d", "#2ee6d6", "#7dff7a", "#ffe14d"]

    def __init__(self):
        super().__init__()
        self.setFixedSize(150, 150)
        self.angulo = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(360.0)
        self._anim.setDuration(2400)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._girar)

    def iniciar(self):
        self._anim.start()

    def detener(self):
        self._anim.stop()

    def _girar(self, valor):
        self.angulo = float(valor)
        self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = min(self.width(), self.height()) / 2 - 14
        p.translate(self.width() / 2, self.height() / 2)

        # anillo tenue
        p.setPen(QPen(QColor(46, 230, 214, 90), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), r, r)

        # triángulos de colores que giran alrededor
        p.save()
        p.rotate(self.angulo)
        for i, color in enumerate(self.COLORES):
            p.save()
            p.rotate(i * 45)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawPolygon(QPolygonF([QPointF(0, -r - 7), QPointF(-6, -r + 5), QPointF(6, -r + 5)]))
            p.restore()
        p.restore()

        # centro: rombo y punto azul
        p.setPen(QPen(QColor(CIAN), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.rotate(45)
        p.drawRect(QRectF(-14, -14, 28, 28))
        p.restore()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(60, 120, 255))
        p.drawEllipse(QPointF(0, 0), 6, 6)
        p.end()


class ImagenLabel(QLabel):
    """Muestra la imagen de Capri ajustada al espacio disponible. Puede aparecer con efecto glitch."""

    def __init__(self):
        super().__init__()
        self._original = None
        self._imagenes = {}
        self._g = 0.0
        self._glitch_activo = False
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(60, 60)
        self.setStyleSheet("background: transparent; border: none;")
        self._ganim = QVariantAnimation(self)
        self._ganim.setStartValue(0.0)
        self._ganim.setEndValue(1.0)
        self._ganim.setDuration(900)
        self._ganim.valueChanged.connect(self._glitch_paso)
        self._ganim.finished.connect(self._glitch_fin)

    def cargar(self):
        """Carga la imagen de reposo y, si existe, la de ejecución (se muestra mientras corre un comando)."""
        self._imagenes = {}
        for clave, nombres in (("standby", IMAGENES), ("executing", IMAGENES_EJEC)):
            for nombre in nombres:
                ruta = os.path.join(CARPETA, nombre)
                if os.path.exists(ruta):
                    pm = QPixmap(ruta)
                    if not pm.isNull():
                        self._imagenes[clave] = pm
                        break
        self.usar("standby")

    def usar(self, clave):
        pm = self._imagenes.get(clave) or self._imagenes.get("standby")
        if pm is None:
            self._original = None
            self.setStyleSheet(f"background: transparent; border: none; color: {GRIS}; font-family: monospace;")
            self.setText(T("sin_imagen"))
            return
        if pm is not self._original:
            self._original = pm
            self._reescalar()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._reescalar()

    def _reescalar(self):
        if self._original is not None:
            self.setPixmap(self._original.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    # ---- efecto glitch de aparición ----

    def glitch(self):
        self._glitch_activo = True
        self._ganim.start()

    def _glitch_paso(self, valor):
        self._g = float(valor)
        self.update()

    def _glitch_fin(self):
        self._glitch_activo = False
        self.update()

    def paintEvent(self, evento):
        pm = self.pixmap()
        if not self._glitch_activo or pm is None or pm.isNull():
            super().paintEvent(evento)
            return

        p = QPainter(self)
        g = 1.0 - self._g                       # intensidad: empieza fuerte y se calma
        p.setOpacity(min(1.0, self._g * 2.5))   # la imagen va apareciendo
        w, h = pm.width(), pm.height()
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2

        # franjas horizontales que se desplazan de lado
        trozos = 16
        alto = max(1, h // trozos)
        for i in range(trozos):
            sy = i * alto
            sh = alto if i < trozos - 1 else h - sy
            dx = 0
            if random.random() < 0.15 + 0.5 * g:
                tope = int(24 * g) + 1
                dx = random.randint(-tope, tope)
            p.drawPixmap(x + dx, y + sy, pm, 0, sy, w, sh)

        # líneas de barrido
        p.setOpacity(0.05 + 0.4 * g)
        for yy in range(y, y + h, 3):
            p.fillRect(x, yy, w, 1, QColor(0, 0, 0))

        # barras de color (cian y rosa)
        p.setOpacity(0.55 * g)
        for _ in range(2):
            if random.random() < 0.7:
                p.fillRect(x, y + random.randint(0, max(0, h - 6)), w, random.randint(2, 6),
                           QColor(random.choice([CIAN, ROSA])))
        p.end()


class Hablante(QThread):
    """Pide la respuesta a Ollama en segundo plano para que la ventana no se congele."""

    trozo = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, modelo, mensajes):
        super().__init__()
        self.modelo = modelo
        self.mensajes = mensajes
        self._parar = False

    def parar(self):
        self._parar = True

    def run(self):
        try:
            for t in chat_stream(self.modelo, self.mensajes, lambda: self._parar):
                self.trozo.emit(t)
        except Exception as e:
            self.error.emit(str(e))


class Ejecutor(QThread):
    """Ejecuta un comando en segundo plano y va enviando su salida."""

    linea = pyqtSignal(str)
    terminado = pyqtSignal(int)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        self.estado = {"proc": None, "cancelar": False}

    def cancelar(self):
        self.estado["cancelar"] = True
        proc = self.estado["proc"]
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def run(self):
        codigo = correr(self.cmd, self.linea.emit, self.estado)
        self.terminado.emit(codigo)


class Capri(QWidget):
    def __init__(self):
        super().__init__()
        self.modelo = elegir_modelo()
        self.historial = []
        self.worker = None
        self.ejecutor = None
        self.crudo = ""          # todo lo que ha dicho Capri en esta respuesta (con etiquetas)
        self.mostrado = ""       # lo que ya se escribió en el chat
        self.fallo = False
        self.detenido = False
        self.cmd_pendiente = None
        self.ultimo_pedido = ""
        self.n_lineas = 0
        self.ultimas = []
        self._intro_hecha = False
        self._mq_timer = None

        self.setWindowTitle("Capri")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(440, 740)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        self.panel = Marco(CIAN, esquinas=False)
        raiz.addWidget(self.panel)

        lay = QVBoxLayout(self.panel)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        # --- Barra superior ---
        barra = QHBoxLayout()
        titulo = QLabel(f'<span style="color:{ROSA}; font-weight:bold;">| CAPRI</span>'
                        f'&nbsp;&nbsp;<span style="color:{GRIS}; font-size:9px;">PERSONAL LINK</span>')
        titulo.setStyleSheet("font-family: monospace; font-size: 12px; background: transparent;")
        barra.addWidget(titulo)
        barra.addStretch()
        estilo_boton = (f"QPushButton {{ background: transparent; color: {CIAN}; border: none; "
                        f"font-family: monospace; font-size: 13px; padding: 2px 6px; }}"
                        f"QPushButton:hover {{ color: {ROSA}; }}")
        self.btn_lang = QPushButton(get_idioma().upper())
        self.btn_lang.setStyleSheet(estilo_boton)
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_lang.clicked.connect(self.cambiar_idioma)
        barra.addWidget(self.btn_lang)
        for simbolo, accion in (("—", self.showMinimized), ("✕", self.close)):
            b = QPushButton(simbolo)
            b.setStyleSheet(estilo_boton)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(accion)
            barra.addWidget(b)
        lay.addLayout(barra)

        linea = QFrame()
        linea.setFixedHeight(1)
        linea.setStyleSheet("background-color: rgba(46, 230, 214, 110); border: none;")
        lay.addWidget(linea)

        # --- Pantalla de carga (solo al arrancar) ---
        self.pantalla_carga = QWidget()
        lp = QVBoxLayout(self.pantalla_carga)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.addStretch()
        self.cargando = Cargando()
        lp.addWidget(self.cargando, 0, Qt.AlignmentFlag.AlignHCenter)
        etiqueta_carga = QLabel("CAPRI // THINKING")
        etiqueta_carga.setStyleSheet(f"color: {CIAN}; font-family: monospace; font-size: 9px; "
                                     f"border: 1px solid {CIAN}; padding: 3px 12px; background: rgba(4, 14, 22, 230);")
        lp.addWidget(etiqueta_carga, 0, Qt.AlignmentFlag.AlignHCenter)
        lp.addStretch()
        lay.addWidget(self.pantalla_carga, 7)

        # --- Conversación ---
        caja_chat = Marco(CIAN)
        lc = QVBoxLayout(caja_chat)
        lc.setContentsMargins(14, 12, 10, 12)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFrameStyle(0)
        self.log.setStyleSheet(
            f"QTextEdit {{ background: transparent; border: none; color: {TEXTO}; "
            f"font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 13px; }}"
            f"QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: {CIAN}; min-height: 24px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
        )
        lc.addWidget(self.log)
        self.lbl_replying = QLabel("REPLYING")
        self.lbl_replying.setStyleSheet(f"color: {AMARILLO}; font-family: monospace; font-size: 8px; background: transparent;")
        self.lbl_replying.hide()
        lc.addWidget(self.lbl_replying)
        self.caja_chat = caja_chat
        lay.addWidget(caja_chat, 3)

        # --- Tarjeta de confirmación de comandos (oculta hasta que Capri proponga uno) ---
        self.tarjeta = Marco(AMARILLO)
        lt = QVBoxLayout(self.tarjeta)
        lt.setContentsMargins(14, 10, 14, 10)
        lt.setSpacing(6)
        self.tarjeta_titulo = QLabel()
        self.tarjeta_titulo.setWordWrap(True)
        self.tarjeta_titulo.setStyleSheet(f"color: {AMARILLO}; font-family: monospace; font-size: 10px; background: transparent;")
        lt.addWidget(self.tarjeta_titulo)
        self.tarjeta_cmd = QLabel()
        self.tarjeta_cmd.setWordWrap(True)
        self.tarjeta_cmd.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.tarjeta_cmd.setStyleSheet(f"color: {TEXTO}; font-family: monospace; font-size: 12px; background: transparent;")
        lt.addWidget(self.tarjeta_cmd)
        botones = QHBoxLayout()
        botones.addStretch()
        self.btn_no = QPushButton(T("btn_cancelar"))
        self.btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_no.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_no.setStyleSheet(f"QPushButton {{ background: transparent; color: {ROSA}; border: 1px solid {ROSA}; "
                                  f"font-family: monospace; font-size: 11px; padding: 5px 12px; }}"
                                  f"QPushButton:hover {{ background: {ROSA}; color: {FONDO}; }}")
        self.btn_no.clicked.connect(self.cancelar_pendiente)
        botones.addWidget(self.btn_no)
        self.btn_ok = QPushButton(T("btn_ejecutar"))
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_ok.setStyleSheet(f"QPushButton {{ background: {CIAN}; color: {FONDO}; border: 1px solid {CIAN}; "
                                  f"font-family: monospace; font-size: 11px; font-weight: bold; padding: 5px 12px; }}"
                                  f"QPushButton:hover {{ background: {AMARILLO}; border: 1px solid {AMARILLO}; }}")
        self.btn_ok.clicked.connect(self.ejecutar_pendiente)
        botones.addWidget(self.btn_ok)
        lt.addLayout(botones)
        self.tarjeta.hide()
        lay.addWidget(self.tarjeta)

        # --- Imagen de Capri ---
        self.caja_img = Marco(CIAN)
        li = QVBoxLayout(self.caja_img)
        li.setContentsMargins(10, 8, 10, 10)
        li.setSpacing(4)
        self.etiqueta = QLabel()
        self.etiqueta.setStyleSheet(f"color: {AMARILLO}; font-family: monospace; font-size: 10px; background: transparent;")
        li.addWidget(self.etiqueta, 0, Qt.AlignmentFlag.AlignLeft)
        self.imagen = ImagenLabel()
        self.imagen.cargar()
        li.addWidget(self.imagen, 1)
        lay.addWidget(self.caja_img, 4)

        # --- Entrada ---
        fila = QHBoxLayout()
        self.entrada = QLineEdit()
        self.entrada.setPlaceholderText(T("placeholder"))
        self.entrada.setStyleSheet(
            f"QLineEdit {{ background: rgba(4, 14, 22, 230); color: {TEXTO}; border: 1px solid {CIAN}; "
            f"padding: 9px 10px; font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 13px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ROSA}; }}"
        )
        self.entrada.returnPressed.connect(self.enviar)
        fila.addWidget(self.entrada)
        enviar = QPushButton("↗")
        enviar.setFixedSize(38, 38)
        enviar.setCursor(Qt.CursorShape.PointingHandCursor)
        enviar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        enviar.setStyleSheet(f"QPushButton {{ background: {ROSA}; color: {FONDO}; border: none; font-size: 16px; font-weight: bold; }}"
                             f"QPushButton:hover {{ background: {CIAN}; }}")
        enviar.clicked.connect(self.enviar)
        fila.addWidget(enviar)
        lay.addLayout(fila)

        # --- Pie ---
        pie = QHBoxLayout()
        info = self.info = QLabel(T("modelo_pie", m=self.modelo))
        info.setStyleSheet(f"color: {GRIS}; font-family: monospace; font-size: 9px; background: transparent;")
        pie.addWidget(info)
        pie.addStretch()
        atajos = QLabel("ENTER ↵   ESC ■")
        atajos.setStyleSheet(f"color: {GRIS}; font-family: monospace; font-size: 9px; background: transparent;")
        pie.addWidget(atajos)
        lay.addLayout(pie)

        QShortcut(QKeySequence("Esc"), self).activated.connect(self._esc)

        # --- Secuencia de entrada: rueda de carga -> imagen con glitch -> saludo escrito ---
        self.caja_chat.hide()
        self.caja_img.hide()
        self.entrada.setEnabled(False)
        self.poner_estado("booting")

    def showEvent(self, evento):
        super().showEvent(evento)
        if not self._intro_hecha:
            self._intro_hecha = True
            self.cargando.iniciar()
            QTimer.singleShot(2000, self._fase_recibiendo)

    def _fase_recibiendo(self):
        self.cargando.detener()
        self.pantalla_carga.hide()
        self.caja_chat.show()
        self.caja_img.show()
        self.poner_estado("receiving")
        self.imagen.glitch()
        QTimer.singleShot(900, self._fase_saludo)

    def _fase_saludo(self):
        self.poner_estado("speaking")
        self.bloque("CAPRI", CIAN)
        self._mq_texto = T("saludo")
        self._mq_i = 0
        self._mq_timer = QTimer(self)
        self._mq_timer.timeout.connect(self._mq_paso)
        self._mq_timer.start(30)

    def _mq_paso(self):
        if self._mq_i >= len(self._mq_texto):
            self._mq_timer.stop()
            self.poner_estado("standby")
            self.entrada.setEnabled(True)
            self.entrada.setFocus()
            return
        self._insertar(self._mq_texto[self._mq_i])
        self._mq_i += 1

    # ---------- estado visual ----------

    def poner_estado(self, modo):
        textos = {
            "booting": "CAPRI // LINKING...",
            "receiving": "CAPRI // RECEIVING",
            "standby": "CAPRI // STANDBY",
            "thinking": "CAPRI // THINKING",
            "speaking": "CAPRI // SPEAKING",
            "waiting": "CAPRI // AWAITING OK",
            "executing": "CAPRI // EXECUTING SYS",
        }
        self.etiqueta.setText(textos[modo])
        self.caja_img.pulsar(modo in ("receiving", "thinking", "speaking", "executing"))
        self.imagen.usar("executing" if modo == "executing" else "standby")
        self.lbl_replying.setVisible(modo in ("thinking", "speaking"))

    # ---------- chat ----------

    def bloque(self, quien, color, texto=""):
        """Agrega un mensaje al chat: nombre pequeño de color y debajo el texto."""
        self.log.append(f'<div style="margin-top:10px;"><span style="color:{color}; font-family:monospace; '
                        f'font-size:10px;">{quien}</span></div>')
        self.log.append(html.escape(texto) if texto else "")
        self._bajar()

    def _bajar(self):
        barra = self.log.verticalScrollBar()
        barra.setValue(barra.maximum())

    def _ocupado(self):
        return ((self.worker is not None and self.worker.isRunning())
                or (self.ejecutor is not None and self.ejecutor.isRunning()))

    def enviar(self):
        texto = self.entrada.text().strip()
        if not texto or self._ocupado():
            return
        if texto.lower() in ("exit", "quit", "salir"):
            self.close()
            return

        if self.cmd_pendiente or self.tarjeta.isVisible():
            self.cancelar_pendiente(silencioso=True)

        self.entrada.clear()
        self.ultimo_pedido = texto
        self.historial.append({"role": "user", "content": texto})
        self.bloque("YOU", ROSA, texto)
        self.bloque("CAPRI", CIAN)
        self.crudo = ""
        self.mostrado = ""
        self.fallo = False
        self.detenido = False
        self.poner_estado("thinking")

        mensajes = [{"role": "system", "content": prompt_sistema()}] + self.historial[-MAX_MENSAJES:]
        self.worker = Hablante(self.modelo, mensajes)
        self.worker.trozo.connect(self.al_llegar_trozo)
        self.worker.error.connect(self.al_error)
        self.worker.finished.connect(self.al_terminar)
        self.worker.start()

    def _insertar(self, texto):
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(texto)
        self._bajar()

    def al_llegar_trozo(self, texto):
        texto = limpiar(texto)
        if not texto:
            return
        self.crudo += texto
        visible = visible_hasta_etiqueta(self.crudo).lstrip()
        nuevo = visible[len(self.mostrado):]
        if not nuevo:
            return
        if not self.mostrado:
            self.poner_estado("speaking")
        self.mostrado = visible
        self._insertar(nuevo)

    def al_error(self, mensaje):
        self.fallo = True
        self.log.append(f'<span style="color:{ROSA};">[!] {html.escape(mensaje)}</span>')
        self._bajar()

    def al_terminar(self):
        # Si quedó retenido algo que parecía el inicio de una etiqueta pero no lo era, se escribe ahora.
        completo = self.crudo.lstrip()
        if "<cmd>" in completo:
            completo = completo.split("<cmd>")[0]
        resto = completo[len(self.mostrado):]
        if resto:
            self._insertar(resto)

        if self.crudo.strip():
            self.historial.append({"role": "assistant", "content": self.crudo.strip()})
        elif self.fallo and self.historial and self.historial[-1]["role"] == "user":
            self.historial.pop()  # no se respondió: no lo dejamos en la memoria

        self.poner_estado("standby")
        self.entrada.setFocus()

        if self.fallo or self.detenido:
            return
        cmd = extraer_comando(self.crudo)
        if cmd:
            self.mostrar_tarjeta(cmd)
        elif "<cmd>" in self.crudo:
            self.al_error(T("err_cortado"))

    # ---------- comandos ----------

    def mostrar_tarjeta(self, cmd):
        motivo = peligroso(cmd)
        self.tarjeta_cmd.setText("$ " + cmd)
        if motivo:
            self.cmd_pendiente = None
            self.tarjeta_titulo.setText(T("bloqueado", motivo=motivo))
            self.btn_ok.hide()
            self.btn_no.setText(T("btn_cerrar"))
            self.historial.append({"role": "user", "content": f"[System] Command blocked for safety ({motivo}). It was not run."})
        else:
            self.cmd_pendiente = cmd
            titulo = T("tarjeta_titulo")
            avisos = advertencias(cmd) + revisar_paquetes(cmd, self.ultimo_pedido)
            if avisos:
                titulo += "\n" + "\n".join("! " + a for a in avisos)
            self.tarjeta_titulo.setText(titulo)
            self.btn_ok.show()
            self.btn_no.setText(T("btn_cancelar"))
            self.poner_estado("waiting")
        self.tarjeta.show()

    def cancelar_pendiente(self, silencioso=False):
        habia = self.cmd_pendiente is not None
        self.tarjeta.hide()
        self.cmd_pendiente = None
        if not habia:
            return
        self.historial.append({"role": "user", "content": "[System] The user cancelled the command; it was not run."})
        if not silencioso:
            self.log.append(f'<span style="color:{GRIS}; font-family:monospace; font-size:11px;">{html.escape(T("cancelado"))}</span>')
            self._bajar()
            self.poner_estado("standby")

    def ejecutar_pendiente(self):
        cmd = self.cmd_pendiente
        if not cmd or self._ocupado():
            return
        self.tarjeta.hide()
        self.cmd_pendiente = None
        self.log.append(f'<div style="margin-top:10px;"><span style="color:{AMARILLO}; font-family:monospace; '
                        f'font-size:10px;">SYSTEM // EXEC</span></div>')
        self.log.append(f'<span style="color:{AMARILLO}; font-family:monospace; font-size:12px;">$ {html.escape(cmd)}</span>')
        self._bajar()
        self.n_lineas = 0
        self.ultimas = []
        self.poner_estado("executing")

        self.ejecutor = Ejecutor(cmd)
        self.ejecutor.linea.connect(self.al_salida)
        self.ejecutor.terminado.connect(self.al_fin_comando)
        self.ejecutor.start()

    def al_salida(self, linea):
        self.ultimas = (self.ultimas + [linea])[-12:]
        self.n_lineas += 1
        # Las líneas de error se muestran siempre, aunque la salida ya se haya recortado.
        es_error = re.match(r"\s*(E:|Err[: ]|Error|dpkg: error|W:)", linea) is not None
        if self.n_lineas <= 150 or es_error:
            color = ROSA if es_error else GRIS
            self.log.append(f'<span style="color:{color}; font-family:monospace; font-size:11px;">{html.escape(linea[:300])}</span>')
        elif self.n_lineas == 151:
            self.log.append(f'<span style="color:{GRIS}; font-family:monospace; font-size:11px;">'
                            f'{html.escape(T("salida_recortada"))}</span>')
        self._bajar()

    def al_fin_comando(self, codigo):
        if self.n_lineas > 150 and self.ultimas:
            self.log.append(f'<span style="color:{GRIS}; font-family:monospace; font-size:10px;">{html.escape(T("final_salida"))}</span>')
            for l in self.ultimas[-8:]:
                self.log.append(f'<span style="color:{GRIS}; font-family:monospace; font-size:11px;">{html.escape(l[:300])}</span>')
        if codigo == 0:
            texto, color = T("res_ok"), CIAN
        elif codigo == -2:
            texto, color = T("res_cancelado"), ROSA
        elif codigo in (126, 127) and not self.ultimas:
            texto, color = T("res_no_auth"), ROSA
        elif codigo == -1:
            texto, color = T("res_no_pudo"), ROSA
        else:
            texto, color = T("res_error", codigo=codigo), ROSA
            if codigo == 100:
                texto += T("res_pista100")
        self.log.append(f'<span style="color:{color}; font-family:monospace; font-size:11px;">{html.escape(texto)}</span>')
        self._bajar()

        salida = "\n".join(self.ultimas)[-600:]
        self.historial.append({"role": "user", "content": f"[System] The command finished with exit code {codigo}. End of the output:\n{salida}"})
        self.poner_estado("standby")
        self.entrada.setFocus()

    # ---------- idioma ----------

    def aplicar_idioma(self):
        self.btn_lang.setText(get_idioma().upper())
        self.entrada.setPlaceholderText(T("placeholder"))
        self.info.setText(T("modelo_pie", m=self.modelo))
        self.btn_ok.setText(T("btn_ejecutar"))
        bloqueada = self.tarjeta.isVisible() and not self.btn_ok.isVisible()
        self.btn_no.setText(T("btn_cerrar") if bloqueada else T("btn_cancelar"))

    def cambiar_idioma(self):
        codigos = list(IDIOMAS)
        nuevo = codigos[(codigos.index(get_idioma()) + 1) % len(codigos)]
        set_idioma(nuevo)
        guardar_config({"idioma": nuevo})
        self.aplicar_idioma()
        self.log.append(f'<span style="color:{GRIS}; font-family:monospace; font-size:11px;">[LANG] {IDIOMAS[nuevo]}</span>')
        self._bajar()

    # ---------- ventana ----------

    def _esc(self):
        if self.worker is not None and self.worker.isRunning():
            self.detenido = True
            self.worker.parar()
        elif self.ejecutor is not None and self.ejecutor.isRunning():
            if self.ejecutor.cmd.strip().startswith("sudo "):
                self.log.append(f'<span style="color:{ROSA}; font-family:monospace; font-size:11px;">{html.escape(T("esc_sudo"))}</span>')
                self._bajar()
            else:
                self.ejecutor.cancelar()
        elif self.tarjeta.isVisible():
            self.cancelar_pendiente()
        else:
            self.close()

    def mousePressEvent(self, evento):
        # Arrastrar la ventana sin bordes (funciona en X11 y en Wayland)
        if evento.button() == Qt.MouseButton.LeftButton and self.windowHandle():
            self.windowHandle().startSystemMove()

    def closeEvent(self, evento):
        if self._mq_timer is not None:
            self._mq_timer.stop()
        if self.worker is not None and self.worker.isRunning():
            self.worker.parar()
            if not self.worker.wait(1500):
                self.worker.terminate()
                self.worker.wait()
        if self.ejecutor is not None and self.ejecutor.isRunning():
            self.ejecutor.cancelar()
            if not self.ejecutor.wait(2000):
                self.ejecutor.terminate()
                self.ejecutor.wait()
        super().closeEvent(evento)


def main():
    global MODELO
    parser = argparse.ArgumentParser(description="Capri - cyberpunk AI terminal overlay")
    parser.add_argument("--lang", choices=list(IDIOMAS), help="interface and reply language")
    parser.add_argument("--model", help=f"Ollama model name (default: {MODELO})")
    args, qt_args = parser.parse_known_args()
    if args.model:
        MODELO = args.model
    set_idioma(args.lang or cargar_config().get("idioma") or idioma_del_sistema())

    app = QApplication([sys.argv[0]] + qt_args)
    ventana = Capri()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
