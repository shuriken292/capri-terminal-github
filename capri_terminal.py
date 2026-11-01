import sys
import subprocess
import os
import json
import urllib.request
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QLineEdit
from PyQt6.QtGui import QPixmap, QMovie
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QVariantAnimation, QEasingCurve

# Hilo secundario para consultas locales a Ollama
class AIWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.2:1b",
            "prompt": f"Responde en español, de forma breve, útil y con un tono ciberpunk/casual a esto: {self.prompt}",
            "stream": False
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                self.finished.emit(result.get("response", "Capri no obtuvo respuesta."))
        except Exception as e:
            self.finished.emit(f"CAPRI LOCAL ERROR: ¿Está corriendo Ollama? ({str(e)})")

class CapriTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("CAPRI // AI OVERLAY (LOCAL)")
        self.setFixedSize(520, 680)
        self.setStyleSheet("background-color: #0d0d0d; color: #00ffcc;")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        main_layout = QVBoxLayout()

        # 1. VISOR DE CAPRI
        self.image_label = QLabel(self)
        self.movie = None
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #ffff00; background-color: #1a001a;")
        main_layout.addWidget(self.image_label)

        # 2. PANEL DE LOGS
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(
            "background-color: #050505; "
            "color: #00ffcc; "
            "font-family: monospace; "
            "font-size: 13px; "
            "border: 2px solid #00ffcc;"
        )
        self.log_output.append("[SYSTEM] Enlazado al Motor Local de Ollama (Offline Mode).")
        self.log_output.append("[CAPRI // STANDBY] Sistemas 100% operativos, we. ¿Qué hacemos?\n")
        main_layout.addWidget(self.log_output)

        # 3. LÍNEA DE COMANDOS
        self.command_input = QLineEdit(self)
        self.command_input.setPlaceholderText("Escribe algo a Capri o 'exec [cmd]'...")
        self.command_input.setStyleSheet(
            "background-color: #101010; "
            "color: #ff007f; "
            "font-family: monospace; "
            "font-size: 14px; "
            "border: 2px solid #ff007f; "
            "padding: 8px;"
        )
        self.command_input.returnPressed.connect(self.procesar_entrada)
        main_layout.addWidget(self.command_input)

        self.setLayout(main_layout)
        self.cambiar_sprite("standby")

    def cambiar_sprite(self, estado):
        if self.movie:
            self.movie.stop()
            self.movie = None

        h_target = 680

        if estado == "talking":
            self.movie = QMovie("capri_talking.gif")
            if self.movie.isValid():
                self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
                self.image_label.setMovie(self.movie)
                self.movie.start()
                h_target = 720
            else:
                self.image_label.setText("[!] Falta: capri_talking.gif")
        elif estado == "executing":
            pixmap = QPixmap("capri_executing.jpeg")
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(480, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                h_target = 640
            else:
                self.image_label.setText("[!] Falta: capri_executing.jpeg")
        else:
            pixmap = QPixmap("capri_standby.jpeg")
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(480, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                h_target = 680
            else:
                self.image_label.setText("[!] Falta: capri_standby.jpeg")

        self.animar_tamano(h_target)

    def animar_tamano(self, nueva_altura):
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setStartValue(self.height())
        self.anim.setEndValue(nueva_altura)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(lambda val: self.setFixedSize(520, int(val)))
        self.anim.start()

    def procesar_entrada(self):
        cmd = self.command_input.text().strip()
        if not cmd:
            return

        self.log_output.append(f"> user: {cmd}")
        self.command_input.clear()

        if cmd.lower() == "exit":
            QApplication.quit()
        elif cmd.lower() == "clear":
            self.log_output.clear()
            self.cambiar_sprite("standby")
        elif cmd.startswith("exec "):
            self.cambiar_sprite("executing")
            real_cmd = cmd.replace("exec ", "", 1)
            try:
                resultado = subprocess.check_output(real_cmd, shell=True, text=True, stderr=subprocess.STDOUT)
                self.log_output.append(f"RESULT (LOCAL):\n{resultado}")
            except Exception as e:
                self.log_output.append(f"ERROR: {str(e)}\n")
            self.cambiar_sprite("standby")
        else:
            self.cambiar_sprite("talking")
            self.worker = AIWorker(cmd)
            self.worker.finished.connect(self.mostrar_respuesta_ia)
            self.worker.start()

    def mostrar_respuesta_ia(self, texto):
        self.log_output.append(f"CAPRI:\n{texto.strip()}\n")
        self.cambiar_sprite("standby")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    terminal = CapriTerminal()
    terminal.show()
    sys.exit(app.exec())
