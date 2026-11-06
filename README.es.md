<div align="center">

# CAPRI

**Un HUD ciberpunk flotante con un asistente de IA local que puede ejecutar comandos en tu PC con Linux, pero solo después de que tú los apruebes.**

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)
![Ollama](https://img.shields.io/badge/IA-Ollama%20(local)-000000)
![Plataforma](https://img.shields.io/badge/plataforma-Linux-FCC624?logo=linux&logoColor=black)
![Licencia](https://img.shields.io/badge/licencia-MIT-blue)

[English](README.md) · [Español](README.es.md)

</div>

<!-- Agrega aquí una captura o un GIF cuando lo tengas:
![Captura de Capri](docs/screenshot.png)
-->

---

## Descripción

Capri es un asistente de escritorio con una interfaz HUD ciberpunk. Habla con un modelo de lenguaje que corre **por completo en tu equipo** a través de [Ollama](https://ollama.com), así que no hay claves de API, ni nube, ni límites de uso. Cuando le pides algo en tu PC ("instala vlc", "¿cuánto espacio libre tengo?"), Capri propone el comando exacto, lo muestra en una tarjeta de confirmación y **no hace nada hasta que pulses EJECUTAR**.

Está pensado para ser ligero: se desarrolló y probó en un portátil con 8 GB de RAM y sin GPU, con un modelo Qwen de 4B parámetros.

## Características

- **IA 100% local** con Ollama. Funciona sin internet una vez descargado el modelo.
- **Ejecución de comandos con confirmación.** Cada comando pasa por una tarjeta que debes aprobar.
- **Revisiones de seguridad antes de aprobar:**
  - Los comandos destructivos (`rm -rf /`, `mkfs`, `dd` sobre discos, fork bombs...) se bloquean.
  - Avisos para `sudo`, para comandos que actualizan todo el sistema y para instalaciones tipo `curl ... | sh`.
  - En `apt install`, comprueba que el paquete exista y avisa de errores al escribir (por ejemplo, sugiere `asciiquarium` si escribiste `asciicuarium`).
- **Permisos de administrador sin compartir tu contraseña.** Los comandos con `sudo` se ejecutan con `pkexec`, así que el sistema muestra su propia ventana de contraseña. La contraseña nunca pasa por Capri ni por el modelo.
- **Tres idiomas:** inglés, español y portugués. Se cambia con el botón `ES / EN / PT`; el idioma de la interfaz y el de las respuestas cambian juntos y la elección se recuerda.
- **Respuestas en streaming** y memoria de la conversación.
- **Interfaz HUD:** animación de arranque, efectos glitch, etiquetas de estado y ventana sin bordes que se puede arrastrar.
- **Salida de comandos legible.** Las salidas largas se recortan, pero los errores y las últimas líneas siempre se muestran.

## Cómo funciona

```
 tú ──► Capri ──► modelo local (Ollama) ──► propone un comando
                                                   │
                      tarjeta de confirmación ◄────┘
                              │  (EJECUTAR / CANCELAR)
                              ▼
                    bash  (o pkexec para sudo)  ──►  la salida vuelve al chat
```

## Requisitos

| Requisito | Notas |
|---|---|
| Linux | Probado en Pop!_OS (base Ubuntu 24.04, escritorio COSMIC). Las sugerencias de comandos suponen una distribución basada en `apt` |
| Python | Se recomienda 3.10+ (desarrollado y probado en 3.12) |
| PyQt6 | Se instala desde `requirements.txt` |
| [Ollama](https://ollama.com) | Corriendo en local con al menos un modelo |
| `pkexec` | Solo para comandos con `sudo`. Viene con polkit en la mayoría de escritorios |
| RAM | Unos 4 GB libres para el modelo de 4B. Los modelos más pequeños necesitan menos |

## Instalación

### 1. Paquetes del sistema (Debian / Ubuntu / Pop!_OS / Mint)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
```

<details>
<summary>Otras distribuciones</summary>

```bash
# Arch / Manjaro
sudo pacman -S python python-pip git
# Fedora
sudo dnf install python3 python3-pip git
# openSUSE
sudo zypper install python3 python3-pip git
```

Las sugerencias de comandos y la revisión de paquetes de Capri están escritas para `apt`. En otras distribuciones la interfaz funciona, pero conviene editar `REGLAS_COMANDOS` en `capri.py` para describir tu gestor de paquetes.
</details>

### 2. Instalar Ollama y descargar un modelo

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:4b
```

Comprueba los nombres exactos de los modelos en [ollama.com/library](https://ollama.com/library). Capri está pensada para funcionar con cualquier modelo de chat disponible en Ollama; se desarrolló y probó con Qwen.

### 3. Obtener Capri

```bash
git clone https://github.com/shuriken292/capri-terminal-github.git
cd capri-terminal-github
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Ejecutar

```bash
python3 capri.py
```

## Uso

Escribe en la barra de abajo y pulsa **Enter**.

| Dices | Qué pasa |
|---|---|
| `¿cuánto espacio libre tengo en el disco?` | Capri propone `df -h`, lo apruebas y la salida aparece en el chat |
| `instala htop` | Capri propone `sudo apt install -y htop` y el sistema te pide la contraseña |
| `actualiza btop` | Capri propone `sudo apt install --only-upgrade -y btop` |

**Teclas**

| Tecla | Acción |
|---|---|
| `Enter` | Enviar el mensaje |
| `Esc` | Detener la respuesta, o cerrar la tarjeta de confirmación, o cerrar la ventana |
| `exit` / `quit` / `salir` | Cerrar Capri |

**Lee siempre la tarjeta antes de pulsar EJECUTAR.** Un modelo local pequeño puede leer mal un nombre o armar un comando equivocado; la tarjeta es tu protección.

### Idioma

Pulsa el botón de idioma en la barra de título (`ES`, `EN`, `PT`) para cambiarlo. La elección se guarda en `~/.config/capri/config.json`. También puedes forzarlo desde la línea de comandos:

```bash
python3 capri.py --lang en
python3 capri.py --lang es
python3 capri.py --lang pt
```

Si no hay nada configurado, Capri usa el idioma de tu sistema y, si no lo soporta, inglés.

### Opciones de línea de comandos

| Opción | Descripción |
|---|---|
| `--lang {es,en,pt}` | Idioma de la interfaz y de las respuestas |
| `--model NOMBRE` | Modelo de Ollama a usar (sobrescribe `MODELO`) |

## Configuración

Edita el bloque **SETTINGS** al inicio de `capri.py`:

| Ajuste | Por defecto | Descripción |
|---|---|---|
| `MODELO` | `qwen3.5:4b` | Nombre del modelo como sale en `ollama list`. Si no está instalado, Capri usa otro modelo Qwen instalado |
| `MAX_MENSAJES` | `14` | Mensajes recientes que recuerda Capri. Más memoria significa respuestas más lentas |
| `MAX_TOKENS` | `256` | Largo máximo de cada respuesta |
| `IMAGENES` | `capri.png`, `capri_standby.jpeg`... | Imagen del personaje, buscada junto a `capri.py`. Un PNG transparente se ve mejor |
| `IMAGENES_EJEC` | `capri_executing.jpeg`... | Imagen opcional que se muestra mientras corre un comando |

### Elegir un modelo para equipos modestos

| Equipo | Sugerencia |
|---|---|
| 8 GB de RAM, solo CPU | Un modelo de 4B (probado). La primera respuesta tarda más mientras se carga el modelo; las siguientes son más rápidas |
| 4 GB de RAM o CPU lenta | Un modelo más pequeño (2B o menos) |
| 16 GB de RAM o una GPU | Un modelo más grande para que acierte más con los comandos |

## Seguridad

Capri puede ejecutar comandos en tu computador, así que lee esta sección.

- **Nada se ejecuta sin tu aprobación.** No existe un modo automático.
- Una lista de bloqueo rechaza los comandos claramente destructivos, pero es una red de seguridad, no una garantía. **Tú eres responsable de lo que apruebas.**
- Un modelo de lenguaje puede equivocarse, sobre todo los pequeños. Revisa el comando de la tarjeta cada vez, en especial si lleva `sudo`, `upgrade`, `rm` o `| sh`.
- Los comandos con permisos de administrador **no se pueden detener desde Capri** (ese proceso pertenece al sistema). Espera a que terminen; interrumpir `apt` a mitad puede dejar paquetes a medias (`sudo dpkg --configure -a` lo repara).
- Úsalo bajo tu propia responsabilidad. Consulta la [licencia](LICENSE).

## Estructura del proyecto

```
capri-terminal-github/
├── capri.py               # toda la aplicación
├── capri_standby.jpeg     # imagen del personaje (reposo)
├── capri_executing.jpeg   # imagen del personaje (mientras corre un comando)
├── requirements.txt
├── README.md · README.es.md
└── LICENSE
```

## Agregar un idioma

1. En `capri.py`, agrega un código y un nombre a `IDIOMAS`, por ejemplo `"fr": "Français"`.
2. Copia un bloque de `TEXTOS` (por ejemplo `"en"`) y traduce todos los valores. Deja las claves y los `{marcadores}` como están. Si falta una clave, Capri usa el inglés.
3. Los pull requests son bienvenidos.

## Solución de problemas

| Problema | Solución |
|---|---|
| `No puedo conectar con Ollama` | Inícialo con `ollama serve` (o revisa `systemctl status ollama`) |
| `No encuentro el modelo ...` | Ejecuta `ollama list` y pon el nombre exacto en `MODELO`, o usa `--model` |
| `Could not load the Qt platform plugin "xcb"` | `sudo apt install libxcb-cursor0` |
| La ventana no se mantiene siempre encima | Algunos compositores Wayland ignoran esa opción. Es solo estético |
| `apt` falla con código 100 | Busca las líneas que empiezan con `E:` en la salida. Capri siempre las muestra |
| Capri tarda en la primera respuesta | El modelo se está cargando en la RAM. Las siguientes son más rápidas |

## Hoja de ruta

- [ ] Voz de Capri (síntesis de voz sin conexión, por ejemplo Piper)
- [ ] Reconocimiento de tu voz (sin conexión)
- [ ] Sprite del personaje con fondo transparente y animaciones en reposo
- [ ] Soporte para otros gestores de paquetes (`dnf`, `pacman`, `zypper`)
- [ ] Más idiomas

## Créditos y aviso legal

Capri es un **proyecto de fans, no oficial y sin fines de lucro**. El personaje Capri y *Cyberpunk: Edgerunners* pertenecen a sus respectivos dueños (CD PROJEKT RED, Studio Trigger y Netflix). Este proyecto no está afiliado, respaldado ni patrocinado por ellos. Las imágenes del personaje incluidas en este repositorio se usan solo a modo ilustrativo y siguen siendo propiedad de sus dueños; si reutilizas o redistribuyes este proyecto, reemplázalas por tu propio arte.

La idea se inspiró en el compañero de escritorio Capri que muestra [@overyx2 en TikTok](https://www.tiktok.com/@overyx2/video/7700585401852906753). Este repositorio es una implementación independiente y no comparte código con él.

## Licencia

El código fuente se publica bajo la [Licencia MIT](LICENSE). El arte del personaje no está cubierto por ella.
