<div align="center">

# CAPRI

**A floating cyberpunk HUD with a local AI assistant that can run commands on your Linux PC, but only after you approve them.**

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)
![Ollama](https://img.shields.io/badge/AI-Ollama%20(local)-000000)
![Platform](https://img.shields.io/badge/platform-Linux-FCC624?logo=linux&logoColor=black)
![License](https://img.shields.io/badge/license-MIT-blue)

[English](README.md) · [Español](README.es.md)

</div>

<!-- Add a screenshot or GIF here once you have one:
![Capri screenshot](docs/screenshot.png)
-->

---

## Overview

Capri is a desktop assistant with a cyberpunk HUD interface. It talks to a language model that runs **entirely on your machine** through [Ollama](https://ollama.com), so there are no API keys, no cloud and no usage limits. When you ask it to do something on your PC ("install vlc", "how much disk space do I have?"), Capri proposes the exact shell command, shows it on a confirmation card, and **does nothing until you press RUN**.

It is designed to be light: it was developed and tested on a laptop with 8 GB of RAM and no GPU, using a 4B-parameter Qwen model.

## Features

- **100% local AI** through Ollama. Works offline once the model is downloaded.
- **Command execution with confirmation.** Every command goes through a card you must approve.
- **Safety checks before you approve:**
  - Destructive commands (`rm -rf /`, `mkfs`, `dd` onto disks, fork bombs...) are blocked outright.
  - Warnings for `sudo`, for commands that upgrade the whole system, and for `curl ... | sh` style installs.
  - For `apt install`, it checks that the package exists and warns about typos (for example, it suggests `asciiquarium` if you typed `asciicuarium`).
- **Administrator rights without sharing your password.** `sudo` commands run through `pkexec`, so the system shows its own password dialog. The password never goes through Capri or the model.
- **Three languages:** English, Spanish and Portuguese. Switch with the `ES / EN / PT` button; the reply language and the UI change together and the choice is remembered.
- **Streaming replies** and conversation memory.
- **HUD interface:** boot animation, glitch effects, status tags, a draggable frameless window.
- **Readable command output.** Long outputs are trimmed, but errors and the final lines are always shown.

## How it works

```
 you ──► Capri ──► local model (Ollama) ──► proposes a command
                                                   │
                       confirmation card ◄─────────┘
                              │  (RUN / CANCEL)
                              ▼
                    bash  (or pkexec for sudo)  ──►  output back in the chat
```

## Requirements

| Requirement | Notes |
|---|---|
| Linux | Tested on Pop!_OS (Ubuntu 24.04 base, COSMIC desktop). Command suggestions assume an `apt`-based distribution. |
| Python | 3.10+ recommended (developed and tested on 3.12) |
| PyQt6 | Installed from `requirements.txt` |
| [Ollama](https://ollama.com) | Running locally with at least one model |
| `pkexec` | Only for `sudo` commands. Included with polkit on most desktops |
| RAM | About 4 GB free for the 4B model. Smaller models need less |

## Installation

### 1. System packages (Debian / Ubuntu / Pop!_OS / Mint)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
```

<details>
<summary>Other distributions</summary>

```bash
# Arch / Manjaro
sudo pacman -S python python-pip git
# Fedora
sudo dnf install python3 python3-pip git
# openSUSE
sudo zypper install python3 python3-pip git
```

Capri's command suggestions and package checks are written for `apt`. On other distributions the interface works, but you should edit `REGLAS_COMANDOS` in `capri.py` to describe your package manager.
</details>

### 2. Install Ollama and download a model

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:4b
```

Check the exact model names at [ollama.com/library](https://ollama.com/library). Capri is designed to work with any chat model available in Ollama; it was developed and tested with Qwen.

### 3. Get Capri

```bash
git clone https://github.com/shuriken292/capri-terminal-github.git
cd capri-terminal-github
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run

```bash
python3 capri.py
```

## Usage

Type in the bar at the bottom and press **Enter**.

| Say | What happens |
|---|---|
| `how much free disk space do I have?` | Capri proposes `df -h`, you approve, the output appears in the chat |
| `install htop` | Capri proposes `sudo apt install -y htop`, the system asks for your password |
| `update btop` | Capri proposes `sudo apt install --only-upgrade -y btop` |

**Keys**

| Key | Action |
|---|---|
| `Enter` | Send the message |
| `Esc` | Stop the reply, or close the confirmation card, or close the window |
| `exit` / `quit` | Close Capri |

**Always read the card before pressing RUN.** A small local model can misread a name or build a wrong command; the card is your protection.

### Language

Click the language button in the title bar (`ES`, `EN`, `PT`) to switch. The choice is saved in `~/.config/capri/config.json`. You can also force it from the command line:

```bash
python3 capri.py --lang en
python3 capri.py --lang es
python3 capri.py --lang pt
```

If nothing is set, Capri uses your system language and falls back to English.

### Command-line options

| Option | Description |
|---|---|
| `--lang {es,en,pt}` | Interface and reply language |
| `--model NAME` | Ollama model to use (overrides `MODELO`) |

## Configuration

Edit the **SETTINGS** block at the top of `capri.py`:

| Setting | Default | Description |
|---|---|---|
| `MODELO` | `qwen3.5:4b` | Model name as shown by `ollama list`. If it is not installed, Capri uses another installed Qwen model |
| `MAX_MENSAJES` | `14` | Recent messages Capri remembers. More memory means slower replies |
| `MAX_TOKENS` | `256` | Maximum reply length |
| `IMAGENES` | `capri.png`, `capri_standby.jpeg`... | Character image, looked up next to `capri.py`. A transparent PNG looks best |
| `IMAGENES_EJEC` | `capri_executing.jpeg`... | Optional image shown while a command is running |

### Choosing a model for low-end hardware

| Hardware | Suggestion |
|---|---|
| 8 GB RAM, CPU only | A 4B model (tested). The first reply is slower while the model loads; later replies are faster |
| 4 GB RAM or slow CPU | A smaller model (2B or less) |
| 16 GB RAM or a GPU | A larger model for better command accuracy |

## Safety

Capri can run commands on your computer, so please read this section.

- **Nothing runs without your approval.** There is no auto-run mode.
- A blocklist refuses clearly destructive commands, but it is a safety net, not a guarantee. **You are responsible for what you approve.**
- A language model can make mistakes, especially small ones. Check the command on the card every time, particularly anything with `sudo`, `upgrade`, `rm` or `| sh`.
- Commands that run with administrator rights **cannot be stopped from Capri** (the system owns that process). Wait for them to finish; interrupting `apt` halfway can leave packages half-installed (`sudo dpkg --configure -a` repairs that).
- Use at your own risk. See the [license](LICENSE).

## Project structure

```
capri-terminal-github/
├── capri.py               # the whole application
├── capri_standby.jpeg     # character image (idle)
├── capri_executing.jpeg   # character image (while a command runs)
├── requirements.txt
├── README.md · README.es.md
└── LICENSE
```

## Adding a language

1. In `capri.py`, add a code and name to `IDIOMAS`, for example `"fr": "Français"`.
2. Copy one block of `TEXTOS` (for example `"en"`) and translate every value. Keep the keys and the `{placeholders}` unchanged. If a key is missing, Capri falls back to English.
3. Pull requests are welcome.

## Troubleshooting

| Problem | Solution |
|---|---|
| `Can't connect to Ollama` | Start it with `ollama serve` (or `systemctl status ollama`) |
| `Model ... not found` | Run `ollama list` and put the exact name in `MODELO`, or use `--model` |
| `Could not load the Qt platform plugin "xcb"` | `sudo apt install libxcb-cursor0` |
| The window is not always on top | Some Wayland compositors ignore that hint. It is cosmetic |
| `apt` fails with code 100 | Look for the lines starting with `E:` in the output. Capri always shows them |
| Capri is slow to answer the first time | The model is loading into RAM. Later answers are faster |

## Roadmap

- [ ] Voice output (offline TTS, for example Piper)
- [ ] Voice input (offline speech recognition)
- [ ] Transparent character sprite and idle animations
- [ ] Support for other package managers (`dnf`, `pacman`, `zypper`)
- [ ] More languages

## Credits and disclaimer

Capri is an **unofficial, non-commercial fan project**. The character Capri and *Cyberpunk: Edgerunners* belong to their respective owners (CD PROJEKT RED, Studio Trigger and Netflix). This project is not affiliated with, endorsed by or sponsored by them. The character images included in this repository are used for illustration only and remain the property of their owners; if you reuse or redistribute this project, replace them with your own artwork.

The idea was inspired by the Capri desktop companion shown by [@overyx2 on TikTok](https://www.tiktok.com/@overyx2/video/7700585401852906753). This repository is an independent implementation and shares no code with it.

## License

The source code is released under the [MIT License](LICENSE). The character artwork is not covered by it.
