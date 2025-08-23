# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fdsmp is an automated spam filter that analyzes IMAP emails using a local LLM (Ollama) and moves spam messages to the spam folder. The system fetches the latest 3 emails, extracts text content, classifies emails using LangChain few-shot templates, and automatically moves spam to the spam folder.

## Package Management
- Use `uv` for all Python package management operations
- Do not use pip, pipenv, or other package managers

## Development Workflow
- Use `uv add <package>` to add dependencies
- Use `uv run <script>` to run Python scripts
- Use `uv sync` to sync dependencies
- Use `ruff` for linting and code formatting

## Common Commands

### Running the Application
```bash
# Run the spam filter
uv run main.py

# Sync dependencies
uv sync
```

### Configuration
```bash
# Create environment file from template
cp .env.template .env

# Edit configuration
nano .env
```

## Common Commands

### Development and Testing
```bash
# Run with different modes
uv run main.py --dry-run --emails 5          # Safe testing without moving emails
uv run main.py --debug --emails 3            # Debug mode with detailed logs
uv run main.py --debug-prompt --emails 1     # Show full LLM prompts

# Extract emails for building spam examples
uv run extract_emails.py --emails 10

# Debug utilities
uv run debug_scripts/test_imap_folders.py     # Test IMAP connection and folders
uv run debug_scripts/test_email_fetch.py     # Test email fetching

# Code quality
uv run ruff check .                           # Run linter
uv run ruff format .                          # Format code
```

### Production
```bash
# Normal operation
uv run main.py --emails 3

# Cron setup for automated filtering every 15 minutes
*/15 * * * * cd /PFAD_ANPASSEN/fdsmp && /usr/bin/uv run main.py >> fdsmp-cron.log 2>&1
```

## Architecture

### 3-Phase Offline Processing Pattern
The system uses a unique offline architecture to prevent IMAP timeouts during slow LLM processing:

1. **FETCH Phase**: Connect to IMAP, retrieve emails with UIDs, disconnect immediately
2. **CLASSIFY Phase**: Process emails offline with LLM (no IMAP connection)
3. **MOVE Phase**: Reconnect to IMAP, batch-move spam emails, disconnect

This pattern is critical because LLM inference can take 1+ minutes per email on resource-constrained devices.

The application follows a modular architecture with clear separation of concerns:

### Core Components

1. **main.py** - Entry point that orchestrates the spam filtering process
   - Sets up logging to both file (`fdsmp.log`) and stdout
   - Coordinates EmailClient, TextExtractor, and SpamClassifier
   - Handles error recovery and cleanup

2. **email_client.py** - IMAP email handling
   - Manages IMAP4_SSL connections
   - Fetches latest N emails from inbox
   - Moves spam emails to spam folder
   - Configurable folder names and email limits

3. **text_extractor.py** - Email content processing
   - Extracts text from multipart emails
   - Handles both HTML and plain text content
   - Uses BeautifulSoup for HTML parsing
   - Truncates content to 2000 characters for analysis

4. **spam_classifier.py** - LLM-based spam detection
   - Uses Ollama LLM with configurable models
   - Implements few-shot learning with **typ 1/typ 2** classification (avoids LLM spam bias)
   - LangChain integration for prompt templating
   - Robust regex-based response parsing for reasoning models (qwen3)
   - Fallback to "not spam" on classification errors

5. **extract_emails.py** - Utility for building spam training examples
   - Extracts emails from IMAP for manual classification
   - Outputs JSON format ready for `spam_examples.json`

### Configuration System

All configuration is managed through environment variables loaded from `.env`:
- IMAP server settings (server, port, credentials)
- Folder configuration (inbox, spam folders)
- Ollama settings (base URL, model name)
- Processing limits (max emails per run)
- Email body length for analysis (MAIL_BODY_LENGTH)

### Few-Shot Learning System

The classifier uses abstract **typ 1/typ 2** labels instead of "spam/not-spam" to avoid LLM bias:
- **typ 1** = legitimate email (ham)
- **typ 2** = spam email

Examples are stored in `spam_examples.json` with this format:
```json
{
  "examples": [
    {
      "email": "Subject: 🔥 Mega Sale Alert!\nFrom: spammer@example.com\nBody: Click now...",
      "classification": "typ 2"
    }
  ]
}
```

**Important**: When examples don't work (LLM ignores matches), this indicates context window overflow or model limitations. Solutions:
1. Move problematic email to first position in examples
2. Reduce example count
3. Use larger/stronger LLM model
4. Check LLM_NUM_CTX setting

### Dependencies

Key dependencies managed in `pyproject.toml`:
- `beautifulsoup4` - HTML parsing
- `langchain` + `langchain-ollama` - LLM integration
- `python-dotenv` - Environment configuration

## Logging

The application logs to both `fdsmp.log` file and stdout with timestamps and log levels. Email processing progress and errors are tracked for debugging and monitoring.

### Text Processing Pipeline

The system implements comprehensive text cleaning for marketing emails:
1. **HTML Processing**: BeautifulSoup parsing with link removal
2. **Invisible Character Cleaning**: Removes Unicode tracking characters (zero-width spaces, soft hyphens, etc.)
3. **Content Truncation**: Configurable body length (default 200 chars) for analysis
4. **Header Extraction**: Subject, From, and Body content combined for LLM analysis

## Code Style

- NEVER use emojis in code, logs, or commit messages
- Keep all output professional and concise  
- Use clear, descriptive language without decorative elements
- Use Unicode symbols in user-facing logs for better readability (👨📧✅❌⏱️)

## Communication Style

- NEVER add completion statements like "All tasks completed!" or similar summary phrases
- These statements are usually incorrect and unnecessary
- Simply complete the requested work without commentary