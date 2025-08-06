# fdsmp

Ein Filter-Skript, das IMAP-E-Mails nach Vorgabe mit einem lokalen LLM analysiert und verschiebt.

## Features

- **3-Phasen Offline-Architektur**: FETCH → CLASSIFY → MOVE (verhindert IMAP-Timeouts)
- **LangChain Few-Shot Examples**: LLM-gestützte Spam-Erkennung mit Beispielen
- **Batch Processing**: Effiziente Verarbeitung mehrerer Emails
- **Debug-Modi**: Logging- und Debugging-Optionen
- **Dry-Run Modus**: Sicheres Testen ohne Email-Manipulation

## Anlass

Mein Mail-Provider patzt bei der Spamerkennung. Je "größer" der Versender, desto weniger funktioniert das manuelle Spam-Training.
Werbung von Aliexpress kommt praktisch immer durch. Dabei hat natürlich nichts mit irgendetwas zu tun.
Zur Rettung herbei eilt ein Raspberry 5 mit 8 GB RAM und Vibe-Coding.

Die Frage nach dem Sinn sollte man sich bei LLM-Inferenz auf einem Raspberry Pi besser nicht stellen.
Selbst das kleinste Modell Qwen3:0.6b braucht für die Analyse einer Mail mindestens eine Minute.

## Installation

### Python und Paketmanager

```bash
# Python 3.11+
sudo apt update && sudo apt install python3 python3-pip

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# oder: pip install uv
```

### Ollama installieren und Modell laden

```bash
# Ollama installieren
curl -fsSL https://ollama.ai/install.sh | sh

# Empfohlene LLMs laden
ollama pull qwen3:0.6b      # Schnell, 600MB
ollama pull gemma3:1b       # Mittel, 815MB  
ollama pull phi4-mini       # Groß, 2.5GB (braucht 3.9GB RAM)
```

### Repository-Setup

```bash
# Repository klonen/downloaden
git clone https://github.com/sabotrax/fdsmp.git fdsmp
cd fdsmp

# Abhängigkeiten installieren
uv sync

# Konfiguration aus Template erstellen
cp .env.template .env
```

### Skript konfigurieren

Mindestens IMAP und Mail-Ordner konfigurieren.

```bash
# IMAP Configuration
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password

# Email Folders
INBOX_FOLDER=INBOX
SPAM_FOLDER=SPAM

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:0.6b

# Spam Classification
SPAM_EXAMPLES_FILE=spam_examples.json
LLM_TEMPERATURE=0.2
LLM_NUM_CTX=8192

# Processing Configuration
MAX_EMAILS_TO_PROCESS=3
MAIL_BODY_LENGTH=300
```

## Beispiel-Mails für LLM bereitstellen

### Spam-Klassifikation

Das System verwendet **typ 1/typ 2** zur Kennzeichnung, um LLM-Spam-Bias zu umgehen:
- **typ 1** = kein Spam/Ham
- **typ 2** = Spam

### Beispiel-Mails hinzufügen

Spam und Ham sollten gleich vertreten sein. Je unterschiedlicher, desto besser.
Die Liste sollte nicht riesig werden, weil Sie bei jeder Mail vom LLM verarbeitet werden muss.

**Mails extrahieren:**

Das Skript zieht die neuesten N Mails und legt sie in `data/` ab.

```bash
uv run extract_emails.py --emails 10
```

**JSON-Snippets aus Dateien kopieren und zu `spam_examples.json` hinzufügen:**

Die Einträge müssen nicht geordnet sein.

```json
{
  "examples": [
    {
      "email": "Subject: 🔥 Mega Sale Alert!\nFrom: spammer@example.com",
      "classification": "typ 2"
    },
    {
      "email": "Subject: Beleg für Ihre Zahlung\nFrom: PayPal <service@paypal.de>",
      "classification": "typ 1"
    }
  ]
}
```

### Hinweise zum Betrieb

Wenn die Liste länger wird oder die Mails darin größer, stößt man schnell an die Grenzen des kleinsten Modells.
Anzeichen dafür sind, dass das LLM falsch sortiert (auch bei hoher Übereinstimmung von Vorlage und Mail).

