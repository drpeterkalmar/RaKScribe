# ⚙️ Installations- und Einrichtungsanleitung (Offline-Version)

RaKScribe 2.0 läuft vollständig lokal auf Ihrem Rechner. Es sind keine Cloud-Abonnements oder API-Keys mehr erforderlich.

---

## 1. Systemvoraussetzungen 💻

Um STT (Spracherkennung) und LLM (Strukturierung) gleichzeitig flüssig zu betreiben, wird folgende Hardware empfohlen:

* **GPU:** NVIDIA Grafikkarte mit mind. **8 GB VRAM** (z.B. RTX 3070 Ti, 4060 oder besser).
* **RAM:** Mind. 16 GB Arbeitsspeicher.
* **Betriebssystem:** Windows 10/11 (bevorzugt).
* **Python:** Version 3.12 oder neuer.

---

## 2. Software-Komponenten installieren 📦

### A. Ollama (Das LLM-Backend)
1. Laden Sie Ollama von [ollama.com](https://ollama.com) herunter und installieren Sie es.
2. Öffnen Sie ein Terminal (PowerShell) und laden Sie das benötigte Sprachmodell:
   ```powershell
   ollama pull gemma4:e4b
   ```

### B. Python-Abhängigkeiten
Navigieren Sie in den Projektordner und installieren Sie die Bibliotheken:
```powershell
pip install -r requirements.txt
```

### C. Audio-Treiber testen
Stellen Sie sicher, dass Ihr Mikrofon erkannt wird:
```powershell
python -m sounddevice
```

---

## 3. Konfiguration einrichten 🛠️

RaKScribe nutzt eine `config.ini` Datei für alle Einstellungen.

1. Erstellen Sie eine Datei namens **`config.ini`** im Hauptverzeichnis (falls nicht vorhanden).
2. Fügen Sie folgenden Inhalt ein:

```ini
[SETTINGS]
OLLAMA_URL = http://localhost:11434
LLM_MODEL = gemma4:e4b
WHISPER_MODEL = large-v3-turbo
WHISPER_COMPUTE_TYPE = int8
CHUNK_DURATION = 7
```

---

## 4. Erster Start 🚀

1. Starten Sie die Anwendung:
   ```powershell
   python RaKScribe.py
   ```
2. **Hinweis:** Beim allerersten Start lädt die App das Whisper-Modell (~1.5 GB) automatisch herunter. Dies kann je nach Internetgeschwindigkeit einige Minuten dauern. Danach startet die App in Sekunden.
3. Passen Sie die `radiology_prompt.txt` an Ihre gewohnten Befunde an.

---

## 5. Bedienung und Workflow 🎤

1. **Starten:** Drücken Sie **F10**. Sprechen Sie Ihren Befund. Der Pegel-Balken schlägt aus und das Transkript wird in Chunks (Paketen) live angezeigt.
2. **Stoppen:** Drücken Sie erneut **F10**. Die KI strukturiert den Text.
3. **Einfügen:** Der fertige Befund wird automatisch in die Zwischenablage kopiert und im aktiven Fenster (z.B. Word oder RIS-Textfeld) eingefügt.

---

## Fehlerbehebung (Troubleshooting)

* **Ollama nicht gefunden:** Stellen Sie sicher, dass das Ollama-Icon in der Taskleiste sichtbar ist.
* **GPU-Fehler (CUDA):** Wenn keine NVIDIA-Karte vorhanden ist, wechselt die App automatisch auf den CPU-Modus (deutlich langsamer). Installieren Sie ggf. die neuesten NVIDIA-Treiber.
* **Kein Pegelausschlag:** Prüfen Sie in den Windows-Soundeinstellungen, ob das richtige Mikrofon als Standardgerät ausgewählt ist.

---
*(c) 2026 RaKScribe Team - Lokale radiologische Dokumentation.*
