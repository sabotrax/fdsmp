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

## Architecture

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
   - Implements few-shot learning with spam/not-spam examples
   - LangChain integration for prompt templating
   - Fallback to "not spam" on classification errors

### Configuration System

All configuration is managed through environment variables loaded from `.env`:
- IMAP server settings (server, port, credentials)
- Folder configuration (inbox, spam folders)
- Ollama settings (base URL, model name)
- Processing limits (max emails per run)

### Dependencies

Key dependencies managed in `pyproject.toml`:
- `beautifulsoup4` - HTML parsing
- `langchain` + `langchain-ollama` - LLM integration
- `python-dotenv` - Environment configuration

## Logging

The application logs to both `fdsmp.log` file and stdout with timestamps and log levels. Email processing progress and errors are tracked for debugging and monitoring.