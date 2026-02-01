# SimpleDB

**SimpleX Chat Database Export Tool**

Export chat history from encrypted SimpleX Desktop database with a modern CLI interface.

## Features

- SQLCipher encrypted database support
- Export contact and group chats
- Shows quoted messages (replies)
- Marks edited messages
- Shows deleted messages
- Detects media types (images, files, voice, video)
- Modern terminal UI with rich

## Export Formats

| Format | Description |
|--------|-------------|
| **TXT** | Readable plain text with timestamps |
| **JSON** | Structured data for processing |
| **HTML** | Beautiful dark theme view in browser |

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python simpledb.py
```

## Database Locations

| OS | Path |
|----|------|
| **Windows** | `%APPDATA%\SimpleX\simplex_v1_chat.db` |
| **Linux** | `~/.simplex/simplex_v1_chat.db` |

## License

MIT
