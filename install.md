⚙️ Voraussetzungen und API-Zugriff

🇩🇪 Sprachhinweis: Das RaKScribe-Projekt ist in seiner aktuellen Version (v0.9) vollständig auf die deutsche Sprache fixiert. 
Dies betrifft sowohl die Spracherkennung (language_code="de-DE" in Google Cloud STT) als auch die gesamte Befundstrukturierung durch GPT-4o (radiology_prompt.txt). 
Eine Nutzung in anderen Sprachen erfordert Anpassungen im Code und im Prompt-Template. 


Die Nutzung erfordert die Einrichtung von kostenpflichtigen Cloud-Diensten.
A. Python-Umgebung
    • Python 3.10 oder neuer muss installiert sein. Verwendet wurde 3.14
    • WICHTIG: Die PowerShell/CMD muss die Python-Befehle (python, pip) erkennen können.
B. Cloud-API-Voraussetzungen
Dienst	Notwendiger Zugang	Bemerkung
OpenAI	API-Schlüssel (für das Modell gpt-4o)	Das Guthaben muss ausreichend sein, um das Modell aufrufen zu können.
Google Cloud	Dienstkonto mit aktivierter "Cloud Speech-to-Text API"	Der API-Schlüssel (JSON-Datei) muss volle Rechte für diese API besitzen.

📦 Installation der Abhängigkeiten
Öffnen Sie die PowerShell oder CMD und navigieren Sie in das Hauptverzeichnis des Projekts (cd C:\RaKScribe\RaKScribe).
A. Pakete installieren
Installieren Sie alle notwendigen Python-Bibliotheken in einem Schritt:

pip install -r requirements.txt

B. Audio-Treiber testen
Stellen Sie sicher, dass das Mikrofon erkannt wird:

python -m sounddevice

🔐 Authentifizierung einrichten
Sie müssen Ihre Schlüssel und die Google JSON-Datei im Projektordner hinterlegen.
A. Konfigurationsdatei erstellen
    1. Kopieren Sie die Musterdatei config.ini.example.
    2. Benennen Sie die Kopie um in config.ini.
    3. Öffnen Sie die config.ini und ersetzen Sie die Platzhalter (YOUR_...) durch Ihre tatsächlichen Schlüssel und den Dateinamen des Google-Schlüssels:

[API_KEYS]
OPENAI_API_KEY = IHR_SCHLUESSEL_sk-proj-HIER
GOOGLE_JSON_FILENAME = IHRE_DATEI_rakscribe-123456789yyy.json

B. Google JSON-Schlüssel hinterlegen
    • Legen Sie die heruntergeladene .json-Datei (mit Ihrem privaten Schlüssel) in denselben Ordner wie die rakscribe0.9.py.

🚀 Erster Start und Optimierung
A. Anwendung starten
Starten Sie die App über die Kommandozeile:

python rakscribe0.9.py

B. Prompt-Vorlage anpassen
    • Die KI-Anweisungen (Terminologie-Regeln, Abkürzungen etc.) werden aus der Datei radiology_prompt.txt geladen.
    • WICHTIG: Passen Sie die Regeln in dieser Datei an die lokalen Befundungsgewohnheiten und Abkürzungen an. Sie ist das Herzstück der Strukturierung.
C. Diktat testen
    • Klicken Sie auf "Diktat Start / Stopp".
    • Achten Sie auf den Mikrofonpegel (Balken muss ausschlagen).
    • Nach dem Stoppen erfolgt die automatische Strukturierung durch GPT-4o und die Formatierung (HTML-Text für Word) wird in die Zwischenablage kopiert.