Abhilfe:
+ Die nicht-erkannte Mail an die erste Position in der Liste der Beispiel-Mails setzen.
+ Die Liste verkleinern.
+ Ein anderes/stärkeres/größeres Modell wählen.
  Ich habe die besten Erfahrungen mit Qwen3-Modellen gemacht. 

Man muss zwischen Anforderung und Ressourcen wie GPU, CPU und RAM abwägen.

### Ausführung

```bash
# Dry-Run Test (verschiebt keine Mails)
uv run main.py --dry-run --emails 5

# Debug-Modus für detaillierte Logs
uv run main.py --dry-run --debug --emails 3

# Erste echte Ausführung
uv run main.py --emails 3
```

## Verwendung

### Kommandozeilen-Optionen

```bash
uv run main.py [OPTIONS]

Optionen:
  --dry-run           Emails klassifizieren, aber nicht verschieben
  --debug             Debug-Logging für LLM-Klassifikation aktivieren  
  --debug-prompt      Vollständigen Prompt anzeigen (erweitert --debug)
  --emails N          Anzahl Emails verarbeiten (überschreibt Wert aus .env)
  -h, --help          Hilfe anzeigen
```

## Cron Setup

### Alle 15 Minuten
```bash
crontab -e

# Diese Zeile hinzufügen:
*/15 * * * * cd /PFAD_ANPASSEN/fdsmp && /usr/bin/uv run main.py >> fdsmp-cron.log 2>&1
```

**Wichtig:** Verwende absolute Pfade für `uv` und das Verzeichnis.

## Architektur

### 3-Phasen Offline-Processing

**Phase 1 - FETCH:**
- IMAP-Verbindung aufbauen
- Emails mit UID-basierten Operationen holen
- IMAP-Verbindung trennen

**Phase 2 - CLASSIFY (Offline):**
- LLM-Klassifikation
- Spam-Email UIDs sammeln

**Phase 3 - MOVE:**
- IMAP-Verbindung für Batch-Operation
- Robustes Error Handling für verschwundene Emails
- Detaillierte Success/Failure-Berichte

### Fehlerbehandlung

Das System behandelt folgende Szenarien graceful:
- **Verschwundene Emails**: User hat Email zwischenzeitlich verschoben
- **IMAP-Verbindungsfehler**: Netzwerkprobleme während Move-Phase
- **Spam-Ordner-Probleme**: Berechtigungen oder Speicherplatz
- **LLM-Timeouts**: Durch Offline-Processing eliminiert

## Logging

### Log-Dateien

- **`fdsmp.log`**: Hauptlog-Datei (automatisch rotiert)
- **`fdsmp-cron.log`**: Cron-Ausführungen (bei Cron-Setup)

## Troubleshooting

### Häufige Probleme

**LLM antwortet nicht:**
```bash
# LLM-Verbindung testen
curl http://localhost:11434/api/version

# Model verfügbar?
ollama list
```

**IMAP-Verbindung fehlschlägt:**
```bash
# IMAP-Ordner testen
uv run debug_scripts/test_imap_folders.py
```

**Emails werden nicht verschoben:**
```bash
# Debug-Modus mit Prompt-Anzeige
uv run main.py --debug --debug-prompt --emails 1
```

**Emails falsch klassifiziert:**
- LLM zu klein/schwach → Größeres Modell verwenden
- Zu wenige Beispiele für das LLM → Mehr in `spam.json` hinzufügen
- Temperatur verändern in `.env` (LLM-Wissen erforderlich)
- LLM_NUM_CTX korrekt? Token könnten überschitten sein durch großes Prompt (LLM-Wissen erforderlich)

## Development

### Debug-Scripts

```bash
# IMAP-Ordner und Verbindung testen
uv run debug_scripts/test_imap_folders.py

# Email-Abruf testen
uv run debug_scripts/test_email_fetch.py
```

### Projektstruktur

```
fdsmp/
├── main.py              # Hauptskript
├── email_client.py      # IMAP-Operationen
├── spam_classifier.py   # LLM-Klassifikation
├── text_extractor.py    # Email-Text-Extraktion
├── extract_emails.py    # Utility für Spam-Beispiele
├── spam.json           # Few-Shot Spam-Beispiele
├── debug_scripts/      # Debug-Tools
├── data/               # Extrahierte Emails
└── CLAUDE.md          # Entwickler-Dokumentation
```

## License

MIT License - Nutze es wie du willst, aber Spam nervt trotzdem.
