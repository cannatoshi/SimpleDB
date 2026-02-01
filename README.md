```
   _____ _                 _      ____  ____  
  / ____(_)               | |    |  _ \|  _ \ 
 | (___  _ _ __ ___  _ __ | | ___| | | | |_) |
  \___ \| | '_ ` _ \| '_ \| |/ _ \ | | |  _ < 
  ____) | | | | | | | |_) | |  __/ |_| | |_) |
 |_____/|_|_| |_| |_| .__/|_|\___|____/|____/ 
                    |_|                       
```

# SimpleDB

**Export your SimpleX Chat history with ease.**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)

---

## What is SimpleDB?

SimpleDB is a command-line tool to **export chat histories** from your encrypted [SimpleX Chat](https://simplex.chat/) desktop database. 

SimpleX Chat stores all messages locally in an encrypted SQLCipher database. SimpleDB lets you:

- 📤 **Export** your private conversations and group chats
- 🔐 **Decrypt** the SQLCipher database with your passphrase
- 📄 **Save** in multiple formats for backup or analysis
- 💬 **Preserve** quoted replies, edited messages, and media references

---

## Features

| Feature | Description |
|---------|-------------|
| 🔐 **Encrypted DB Support** | Works with SQLCipher encrypted SimpleX databases |
| 👤 **Contact Export** | Export 1-on-1 conversations |
| 👥 **Group Export** | Export group chat histories |
| 💬 **Quote Detection** | Shows replied-to messages |
| ✏️ **Edit Markers** | Indicates edited messages |
| 🗑️ **Deleted Messages** | Shows deleted message placeholders |
| 📎 **Media Types** | Detects images, files, voice, video |
| 🎨 **Modern CLI** | Beautiful terminal interface with rich |

---

## Export Formats

| Format | Use Case |
|--------|----------|
| **TXT** | Human-readable plain text with timestamps |
| **JSON** | Structured data for processing or import |
| **HTML** | Beautiful dark-themed view in any browser |

---

## Installation
```bash
git clone https://github.com/cannatoshi/SimpleDB.git
cd SimpleDB
pip install -r requirements.txt
```

### Requirements

- Python 3.8+
- SQLCipher support via `sqlcipher3`
- Terminal UI via `rich`

---

## Usage
```bash
python simpledb.py
```

The tool will:
1. Auto-detect your SimpleX database location
2. Ask for your database passphrase
3. Show your contacts and groups with message counts
4. Let you select and export chats

### Database Locations

| OS | Default Path |
|----|--------------|
| **Windows** | `%APPDATA%\SimpleX\simplex_v1_chat.db` |
| **Linux** | `~/.simplex/simplex_v1_chat.db` |
| **macOS** | `~/.simplex/simplex_v1_chat.db` |

---

## Output Example

### TXT Export
```
═══════════════════════════════════════════════════════
  SIMPLEX CHAT EXPORT: Alice
  Exported: 2026-02-01 18:30:00
  Messages: 142
═══════════════════════════════════════════════════════

─────────────────────── 2026-01-30 ───────────────────────

┌─ [14:23:45] Alice
│  ↳ Reply to ME: "Did you see this?"
│  Yes, that's awesome! 🔥
└─

┌─ [14:25:01] ME [edited]
│  Check out this link
└─
```

### HTML Export

Opens in any browser with a modern dark theme matching SimpleX aesthetics.

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

See [LICENSE](LICENSE) for details.

---

## Disclaimer

This tool is for **personal backup purposes only**. Always respect the privacy of your chat partners. SimpleDB is not affiliated with SimpleX Chat or Simplex Chat Ltd.

---

## Contributing

Contributions welcome! Please follow [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages.
```
feat(scope): add new feature
fix(scope): fix bug
docs(scope): update documentation
```
