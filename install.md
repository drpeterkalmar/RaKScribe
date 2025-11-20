# ⚙️ Installations- und Einrichtungsanleitung

> **🇩🇪 Wichtiger Sprachhinweis:**
> Das RaKScribe-Projekt ist in seiner aktuellen Version **vollständig auf die deutsche Sprache fixiert**.
> Dies betrifft sowohl die Spracherkennung (`language_code="de-DE"` in Google Cloud STT) als auch die gesamte Befundstrukturierung durch GPT-4o (`radiology_prompt.txt`). Eine Nutzung in anderen Sprachen erfordert Anpassungen im Code und im Prompt-Template.

---

## 1. Voraussetzungen und API-Zugriff

Die Nutzung erfordert die Einrichtung von kostenpflichtigen Cloud-Diensten.

### A. Python-Umgebung
* **Python 3.10 oder neuer** muss installiert sein. (Entwickelt und getestet mit Python 3.14).
* **WICHTIG:** Die Shell/CMD muss die Python-Befehle (`python`, `pip`) erkennen können (zu PATH hinzufügen).

### B. Cloud-API-Voraussetzungen

| Dienst | Notwendiger Zugang | Bemerkung |
| :--- | :--- | :--- |
| **OpenAI** | API-Schlüssel (für Modell `gpt-4o`) | Das Guthaben (Credits) muss ausreichend sein, um das Modell aufrufen zu können. |
| **Google Cloud** | Dienstkonto mit aktivierter "Cloud Speech-to-Text API" | Der Schlüssel (JSON-Datei) muss volle Rechte für die STT-API besitzen. |

Ihre APIs finden Sie unter https://platform.openai.com/api-keys bzw. https://console.cloud.google.com/apis/

---

## 2. Installation der Abhängigkeiten 📦

Öffnen Sie die PowerShell oder den Terminal (macOS/Linux) und navigieren Sie in das Hauptverzeichnis des Projekts:

🪟WINDOWS: Terminal im Installationsverzeichnis öffnen oder

    cd C:\Pfad\zu\RaKScribe
🐧LINUX oder 🍏MACOS:

    cd ~/RaKScribe

### A. Pakete installieren
Installieren Sie alle notwendigen Python-Bibliotheken in einem Schritt:

    pip install -r requirements.txt

### B. Audio-Treiber testen
Stellen Sie sicher, dass das Mikrofon erkannt wird und Treiber (PortAudio) vorhanden sind:

    python -m sounddevice

*(Sollte eine Liste der verfügbaren Audio-Geräte ausgeben).*

---

## 3. Authentifizierung einrichten 🔐

Damit die App funktioniert, müssen der OpenAI-Schlüssel und die Google-Cloud-Datei hinterlegt werden.

### A. Konfigurationsdatei erstellen
1.  Kopieren Sie die Musterdatei `config.ini.example` (falls vorhanden) oder erstellen Sie eine neue Datei.
2.  Benennen Sie die Datei um in **`config.ini`**.
3.  Öffnen Sie die Datei und fügen Sie folgenden Inhalt ein (ersetzen Sie die Platzhalter):

    [API_KEYS]
    
    OPENAI_API_KEY = sk-proj-IHR-SCHLÜSSEL-HIER
    
    GOOGLE_JSON_FILENAME = 1234-IHRE-DATEI-HIER.json

### B. Google JSON-Schlüssel hinterlegen
Legen Sie die von Google heruntergeladene `.json`-Datei (Service Account Key) direkt in denselben Ordner wie die `RaKScribe.py`. Achten Sie darauf, dass der Dateiname exakt mit dem Eintrag in der `config.ini` übereinstimmt.

---

## 4. Erster Start und Optimierung 🚀

### A. Anwendung starten
Starten Sie die App über die Kommandozeile:

    python RaKScribe.py

### B. Prompt-Vorlage anpassen
* Die KI-Anweisungen (Terminologie-Regeln, Abkürzungen, Normalbefunde) werden aus der Datei `radiology_prompt.txt` geladen.
* **WICHTIG:** Passen Sie die Regeln in dieser Datei an Ihre lokalen Befundungsgewohnheiten an. Diese Datei ist das Herzstück der Strukturierung!
* Sie können den Prompt auch im laufenden Programmfenster ändern, er wird hier allerdings nicht gespeichert!

### C. Diktat testen
1.  Drücken Sie **F10** oder den Button "Diktat Start / Stopp".
2.  Sprechen Sie in das Mikrofon (der Pegel-Balken muss ausschlagen).
3.  Drücken Sie erneut **F10** zum Stoppen.
4.  **Automatischer Export:** Nach kurzer Verarbeitung durch GPT-4o wird der strukturierte Befund in die Zwischenablage kopiert und automatisch eingefügt.

> **💡 Tipp für Word:**
> Damit der Befund perfekt aussieht, sollten in Ihrem Word-Dokument die Formatvorlagen **"Überschrift 1"**, **"Überschrift 2"** und **"Standard"** (Fließtext) sauber vorformatiert sein. RaKScribe nutzt HTML-Formatierung, die diese Stile anspricht.

---

## 5. Optional: Als ausführbare Datei kompilieren: 

Bei Bedarf kann das Python-Skript in eine ausführbare Datei umgewandelt werden. Dies erfordert das Paket `pyinstaller`.

**Befehl für die Erstellung:**

    pyinstaller --noconsole --onefile --clean --name RaKScribe RaKScribe.py 

Die fertige Datei finden Sie anschließend im Unterordner dist/. 

🟦Windows: RaKScribe.exe

💸macOS: RaKScribe.app (oder Unix-Executable)

🤓Linux: RaKScribe (ohne Endung)

Damit sie startet, müssen sich folgende Dateien im selben Ordner befinden:

config.ini

radiology_prompt.txt

Die Google-JSON-Datei



