# backend.py
import socket
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict
import configparser
import os
import sqlite3
from ftplib import FTP_TLS, error_perm
import io

from PySide6.QtCore import QObject, Signal, Slot, QTimer

class Worker(QObject):
    # Signals that the worker can send to the GUI
    connectionStatusChanged = Signal(bool, str)
    logMessage = Signal(str)
    playersUpdated = Signal(list)
    playerHistoryUpdated = Signal(list) # Kept for later use
    entitiesUpdated = Signal(list)
    configDataUpdated = Signal(list)
    statusMessage = Signal(str, int) # message, timeout (in ms)

    def __init__(self, config_file="empyrion_helper.conf"):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # Server details
        self.host = self.config.get('server', 'host', fallback='localhost')
        self.port = self.config.getint('server', 'telnet_port', fallback=30004)
        self.password = self.config.get('server', 'telnet_password', fallback='')

        # FTP details
        ftp_address = self.config.get('ftp', 'host', fallback='')
        self.ftp_host = ftp_address
        self.ftp_port = 21
        if ':' in ftp_address:
            try:
                host, port_str = ftp_address.split(':', 1)
                self.ftp_host = host
                self.ftp_port = int(port_str)
            except ValueError:
                self.logMessage.emit(f"Invalid FTP host format: '{ftp_address}'.")
        self.ftp_user = self.config.get('ftp', 'user', fallback='')
        self.ftp_password = self.config.get('ftp', 'password', fallback='')
        self.remote_config_path = self.config.get('ftp', 'remote_log_path', fallback='/')

        self.socket = None
        self.connected = False
        self._running = False
        self.update_interval = self.config.getint('monitoring', 'update_interval', fallback=30)

        # --- QTimer for periodic updates ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.force_player_update)

        self._init_database()

    def _init_database(self):
        """Initializes the SQLite database and the required tables."""
        self.db_conn = sqlite3.connect('player_history.db')
        cursor = self.db_conn.cursor()
        # Player events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, steam_id TEXT, player_name TEXT,
                playfield_name TEXT, event_type TEXT,
                UNIQUE(timestamp, steam_id, event_type)
            )
        ''')
        # Entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT,
                type TEXT,
                faction TEXT,
                name TEXT,
                playfield TEXT
            )
        ''')
        self.db_conn.commit()

    def _read_until(self, delimiter: bytes, timeout: int = 5) -> bytes:
        data = b""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                chunk = self.socket.recv(1)
                if not chunk: break
                data += chunk
                if data.endswith(delimiter): break
            except socket.timeout: break
        return data

    @Slot()
    def start_monitoring(self):
        """Starts the Telnet monitoring loop."""
        self._running = True
        try:
            self.statusMessage.emit("Connecting...", 0)
            self.logMessage.emit(f"Connecting to {self.host}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            if self.password:
                self._read_until(b"Password:")
                self.socket.send(f"{self.password}\r\n".encode('ascii'))
            self._read_until(b">")
            self.connected = True
            self.connectionStatusChanged.emit(True, "Successfully connected!")
            self.statusMessage.emit("Connected.", 3000)
        except Exception as e:
            self.logMessage.emit(f"Connection error: {e}")
            self.connectionStatusChanged.emit(False, f"Connection failed: {e}")
            self.statusMessage.emit("Connection Failed.", 0)
            self._running = False
            return

        # Initial update and start timer
        self.force_player_update()
        self.timer.start(self.update_interval * 1000)

    @Slot()
    def stop_monitoring(self):
        self.timer.stop() # Stop the timer
        self._running = False
        if self.socket:
            try:
                self.socket.send(b"exit\r\n")
            except Exception: pass
            finally:
                self.socket.close()
                self.socket = None
        self.connected = False
        if self.db_conn:
            self.db_conn.close()
        self.logMessage.emit("Monitoring stopped.")
        self.connectionStatusChanged.emit(False, "Disconnected")
        self.statusMessage.emit("", 0)

    def send_command(self, command: str) -> str:
        if not self.connected or not self.socket: return "Not connected"
        try:
            self.socket.send(f"{command}\r\n".encode('ascii'))
            response = self._read_until(b">", timeout=20)
            response_text = response.decode('ascii', errors='ignore').strip()
            if response_text.endswith('>'):
                response_text = response_text[:-1].strip()
            return response_text
        except Exception as e:
            self.logMessage.emit(f"Command '{command}' failed: {e}")
            self.connected = False; self.connectionStatusChanged.emit(False, "Connection lost")
            self.statusMessage.emit("Connection Lost.", 0)
            return f"Error: {e}"

    @Slot()
    def force_player_update(self):
        """Fetches the player list and emits an update signal."""
        if not self.connected:
            return
        self.logMessage.emit("Refreshing player list...")
        self.statusMessage.emit("Refreshing player list...", 0)
        player_list = self.get_player_list_from_plys()
        self.playersUpdated.emit(player_list)
        self.logMessage.emit(f"Player list refreshed. {len(player_list)} player(s) found.")
        self.statusMessage.emit("Player list refreshed.", 4000)

    def get_player_list_from_plys(self) -> List[Dict]:
        """Gets the player list and parses it using the 'plys' command."""
        response = self.send_command("plys")

        players_data = {}

        global_list_pattern = re.compile(r"id=(\d+)\s+name=(.+?)\s+fac=\[(.+?)\]")
        online_connected_pattern = re.compile(r"(\d+):\s+(\d+),\s+(.+?),\s+([\w\s]+?),\s+([\d\.]+)\|(\d+)")

        in_global_list = False
        for line in response.splitlines():
            if "Global players list" in line:
                in_global_list = True
                continue
            if "Players connected" in line:
                in_global_list = False
                continue

            if in_global_list:
                match = global_list_pattern.search(line)
                if match:
                    player_id, name, faction = match.groups()
                    players_data[player_id] = {
                        'id': player_id,
                        'name': name.strip(),
                        'status': 'Offline',
                        'faction': faction.strip(),
                        'ip': '',
                        'playfield': ''
                    }

        in_online_list = False
        for line in response.splitlines():
            if "Players connected" in line:
                in_online_list = True
                continue
            if "Global online players list" in line:
                in_online_list = False
                continue

            if in_online_list:
                match = online_connected_pattern.match(line.strip())
                if match:
                    e_id = match.group(2)
                    playfield = match.group(4).strip()
                    ip = match.group(5)

                    if e_id in players_data:
                        players_data[e_id]['status'] = 'Online'
                        players_data[e_id]['ip'] = ip
                        players_data[e_id]['playfield'] = playfield

        player_list = sorted(players_data.values(), key=lambda p: (p['status'] != 'Online', p['name'].lower()))
        return player_list

    # --- Gents functionality ---
    @Slot()
    def load_entities(self):
        if not self.connected:
            self.logMessage.emit("Cannot load entities: Not connected.")
            return

        self.timer.stop() # Pause player refresh timer
        try:
            self.statusMessage.emit("Loading entities... (this may take a moment)", 0)
            self.logMessage.emit("Fetching entity list with 'gents' command...")
            response = self.send_command("gents")

            self.logMessage.emit("Parsing entity list...")
            entities = self._parse_gents_response(response)

            self.logMessage.emit(f"Found {len(entities)} entities. Storing in database...")
            self._store_entities_in_db(entities)

            self.logMessage.emit("Fetching updated entity list from database...")
            all_entities = self._query_entities_from_db()
            self.entitiesUpdated.emit(all_entities)
            self.logMessage.emit("Entity list updated successfully.")
            self.statusMessage.emit(f"Entities loaded: {len(all_entities)} found.", 4000)

        except Exception as e:
            self.logMessage.emit(f"Error loading entities: {e}")
            self.statusMessage.emit("Error loading entities.", 4000)
        finally:
            self.timer.start(self.update_interval * 1000) # Resume player refresh timer

    def _parse_gents_response(self, response: str) -> List[Dict]:
        """Parses the raw text output of the 'gents' command."""
        self.logMessage.emit("--- Starting Gents Parse (v9 Logic) ---")
        entities = []
        current_playfield = "Unknown"

        # Pattern for entities WITH a faction in brackets
        entity_pattern_faction = re.compile(r"^\s*\d+\.\s+(\d+)\s+(\w+)\s+\[([^\]]+)\]\s+.*?'([^']*)'")
        # Pattern for entities WITHOUT faction brackets (private entities)
        entity_pattern_private = re.compile(r"^\s*\d+\.\s+(\d+)\s+(\w+)\s+.*?'([^']*)'")

        for line in response.splitlines():
            # A playfield line is not indented and does not start like an entity line
            stripped_line = line.strip()
            if not line.startswith(' ') and stripped_line and not stripped_line.lower().startswith("id     ty fac") and not stripped_line.startswith(tuple('0123456789')) and "Total" not in stripped_line and "Query" not in stripped_line:
                current_playfield = stripped_line.split('[')[0].strip()
                self.logMessage.emit(f"Gents Parser: New playfield detected -> {current_playfield}")
                continue

            # An entity line is indented
            if line.startswith(' '):
                # Try faction pattern first
                faction_match = entity_pattern_faction.match(line)
                if faction_match:
                    entities.append({
                        'entity_id': faction_match.group(1), 'type': faction_match.group(2),
                        'faction': faction_match.group(3), 'name': faction_match.group(4).strip(),
                        'playfield': current_playfield
                    })
                    continue

                # Try private pattern (anything else without faction brackets)
                private_match = entity_pattern_private.match(line)
                if private_match:
                    entities.append({
                        'entity_id': private_match.group(1), 'type': private_match.group(2),
                        'faction': 'Private', 'name': private_match.group(3).strip(),
                        'playfield': current_playfield
                    })
                    continue

        self.logMessage.emit(f"--- Finished Gents Parse, {len(entities)} entities found ---")
        return entities

    def _store_entities_in_db(self, entities: List[Dict]):
        cursor = self.db_conn.cursor()
        cursor.execute("DELETE FROM entities")
        for entity in entities:
            cursor.execute(
                "INSERT INTO entities (entity_id, type, faction, name, playfield) VALUES (?, ?, ?, ?, ?)",
                (entity['entity_id'], entity['type'], entity['faction'], entity['name'], entity['playfield'])
            )
        self.db_conn.commit()

    def _query_entities_from_db(self) -> List[Dict]:
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT playfield, entity_id, type, faction, name FROM entities ORDER BY playfield, name")
        rows = cursor.fetchall()
        return [{'playfield': r[0], 'entity_id': r[1], 'type': r[2], 'faction': r[3], 'name': r[4]} for r in rows]

    @Slot()
    def save_raw_gents_output(self):
        if not self.connected:
            self.logMessage.emit("Cannot save raw output: Not connected.")
            return

        self.logMessage.emit("Fetching raw 'gents' output...")
        self.statusMessage.emit("Fetching raw 'gents' output...", 0)
        response = self.send_command("gents")

        filename = "gents_raw_output.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(response)
            self.logMessage.emit(f"Successfully saved raw output to '{filename}'.")
            self.statusMessage.emit(f"Saved raw output to {filename}", 4000)
        except Exception as e:
            self.logMessage.emit(f"Failed to save raw output: {e}")
            self.statusMessage.emit("Failed to save raw output.", 4000)

    # --- Config file functionality ---
    @Slot()
    def load_config_file(self):
        """Downloads and parses ALL .ecf files from the server."""
        self.logMessage.emit("Starting config files download...")
        self.statusMessage.emit("Downloading all .ecf files from server...", 0)

        try:
            # Download all .ecf files
            config_files = self._download_all_ecf_files()

            if config_files:
                self.logMessage.emit(f"Downloaded {len(config_files)} .ecf files. Parsing...")
                all_items = []

                for filename, content in config_files.items():
                    self.logMessage.emit(f"Parsing {filename}...")

                    # Debug: Show first few lines of the file
                    lines = content.splitlines()[:10]
                    self.logMessage.emit(f"First 10 lines of {filename}:")
                    for i, line in enumerate(lines):
                        self.logMessage.emit(f"  {i+1}: {line}")

                    items = self._parse_config_file(content, filename)
                    all_items.extend(items)
                    self.logMessage.emit(f"Found {len(items)} items in {filename}")

                self.logMessage.emit(f"Total found: {len(all_items)} items with StackSize across all files.")

                # Debug: Show some sample items
                if all_items:
                    self.logMessage.emit("Sample items found:")
                    for i, item in enumerate(all_items[:5]):
                        self.logMessage.emit(f"  {i+1}: {item.get('name', 'Unknown')} - StackSize: {item.get('stack_size', 'None')}")

                self.configDataUpdated.emit(all_items)
                self.statusMessage.emit(f"Config loaded: {len(all_items)} items found.", 4000)
            else:
                self.logMessage.emit("Failed to download config files.")
                self.statusMessage.emit("Failed to download config files.", 4000)

        except Exception as e:
            self.logMessage.emit(f"Error loading config files: {e}")
            self.statusMessage.emit("Error loading config files.", 4000)

    @Slot(list)
    def save_config_changes(self, modified_items):
        """Saves the modified config data back to the server with backup."""
        self.logMessage.emit("Starting config save process...")
        self.statusMessage.emit("Saving config changes to server...", 0)

        try:
            # Group items by source file
            files_to_update = {}
            for item in modified_items:
                source_file = item.get('source_file')
                if source_file and source_file not in files_to_update:
                    files_to_update[source_file] = []
                if source_file:
                    files_to_update[source_file].append(item)

            self.logMessage.emit(f"Will update {len(files_to_update)} files: {', '.join(files_to_update.keys())}")

            for filename, items in files_to_update.items():
                self.logMessage.emit(f"Processing {filename}...")

                # Download current file content
                current_content = self._download_single_file(filename)
                if not current_content:
                    self.logMessage.emit(f"Failed to download {filename} for updating")
                    continue

                # Create modified content
                modified_content = self._update_file_content(current_content, items)

                # Create backup and upload modified file
                if self._backup_and_upload_file(filename, modified_content):
                    self.logMessage.emit(f"Successfully updated {filename}")
                else:
                    self.logMessage.emit(f"Failed to update {filename}")

            self.statusMessage.emit("Config changes saved successfully!", 4000)
            self.logMessage.emit("All config changes saved successfully.")

        except Exception as e:
            self.logMessage.emit(f"Error saving config changes: {e}")
            self.statusMessage.emit("Error saving config changes.", 4000)

    def _download_single_file(self, filename: str) -> str:
        """Downloads a single file from the server."""
        try:
            ftp = FTP_TLS()
            ftp.connect(self.ftp_host, self.ftp_port)
            ftp.login(self.ftp_user, self.ftp_password)
            ftp.prot_p()

            ftp.cwd(self.remote_config_path)

            config_data = io.BytesIO()
            ftp.retrbinary(f'RETR {filename}', config_data.write)
            ftp.quit()

            return config_data.getvalue().decode('utf-8', errors='ignore')

        except Exception as e:
            self.logMessage.emit(f"Error downloading {filename}: {e}")
            return None

    def _update_file_content(self, content: str, items: List[Dict]) -> str:
        """Updates the file content with new StackSize values."""
        lines = content.splitlines()

        # Create a lookup for items by ID and name
        item_lookup = {}
        for item in items:
            key = f"{item.get('id', '')}_{item.get('name', '')}"
            item_lookup[key] = item

        # Process each line
        modified_lines = []
        current_item_id = None
        current_item_name = None
        in_item = False

        item_start_pattern = re.compile(r'^\s*{\s*(?:\+?)(?:Item|Block)\s+Id:\s*(\d+),\s*Name:\s*(\w+)', re.IGNORECASE)
        stack_size_pattern = re.compile(r'^(\s*StackSize:\s*)(\d+)(.*)', re.IGNORECASE)
        item_end_pattern = re.compile(r'^\s*}')

        for line in lines:
            # Check for item start
            item_match = item_start_pattern.match(line)
            if item_match:
                current_item_id = item_match.group(1)
                current_item_name = item_match.group(2)
                in_item = True
                modified_lines.append(line)
                continue

            # Check for item end
            if in_item and item_end_pattern.match(line):
                in_item = False
                current_item_id = None
                current_item_name = None
                modified_lines.append(line)
                continue

            # Check for StackSize line
            if in_item and current_item_id and current_item_name:
                stack_match = stack_size_pattern.match(line)
                if stack_match:
                    key = f"{current_item_id}_{current_item_name}"
                    if key in item_lookup:
                        # Replace StackSize value
                        new_stack_size = item_lookup[key]['stack_size']
                        prefix = stack_match.group(1)
                        suffix = stack_match.group(3)
                        new_line = f"{prefix}{new_stack_size}{suffix}"
                        modified_lines.append(new_line)
                        self.logMessage.emit(f"Updated {current_item_name} StackSize to {new_stack_size}")
                        continue

            # Default: keep line unchanged
            modified_lines.append(line)

        return '\n'.join(modified_lines)

    def _backup_and_upload_file(self, filename: str, new_content: str) -> bool:
        """Creates backup and uploads the modified file with improved backup strategy."""
        try:
            ftp = FTP_TLS()
            ftp.connect(self.ftp_host, self.ftp_port)
            ftp.login(self.ftp_user, self.ftp_password)
            ftp.prot_p()

            ftp.cwd(self.remote_config_path)

            # Get list of existing files
            existing_files = ftp.nlst()

            original_filename = f"{filename}.org"
            backup_filename = f"{filename}.bak"

            # Step 1: Create .org file if it doesn't exist (first-time original backup)
            if original_filename not in existing_files:
                try:
                    # Copy current file to .org (permanent original)
                    ftp.rename(filename, original_filename)
                    self.logMessage.emit(f"Created original backup: {original_filename}")

                    # Download the .org file content to use as current file
                    original_data = io.BytesIO()
                    ftp.retrbinary(f'RETR {original_filename}', original_data.write)

                    # Re-upload it as the current file so we can make a .bak copy
                    original_content_io = io.BytesIO(original_data.getvalue())
                    ftp.storbinary(f'STOR {filename}', original_content_io)
                    self.logMessage.emit(f"Restored current file: {filename}")

                except Exception as e:
                    self.logMessage.emit(f"Warning: Could not create original backup {original_filename}: {e}")

            # Step 2: Create/overwrite .bak file (previous version backup)
            try:
                # If .bak already exists, delete it first
                if backup_filename in existing_files:
                    ftp.delete(backup_filename)
                    self.logMessage.emit(f"Removed old backup: {backup_filename}")

                # Rename current file to .bak
                ftp.rename(filename, backup_filename)
                self.logMessage.emit(f"Created backup: {backup_filename}")

            except Exception as e:
                self.logMessage.emit(f"Warning: Could not create backup {backup_filename}: {e}")

            # Step 3: Upload new content as current file
            new_content_bytes = new_content.encode('utf-8')
            content_io = io.BytesIO(new_content_bytes)

            ftp.storbinary(f'STOR {filename}', content_io)
            self.logMessage.emit(f"Uploaded modified {filename}")

            ftp.quit()
            return True

        except Exception as e:
            self.logMessage.emit(f"Error backing up and uploading {filename}: {e}")
            return False

    def _download_all_ecf_files(self) -> Dict[str, str]:
        """Downloads all .ecf files from the server via FTP."""
        config_files = {}

        try:
            self.logMessage.emit(f"Connecting to FTP server {self.ftp_host}:{self.ftp_port}...")

            # Connect to FTP server
            ftp = FTP_TLS()
            ftp.connect(self.ftp_host, self.ftp_port)
            ftp.login(self.ftp_user, self.ftp_password)
            ftp.prot_p()  # Enable secure data connection

            # Change to the config directory
            ftp.cwd(self.remote_config_path)
            self.logMessage.emit(f"Changed to directory: {self.remote_config_path}")

            # Get list of all files
            files = ftp.nlst()
            ecf_files = [f for f in files if f.lower().endswith('.ecf')]

            if not ecf_files:
                self.logMessage.emit("No .ecf files found in the directory.")
                self.logMessage.emit(f"Available files: {', '.join(files)}")
                ftp.quit()
                return {}

            self.logMessage.emit(f"Found {len(ecf_files)} .ecf files: {', '.join(ecf_files)}")

            # Download each .ecf file
            for filename in ecf_files:
                try:
                    self.logMessage.emit(f"Downloading {filename}...")
                    config_data = io.BytesIO()
                    ftp.retrbinary(f'RETR {filename}', config_data.write)

                    # Convert to string
                    content = config_data.getvalue().decode('utf-8', errors='ignore')
                    config_files[filename] = content
                    self.logMessage.emit(f"Downloaded {filename}: {len(content)} characters")

                except Exception as e:
                    self.logMessage.emit(f"Failed to download {filename}: {e}")
                    continue

            ftp.quit()
            return config_files

        except Exception as e:
            self.logMessage.emit(f"FTP download error: {e}")
            return {}

    def _parse_config_file(self, content: str, filename: str) -> List[Dict]:
        """Parses any .ecf file content and extracts items/blocks with StackSize."""
        items = []
        current_item = {}
        in_item = False
        line_number = 0

        # More flexible regex patterns
        item_start_pattern = re.compile(r'^\s*{\s*(?:\+?)(?:Item|Block)\s+Id:\s*(\d+),?\s*Name:\s*(\w+)', re.IGNORECASE)
        stack_size_pattern = re.compile(r'^\s*StackSize:\s*(\d+)', re.IGNORECASE)
        category_pattern = re.compile(r'^\s*Category:\s*(.+?)(?:,|$)', re.IGNORECASE)
        show_user_pattern = re.compile(r'^\s*ShowUser:\s*(\w+)', re.IGNORECASE)
        item_end_pattern = re.compile(r'^\s*}')

        for line in content.splitlines():
            line_number += 1
            stripped_line = line.strip()

            # Skip comments and empty lines
            if not stripped_line or stripped_line.startswith('#'):
                continue

            # Start of item/block
            item_match = item_start_pattern.match(line)
            if item_match:
                current_item = {
                    'id': item_match.group(1),
                    'name': item_match.group(2),
                    'category': 'Unknown',
                    'show_user': True,
                    'source_file': filename,
                    'line_number': line_number
                }
                in_item = True
                self.logMessage.emit(f"Line {line_number}: Found item start: {current_item['name']} (ID: {current_item['id']})")
                continue

            if in_item:
                # StackSize
                stack_match = stack_size_pattern.match(line)
                if stack_match:
                    try:
                        stack_value = int(stack_match.group(1))
                        current_item['stack_size'] = stack_value
                        self.logMessage.emit(f"Line {line_number}: Found StackSize: {stack_value} for {current_item.get('name', 'Unknown')}")
                    except ValueError as e:
                        self.logMessage.emit(f"Line {line_number}: Error parsing StackSize '{stack_match.group(1)}': {e}")
                    continue

                # Category
                category_match = category_pattern.match(line)
                if category_match:
                    current_item['category'] = category_match.group(1).strip()
                    continue

                # ShowUser
                show_user_match = show_user_pattern.match(line)
                if show_user_match:
                    show_user_value = show_user_match.group(1).lower()
                    current_item['show_user'] = show_user_value in ['yes', 'true', '1']
                    continue

                # End of item/block
                if item_end_pattern.match(line):
                    in_item = False

                    # Add items that have StackSize
                    if 'stack_size' in current_item:
                        items.append(current_item.copy())
                        self.logMessage.emit(f"Line {line_number}: Added item: {current_item['name']} (StackSize: {current_item['stack_size']})")
                    else:
                        self.logMessage.emit(f"Line {line_number}: Skipped item {current_item.get('name', 'Unknown')} - no StackSize found")

                    current_item = {}

        self.logMessage.emit(f"Parsing complete for {filename}: {len(items)} items found")
        return items

    def _should_include_item(self, item: Dict) -> bool:
        """Simple inclusion - just check if it has StackSize."""
        return 'stack_size' in item

    # --- Player action slots ---
    @Slot(str)
    def send_global_message(self, message: str):
        if not message: return
        self.send_command(f"say '{message}'")
    @Slot()
    def save_server(self):
        self.send_command("save")
    @Slot(str, str)
    def kick_player(self, player_name: str, reason: str):
        if not player_name: return
        reason_text = reason if reason else "N/A"
        command = f"kick '{player_name}' '{reason_text}'"
        self.send_command(command)

    @Slot(str)
    def ban_player(self, player_id: str):
        """Bans a player by their ID for 1 hour."""
        if not player_id: return
        command = f"ban {player_id} 1h"
        self.send_command(command)
        self.logMessage.emit(f"Ban command sent for ID: {player_id} (1 hour)")

    @Slot(str)
    def unban_player(self, player_id: str):
        """Unbans a player by their ID."""
        if not player_id: return
        command = f"unban {player_id}"
        self.send_command(command)
        self.logMessage.emit(f"Unban command sent for ID: {player_id}")

    @Slot(str, str)
    def send_private_message(self, player_name: str, message: str):
        if not player_name or not message: return
        self.send_command(f"pm '{player_name}' '{message}'")
