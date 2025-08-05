# fdsmp - Eff Dich Sch**ss Mail-Provider

Ein Filter-Skript, das IMAP-E-Mails nach Vorgabe mit einem lokalen LLM analysiert und verschiebt.

## Features

- **3-Phasen Offline-Architektur**: FETCH → CLASSIFY → MOVE (keine IMAP-Timeouts)
- **UID-basierte IMAP Operationen**: Persistente Email-Identifikation
- **LangChain Few-Shot Learning**: Intelligente Spam-Erkennung mit Beispielen
- **Robustes Error Handling**: Graceful handling von verschwundenen Emails
- **Batch Processing**: Effiziente Verarbeitung mehrerer Emails
- **Typ-System**: Umgeht LLM-Spam-Bias mit "typ 1/typ 2" Klassifikation
- **Debug-Modi**: Umfassende Logging- und Debugging-Optionen
- **Dry-Run Modus**: Sicheres Testen ohne Email-Manipulation

## Anlass

Mein Mail-Provider patzt bei der Spamerkennung. Je "größer" der Versender, desto weniger funktioniert manuelles Training.
Werbung von Alibaba kommt praktisch immer durch. Dabei hat natürlich nichts mit irgendetwas zu tun.
Zur Rettung eilt ein Raspberry 5 mit 8 GB RAM und Vibe-Coding.

Die Frage nach dem Sinn sollte man sich bei KI-Inferenz auf einem Raspberry Pi besser nicht stellen.
Selbst mit dem kleinsten Modell Qwen3:0.6b dauert die Analyse eine Mail ca. eine Minute.

## Installation

### Voraussetzungen

# Debian 12 Bookworm

```bash
# Python 3.11+
sudo apt update && sudo apt install python3 python3-pip

# uv Package Manager installieren
curl -LsSf https://astral.sh/uv/install.sh | sh
# oder: pip install uv
```

### Ollama installieren und Model laden

```bash
# Ollama installieren
curl -fsSL https://ollama.ai/install.sh | sh

# Empfohlene LLM Modelle laden
ollama pull qwen3:0.6b      # Schnell, 600MB
ollama pull gemma3:1b       # Mittel, 815MB  
ollama pull phi4-mini       # Groß, 2.5GB (braucht 3.9GB RAM)
```

### Repository setup

```bash
# Repository klonen/downloaden
git clone <repository-url> fdsmp
cd fdsmp

# Dependencies installieren
uv sync

# Konfiguration aus Template erstellen
cp .env.template .env
```

### Skript konfigurieren

Mindestens IMAP und Mail-Ordner konfigurieren

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
LLM_TEMPERATURE=0.7

# Processing Configuration
MAX_EMAILS_TO_PROCESS=3
```

### Beispiel-Mails für LLM bereitstellen

## Spam-Klassifikation

Das System verwendet **typ 1/typ 2** zur Kennzeichnung, um LLM-Spam-Bias zu umgehen:
- **typ 1** = not spam (legitime Emails)
- **typ 2** = spam (unerwünschte Emails)

### Mail-Beispiele hinzufügen

Spam und Ham sollten gleich vertreten sein. Je unterschiedlicher, desto besser.
Die Liste sollte nicht riesig werden, weil Sie bei der Analyse jeder Mail komplett vom LLM verarbeitet werden muss.
Man sollte zwischen eigener Anforderung und vorhandenen Ressourcen wie Leistungsfähigkeit des Modells, CPU/GPU und RAM abwägen.

1. **Emails extrahieren:**
```bash
uv run extract_emails.py --emails 10
```

2. **Dateien in `data/` prüfen**

3. **JSON-Snippets aus Dateien kopieren und zu `spam.json` hinzufügen:**
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

```bash
# Dry-Run Test (verschiebt keine Emails)
uv run main.py --dry-run --emails 5

# Debug-Modus für detaillierte Logs
uv run main.py --dry-run --debug --emails 3

# Erste echte Ausführung
uv run main.py --emails 3
```

## Usage

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

### Beispiele

```bash
# 10 Emails verarbeiten
uv run main.py --emails 10

# Spam-Detection testen ohne Emails zu verschieben
uv run main.py --dry-run --emails 5

# Debug-Modus für Troubleshooting
uv run main.py --debug --debug-prompt --emails 1

# Email-Extraktion für neue Spam-Beispiele
uv run extract_emails.py --emails 5
```

## Cron Setup

### Einmal pro Stunde, 10 Emails verarbeiten:
```bash
crontab -e

# Diese Zeile hinzufügen:
0 * * * * cd /tank/ayb/srv/dev/fdsmp && /usr/bin/uv run main.py --emails 10 >> fdsmp-cron.log 2>&1
```

### Häufigere Ausführung (alle 15 Minuten):
```bash
*/15 * * * * cd /tank/ayb/srv/dev/fdsmp && /usr/bin/uv run main.py --emails 5 >> fdsmp-cron.log 2>&1
```

**Wichtig:** Verwende absolute Pfade für `uv` und das Verzeichnis.

## 🔧 Architektur

### 3-Phasen Offline-Processing

**Phase 1 - FETCH:**
- IMAP-Verbindung aufbauen
- Emails mit UID-basierten Operationen holen
- IMAP-Verbindung trennen

**Phase 2 - CLASSIFY (Offline):**
- LLM-Klassifikation ohne IMAP-Verbindung
- Kein Timeout-Risiko bei langer LLM-Verarbeitung
- Spam-Email UIDs sammeln

**Phase 3 - MOVE:**
- IMAP-Verbindung für Batch-Operations
- Robustes Error Handling für verschwundene Emails
- Detaillierte Success/Failure-Berichte

### Fehlerbehandlung

Das System behandelt folgende Szenarien graceful:
- **Verschwundene Emails**: User hat Email zwischenzeitlich verschoben
- **IMAP-Verbindungsfehler**: Netzwerkprobleme während Move-Phase
- **Spam-Ordner-Probleme**: Berechtigungen oder Speicherplatz
- **LLM-Timeouts**: Durch Offline-Processing eliminiert

## Logging

### Log-Ausgabe verstehen

```
2025-08-05 05:28:29 - INFO - Using LLM model: qwen3:0.6b
2025-08-05 05:28:29 - INFO - Base prompt size: ~870 tokens
2025-08-05 05:28:29 - INFO - === PHASE 1: FETCHING EMAILS ===
2025-08-05 05:28:30 - INFO - Fetched 3 emails
2025-08-05 05:28:30 - INFO - === PHASE 2: CLASSIFYING EMAILS (OFFLINE) ===
2025-08-05 05:29:31 - INFO - Email classified as: not spam (raw: typ 1)
2025-08-05 05:30:14 - INFO - === PHASE 3: MOVING 2 SPAM EMAILS ===
2025-08-05 05:30:15 - INFO - Processing complete. 2/2 spam emails moved successfully.
```

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

**Alle Emails als Spam klassifiziert:**
- LLM-Model zu klein → Größeres Model verwenden
- Zu wenige Examples → Mehr Beispiele in `spam.json` hinzufügen
- Temperatur zu niedrig → `LLM_TEMPERATURE=0.7` in `.env`

## 🔗 Development

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
