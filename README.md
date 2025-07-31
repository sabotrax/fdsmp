# fdsmp - Fuck Dich Scheiss Mail-Provider

Ein automatischer Spam-Filter, der IMAP-E-Mails mit einem lokalen LLM (Ollama) analysiert und Spam-Nachrichten in den Spam-Ordner verschiebt.

## Features

- Holt die neuesten 3 E-Mails per IMAP
- Extrahiert Text aus HTML- und Plain-Text-E-Mails
- Verwendet LangChain Few-Shot Templates f�r Spam-Erkennung
- Klassifiziert E-Mails mit lokalem Ollama LLM
- Verschiebt Spam automatisch in den Spam-Ordner
- Cron-kompatibel f�r regelm��ige Ausf�hrung

## Setup

### 1. Ollama installieren und Model laden

```bash
# Ollama installieren (siehe https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# LLM Model laden (z.B. llama3.1)
ollama pull llama3.1
```

### 2. Konfiguration

```bash
# .env Datei aus Template erstellen
cp .env.template .env

# .env Datei bearbeiten mit deinen IMAP-Daten
nano .env
```

### 3. Dependencies installieren

```bash
uv sync
```

### 4. Test-Ausf�hrung

```bash
uv run main.py
```

## Cron Setup

F�r automatische Ausf�hrung alle 10 Minuten:

```bash
# Crontab bearbeiten
crontab -e

# Diese Zeile hinzuf�gen (Pfad anpassen):
*/10 * * * * cd /pfad/zu/mailficker && uv run main.py >> /var/log/fdsmp.log 2>&1
```

## Konfiguration (.env)

- `IMAP_SERVER`: IMAP Server (z.B. imap.gmail.com)
- `IMAP_PORT`: IMAP Port (meist 993 f�r SSL)
- `IMAP_USERNAME`: E-Mail Adresse
- `IMAP_PASSWORD`: Passwort oder App-Passwort
- `INBOX_FOLDER`: Posteingang Ordner (meist INBOX)
- `SPAM_FOLDER`: Spam Ordner (meist SPAM oder Junk)
- `OLLAMA_BASE_URL`: Ollama Server URL (http://localhost:11434)
- `OLLAMA_MODEL`: LLM Model (z.B. llama3.1)
- `SPAM_EXAMPLES_FILE`: JSON-Datei mit Few-Shot Examples (Standard: spam_examples.json)
- `MAX_EMAILS_TO_PROCESS`: Anzahl E-Mails pro Durchlauf (Standard: 3)

## Spam-Klassifikation anpassen

Die Few-Shot Examples f�r die Spam-Erkennung k�nnen in der `spam_examples.json` Datei angepasst werden:

```json
{
  "examples": [
    {
      "email": "Subject: ...\nFrom: ...\nContent: ...",
      "classification": "spam"
    },
    {
      "email": "Subject: ...\nFrom: ...\nContent: ...",
      "classification": "not spam"
    }
  ]
}
```

Je mehr relevante Examples hinzugef�gt werden, desto besser kann das LLM zwischen Spam und echten E-Mails unterscheiden.

## Logs

Die Anwendung loggt in `fdsmp.log` und stdout.