#!/usr/bin/env python3
"""
SimpleDB - SimpleX Chat Export Tool
Modern CLI with rich interface
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

try:
    from sqlcipher3 import dbapi2 as sqlite
except ImportError:
    print("ERROR: sqlcipher3 not installed!")
    print("Run: pip install sqlcipher3")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich import box
except ImportError:
    print("ERROR: rich not installed!")
    print("Run: pip install rich")
    sys.exit(1)

console = Console()

# =============================================================================
# DATABASE
# =============================================================================

class SimpleXDB:
    """SimpleX Chat Database Connection."""
    
    DEFAULT_PATHS = [
        Path(os.environ.get('APPDATA', '')) / 'SimpleX' / 'simplex_v1_chat.db',
        Path(os.environ.get('APPDATA', '')) / 'simplex' / 'simplex_v1_chat.db',
        Path.home() / '.simplex' / 'simplex_v1_chat.db',
        Path.home() / '.local' / 'share' / 'simplex' / 'simplex_v1_chat.db',
    ]
    
    def __init__(self, db_path: str, passphrase: str):
        self.db_path = db_path
        self.passphrase = passphrase
        self.conn = None
        
    @classmethod
    def find_database(cls) -> Optional[str]:
        """Find SimpleX database automatically."""
        for path in cls.DEFAULT_PATHS:
            if path.exists():
                return str(path)
        return None
        
    def connect(self) -> bool:
        """Connect to database."""
        self.conn = sqlite.connect(self.db_path)
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA key = '{self.passphrase}'")
        cursor.execute("SELECT count(*) FROM sqlite_master")
        cursor.fetchone()
        return True
    
    def close(self):
        if self.conn:
            self.conn.close()
            
    def get_contacts(self) -> List[Dict]:
        """Get all contacts."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.contact_id, c.local_display_name,
                   cp.display_name, cp.full_name,
                   (SELECT COUNT(*) FROM chat_items WHERE contact_id = c.contact_id 
                    AND item_content LIKE '%MsgContent%') as msg_count
            FROM contacts c
            LEFT JOIN contact_profiles cp ON c.contact_profile_id = cp.contact_profile_id
            WHERE c.deleted = 0
            ORDER BY c.local_display_name
        """)
        return [
            {'id': r[0], 'name': r[1], 'display_name': r[2], 'full_name': r[3], 'msg_count': r[4]}
            for r in cursor.fetchall()
        ]
    
    def get_groups(self) -> List[Dict]:
        """Get all groups."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT g.group_id, g.local_display_name,
                   gp.display_name, gp.full_name,
                   (SELECT COUNT(*) FROM chat_items WHERE group_id = g.group_id
                    AND item_content LIKE '%MsgContent%') as msg_count
            FROM groups g
            LEFT JOIN group_profiles gp ON g.group_profile_id = gp.group_profile_id
            ORDER BY g.local_display_name
        """)
        return [
            {'id': r[0], 'name': r[1], 'display_name': r[2], 'full_name': r[3], 'msg_count': r[4]}
            for r in cursor.fetchall()
        ]
    
    def get_contact_messages(self, contact_id: int, contact_name: str) -> List[Dict]:
        """Get all messages for a contact."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                chat_item_id,
                item_ts,
                item_sent,
                item_text,
                item_deleted,
                item_content,
                item_edited,
                quoted_content,
                quoted_sent
            FROM chat_items
            WHERE contact_id = ?
              AND (item_content LIKE '%rcvMsgContent%' OR item_content LIKE '%sndMsgContent%')
            ORDER BY item_ts ASC
        """, (contact_id,))
        
        messages = []
        for r in cursor.fetchall():
            msg = self._parse_message(r, contact_name)
            if msg:
                messages.append(msg)
        return messages
    
    def get_group_messages(self, group_id: int) -> List[Dict]:
        """Get all messages for a group."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                ci.chat_item_id,
                ci.item_ts,
                ci.item_sent,
                ci.item_text,
                ci.item_deleted,
                ci.item_content,
                ci.item_edited,
                ci.quoted_content,
                ci.quoted_sent,
                gm.local_display_name
            FROM chat_items ci
            LEFT JOIN group_members gm ON ci.group_member_id = gm.group_member_id
            WHERE ci.group_id = ?
              AND (ci.item_content LIKE '%rcvMsgContent%' OR ci.item_content LIKE '%sndMsgContent%')
            ORDER BY ci.item_ts ASC
        """, (group_id,))
        
        messages = []
        for r in cursor.fetchall():
            msg = self._parse_message(r, r[9] if len(r) > 9 else None)
            if msg:
                messages.append(msg)
        return messages
    
    def _parse_message(self, row, contact_name: str = None) -> Optional[Dict]:
        """Parse a message row."""
        chat_item_id, item_ts, item_sent, item_text, item_deleted, item_content, item_edited, quoted_content, quoted_sent = row[:9]
        
        # Parse content type from JSON
        content_type = 'text'
        if item_content:
            try:
                content = json.loads(item_content)
                msg_content = content.get('rcvMsgContent', content.get('sndMsgContent', {}))
                if isinstance(msg_content, dict):
                    inner = msg_content.get('msgContent', {})
                    content_type = inner.get('type', 'text')
            except:
                pass
        
        # Parse quote
        quote = None
        if quoted_content:
            try:
                qc = json.loads(quoted_content)
                quote_text = qc.get('text', '')
                if quote_text:
                    quote = {
                        'text': quote_text,
                        'sent_by_me': bool(quoted_sent)
                    }
            except:
                pass
        
        return {
            'id': chat_item_id,
            'timestamp': self._format_timestamp(item_ts),
            'timestamp_raw': item_ts,
            'sent': bool(item_sent),
            'sender': 'ME' if item_sent else (contact_name or 'CONTACT'),
            'text': item_text or '',
            'deleted': bool(item_deleted),
            'edited': bool(item_edited) if item_edited else False,
            'content_type': content_type,
            'quote': quote
        }
    
    def _format_timestamp(self, ts: str) -> str:
        """Format timestamp."""
        if not ts:
            return ''
        try:
            if 'T' in str(ts):
                clean = str(ts).split('.')[0] if '.' in str(ts) else str(ts).replace('Z', '')
                dt = datetime.fromisoformat(clean)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return str(ts)
        except:
            return str(ts)
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contacts WHERE deleted = 0")
        contacts = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM groups")
        groups = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chat_items WHERE item_content LIKE '%MsgContent%'")
        messages = cursor.fetchone()[0]
        return {'contacts': contacts, 'groups': groups, 'messages': messages}


# =============================================================================
# FORMATTERS
# =============================================================================

class ChatExporter:
    """Export chat messages to various formats."""
    
    CONTENT_ICONS = {
        'text': '',
        'image': '📷',
        'file': '📎',
        'voice': '🎤',
        'video': '🎬',
        'link': '🔗'
    }
    
    def export_txt(self, messages: List[Dict], chat_name: str, filepath: str):
        """Export to readable text file."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  SIMPLEX CHAT EXPORT: {chat_name}")
        lines.append(f"  Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Messages: {len(messages)}")
        lines.append("=" * 70)
        lines.append("")
        
        current_date = None
        for msg in messages:
            # Date separator
            msg_date = msg['timestamp'].split(' ')[0] if msg['timestamp'] else ''
            if msg_date and msg_date != current_date:
                current_date = msg_date
                lines.append("")
                lines.append(f"{'─' * 25} {current_date} {'─' * 25}")
                lines.append("")
            
            # Message
            time = msg['timestamp'].split(' ')[1] if ' ' in msg['timestamp'] else msg['timestamp']
            sender = msg['sender']
            edited = ' [edited]' if msg['edited'] else ''
            icon = self.CONTENT_ICONS.get(msg['content_type'], '')
            
            lines.append(f"┌─ [{time}] {sender}{edited}")
            
            # Quote
            if msg['quote']:
                quote_sender = 'ME' if msg['quote']['sent_by_me'] else 'THEM'
                quote_preview = msg['quote']['text'][:50]
                if len(msg['quote']['text']) > 50:
                    quote_preview += '...'
                lines.append(f"│  ↳ Reply to {quote_sender}: \"{quote_preview}\"")
            
            # Content
            if msg['deleted']:
                lines.append("│  [Message deleted]")
            elif msg['text']:
                for text_line in msg['text'].split('\n'):
                    prefix = f"{icon} " if icon else ""
                    lines.append(f"│  {prefix}{text_line}")
            else:
                lines.append(f"│  {icon} [{msg['content_type'].upper()}]")
            
            lines.append("└─")
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("  END OF EXPORT")
        lines.append("=" * 70)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def export_json(self, messages: List[Dict], chat_name: str, filepath: str):
        """Export to JSON."""
        data = {
            'meta': {
                'chat_name': chat_name,
                'exported_at': datetime.now().isoformat(),
                'message_count': len(messages),
                'tool': 'SimpleDB'
            },
            'messages': messages
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def export_html(self, messages: List[Dict], chat_name: str, filepath: str):
        """Export to HTML with dark theme."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Export: {chat_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 30px;
            background: rgba(0, 217, 255, 0.1);
            border: 1px solid rgba(0, 217, 255, 0.3);
            border-radius: 16px;
            margin-bottom: 30px;
        }}
        h1 {{ color: #00d9ff; font-size: 1.8em; margin-bottom: 10px; }}
        .meta {{ color: #888; font-size: 0.9em; }}
        .date-sep {{
            text-align: center;
            padding: 15px;
            color: #00d9ff;
            font-weight: 600;
            font-size: 0.9em;
        }}
        .msg {{
            margin: 12px 0;
            padding: 14px 18px;
            border-radius: 16px;
            max-width: 75%;
            position: relative;
        }}
        .msg.sent {{
            background: linear-gradient(135deg, #0066cc, #004499);
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }}
        .msg.received {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            margin-right: auto;
            border-bottom-left-radius: 4px;
        }}
        .msg-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-size: 0.8em;
        }}
        .sender {{ font-weight: 600; color: #00d9ff; }}
        .sent .sender {{ color: #66d9ff; }}
        .time {{ color: #666; }}
        .edited {{ color: #888; font-size: 0.75em; margin-left: 8px; }}
        .quote {{
            background: rgba(0,0,0,0.3);
            border-left: 3px solid #00d9ff;
            padding: 10px 14px;
            margin-bottom: 10px;
            border-radius: 8px;
            font-size: 0.9em;
        }}
        .quote-sender {{ color: #00d9ff; font-weight: 600; font-size: 0.85em; }}
        .quote-text {{ color: #aaa; margin-top: 4px; }}
        .content {{ line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; }}
        .deleted {{ color: #666; font-style: italic; }}
        .media {{ 
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(0,217,255,0.1);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>💬 {chat_name}</h1>
            <div class="meta">
                Exported {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • {len(messages)} messages
            </div>
        </header>
        <div class="chat">
"""
        
        current_date = None
        for msg in messages:
            msg_date = msg['timestamp'].split(' ')[0] if msg['timestamp'] else ''
            if msg_date and msg_date != current_date:
                current_date = msg_date
                html += f'            <div class="date-sep">─── {current_date} ───</div>\n'
            
            cls = 'sent' if msg['sent'] else 'received'
            time = msg['timestamp'].split(' ')[1] if ' ' in msg['timestamp'] else ''
            edited = '<span class="edited">(edited)</span>' if msg['edited'] else ''
            
            html += f'            <div class="msg {cls}">\n'
            html += f'                <div class="msg-header">\n'
            html += f'                    <span class="sender">{msg["sender"]}</span>\n'
            html += f'                    <span><span class="time">{time}</span>{edited}</span>\n'
            html += f'                </div>\n'
            
            if msg['quote']:
                q_sender = 'ME' if msg['quote']['sent_by_me'] else 'THEM'
                q_text = self._escape_html(msg['quote']['text'][:100])
                html += f'                <div class="quote">\n'
                html += f'                    <div class="quote-sender">↩ {q_sender}</div>\n'
                html += f'                    <div class="quote-text">{q_text}</div>\n'
                html += f'                </div>\n'
            
            if msg['deleted']:
                html += '                <div class="content deleted">[Message deleted]</div>\n'
            elif msg['text']:
                text = self._escape_html(msg['text'])
                html += f'                <div class="content">{text}</div>\n'
            else:
                icon = self.CONTENT_ICONS.get(msg['content_type'], '📄')
                html += f'                <div class="content"><span class="media">{icon} {msg["content_type"].upper()}</span></div>\n'
            
            html += '            </div>\n'
        
        html += """        </div>
    </div>
</body>
</html>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def _escape_html(self, text: str) -> str:
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace('\n', '<br>'))


# =============================================================================
# MODERN CLI
# =============================================================================

class SimpleDBApp:
    """Main application with modern CLI."""
    
    def __init__(self):
        self.db: Optional[SimpleXDB] = None
        self.exporter = ChatExporter()
    
    def run(self):
        """Main entry point."""
        self.show_banner()
        
        if not self.connect_database():
            return
        
        self.main_menu()
        
        if self.db:
            self.db.close()
        console.print("\n[dim]Goodbye! 👋[/dim]\n")
    
    def show_banner(self):
        """Display application banner."""
        console.print()
        banner = """
[bold cyan]   _____ _                 _      ____  ____ 
  / ____(_)               | |    |  _ \\|  _ \\
 | (___  _ _ __ ___  _ __ | | ___| | | | |_) |
  \\___ \\| | '_ ` _ \\| '_ \\| |/ _ \\ | | |  _ < 
  ____) | | | | | | | |_) | |  __/ |_| | |_) |
 |_____/|_|_| |_| |_| .__/|_|\\___|____/|____/ 
                    |_|[/bold cyan]
        """
        console.print(Panel(banner + "\n[dim]SimpleX Chat Database Export Tool[/dim]", 
                           border_style="cyan", padding=(0, 2)))
    
    def connect_database(self) -> bool:
        """Connect to SimpleX database."""
        # Find database
        db_path = SimpleXDB.find_database()
        
        if db_path:
            console.print(f"\n[green]✓[/green] Found database: [dim]{db_path}[/dim]")
            if not Confirm.ask("Use this database?", default=True):
                db_path = Prompt.ask("Enter database path")
        else:
            console.print("\n[yellow]![/yellow] Database not found automatically")
            db_path = Prompt.ask("Enter database path")
        
        if not os.path.exists(db_path):
            console.print(f"[red]✗ File not found: {db_path}[/red]")
            return False
        
        # Get passphrase
        passphrase = Prompt.ask("🔑 Passphrase", password=True)
        
        # Connect
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Connecting to database...", total=None)
            try:
                self.db = SimpleXDB(db_path, passphrase)
                self.db.connect()
            except Exception as e:
                console.print(f"\n[red]✗ Connection failed: {e}[/red]")
                return False
        
        console.print("[green]✓ Connected![/green]")
        
        # Show stats
        stats = self.db.get_stats()
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_row("Contacts", f"[cyan]{stats['contacts']}[/cyan]")
        table.add_row("Groups", f"[cyan]{stats['groups']}[/cyan]")
        table.add_row("Messages", f"[cyan]{stats['messages']}[/cyan]")
        console.print(Panel(table, title="[bold]Database Stats[/bold]", border_style="dim"))
        
        return True
    
    def main_menu(self):
        """Main menu loop."""
        while True:
            console.print()
            table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", 
                         title="[bold cyan]MAIN MENU[/bold cyan]", padding=(0, 2))
            table.add_column(width=4)
            table.add_column()
            table.add_row("[cyan]1[/cyan]", "Export Contact Chat")
            table.add_row("[cyan]2[/cyan]", "Export Group Chat")
            table.add_row("[cyan]3[/cyan]", "View Contacts")
            table.add_row("[cyan]4[/cyan]", "View Groups")
            table.add_row("[cyan]Q[/cyan]", "Quit")
            console.print(table)
            
            choice = Prompt.ask("\nSelect", choices=["1", "2", "3", "4", "q", "Q"], default="1")
            
            if choice == "1":
                self.export_contact_chat()
            elif choice == "2":
                self.export_group_chat()
            elif choice == "3":
                self.view_contacts()
            elif choice == "4":
                self.view_groups()
            elif choice.upper() == "Q":
                break
    
    def view_contacts(self):
        """Display contacts list."""
        contacts = self.db.get_contacts()
        
        table = Table(title="[bold]Contacts[/bold]", box=box.ROUNDED, border_style="dim")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Display Name", style="dim")
        table.add_column("Messages", justify="right")
        
        for i, c in enumerate(contacts, 1):
            msg_style = "green" if c['msg_count'] > 0 else "dim"
            table.add_row(
                str(i),
                c['name'],
                c['display_name'] or '-',
                f"[{msg_style}]{c['msg_count']}[/{msg_style}]"
            )
        
        console.print()
        console.print(table)
    
    def view_groups(self):
        """Display groups list."""
        groups = self.db.get_groups()
        
        table = Table(title="[bold]Groups[/bold]", box=box.ROUNDED, border_style="dim")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Display Name", style="dim")
        table.add_column("Messages", justify="right")
        
        for i, g in enumerate(groups, 1):
            msg_style = "green" if g['msg_count'] > 0 else "dim"
            table.add_row(
                str(i),
                g['name'],
                g['display_name'] or '-',
                f"[{msg_style}]{g['msg_count']}[/{msg_style}]"
            )
        
        console.print()
        console.print(table)
    
    def export_contact_chat(self):
        """Export a contact's chat."""
        contacts = self.db.get_contacts()
        
        # Show contacts
        table = Table(title="[bold]Select Contact[/bold]", box=box.ROUNDED, border_style="cyan")
        table.add_column("#", width=4)
        table.add_column("Name")
        table.add_column("Messages", justify="right")
        
        for i, c in enumerate(contacts, 1):
            msg_style = "green" if c['msg_count'] > 0 else "dim"
            table.add_row(str(i), c['name'], f"[{msg_style}]{c['msg_count']}[/{msg_style}]")
        
        console.print()
        console.print(table)
        
        # Select contact
        selection = Prompt.ask("\nEnter number or name")
        contact = self._find_item(contacts, selection)
        
        if not contact:
            console.print(f"[red]✗ Contact not found: {selection}[/red]")
            return
        
        console.print(f"[green]✓ Selected: {contact['name']}[/green]")
        
        # Get messages
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("Loading messages...", total=None)
            messages = self.db.get_contact_messages(contact['id'], contact['display_name'] or contact['name'])
        
        if not messages:
            console.print("[yellow]No messages found.[/yellow]")
            return
        
        console.print(f"[green]✓ Found {len(messages)} messages[/green]")
        
        # Export
        self._do_export(messages, contact['name'])
    
    def export_group_chat(self):
        """Export a group's chat."""
        groups = self.db.get_groups()
        
        # Show groups
        table = Table(title="[bold]Select Group[/bold]", box=box.ROUNDED, border_style="cyan")
        table.add_column("#", width=4)
        table.add_column("Name")
        table.add_column("Messages", justify="right")
        
        for i, g in enumerate(groups, 1):
            msg_style = "green" if g['msg_count'] > 0 else "dim"
            table.add_row(str(i), g['name'], f"[{msg_style}]{g['msg_count']}[/{msg_style}]")
        
        console.print()
        console.print(table)
        
        # Select group
        selection = Prompt.ask("\nEnter number or name")
        group = self._find_item(groups, selection)
        
        if not group:
            console.print(f"[red]✗ Group not found: {selection}[/red]")
            return
        
        console.print(f"[green]✓ Selected: {group['name']}[/green]")
        
        # Get messages
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("Loading messages...", total=None)
            messages = self.db.get_group_messages(group['id'])
        
        if not messages:
            console.print("[yellow]No messages found.[/yellow]")
            return
        
        console.print(f"[green]✓ Found {len(messages)} messages[/green]")
        
        # Export
        self._do_export(messages, group['name'])
    
    def _find_item(self, items: List[Dict], selection: str) -> Optional[Dict]:
        """Find item by number or name."""
        # Try as number
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        
        # Try as name
        for item in items:
            if item['name'].lower() == selection.lower():
                return item
        
        return None
    
    def _do_export(self, messages: List[Dict], chat_name: str):
        """Perform the export."""
        # Format selection
        console.print()
        table = Table(show_header=False, box=box.ROUNDED, border_style="cyan",
                     title="[bold]Export Format[/bold]")
        table.add_row("[cyan]1[/cyan]", "TXT - Plain text")
        table.add_row("[cyan]2[/cyan]", "JSON - Structured data")
        table.add_row("[cyan]3[/cyan]", "HTML - View in browser")
        table.add_row("[cyan]4[/cyan]", "ALL - All formats")
        console.print(table)
        
        fmt = Prompt.ask("\nSelect format", choices=["1", "2", "3", "4"], default="1")
        
        # Generate filename
        safe_name = re.sub(r'[^\w\s-]', '', chat_name).strip().replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = f"{safe_name}_{timestamp}"
        
        # Export
        exported = []
        
        if fmt in ['1', '4']:
            filepath = f"{base}.txt"
            self.exporter.export_txt(messages, chat_name, filepath)
            exported.append(filepath)
        
        if fmt in ['2', '4']:
            filepath = f"{base}.json"
            self.exporter.export_json(messages, chat_name, filepath)
            exported.append(filepath)
        
        if fmt in ['3', '4']:
            filepath = f"{base}.html"
            self.exporter.export_html(messages, chat_name, filepath)
            exported.append(filepath)
        
        # Show results
        console.print()
        for f in exported:
            console.print(f"[green]✓ Saved:[/green] [cyan]{f}[/cyan]")


# =============================================================================
# MAIN
# =============================================================================

def main():
    app = SimpleDBApp()
    app.run()


if __name__ == "__main__":
    main()
