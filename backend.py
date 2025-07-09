# backend.py – ENHANCED VERSION 0.2.6-dev (2025‑07‑08)
# -----------------------------------------------------------------------------
# NEW: Enhanced Player Management with Persistent Database Storage
# - All known players stored in database permanently
# - Live status/IP/playfield updated each cycle
# - Status change timestamps tracked
# - Complete player registry for hobby server admins
# 
# Previous fixes maintained:
# - FIXED: Double message sending issue resolved
# - FIXED: Removed daily/custom scheduling - only interval-based scheduling
# - FIXED: Improved timer frequency (30 seconds) for better responsiveness
# - Robust regex for "Players connected" (Empyrion output)
# - SAFE SQLite access (no thread errors): DB connection per-use, no shared connection
# - Fixed indentation and syntax errors in config file methods
# - FIXED: Messaging commands now properly use single quotes around message text
# - FIXED: Scheduled messages error handling and None value protection
# -----------------------------------------------------------------------------

import socket
import time
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import configparser
import os
import sqlite3
from ftplib import FTP_TLS, error_perm
import io

from PySide6.QtCore import QObject, Signal, Slot, QTimer

class Worker(QObject):
    # ------------------------------------------------------------------
    # Qt Signals
    # ------------------------------------------------------------------
    connectionStatusChanged = Signal(bool, str)
    logMessage = Signal(str)
    playersUpdated = Signal(list)
    playerHistoryUpdated = Signal(list)
    entitiesUpdated = Signal(list)
    configDataUpdated = Signal(list)
    statusMessage = Signal(str, int)
    scheduledMessagesLoaded = Signal(list)

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    def __init__(self, config_file="empyrion_helper.conf"):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # --- server params ---
        self.host = self.config.get('server', 'host', fallback='localhost')
        self.port = self.config.getint('server', 'telnet_port', fallback=30004)
        self.password = self.config.get('server', 'telnet_password', fallback='')

        # --- ftp params ---
        ftp_addr = self.config.get('ftp', 'host', fallback='')
        self.ftp_host, self.ftp_port = ftp_addr.split(':')[0], 21
        if ':' in ftp_addr:
            try:
                self.ftp_port = int(ftp_addr.split(':')[1])
            except ValueError:
                pass
        self.ftp_user = self.config.get('ftp', 'user', fallback='')
        self.ftp_password = self.config.get('ftp', 'password', fallback='')
        self.remote_config_path = self.config.get('ftp', 'remote_log_path', fallback='/')

        # --- state
        self.socket = None
        self.connected = False
        self._running = False
        self.update_interval = self.config.getint('monitoring', 'update_interval', fallback=30)

        # --- timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.force_player_update)

        # IMPROVED: More frequent message checking (30 seconds) for better reliability
        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self.check_scheduled_messages)
        self.scheduled_messages = []
        self.last_message_check: Dict[int, datetime] = {}

        # --- config data storage
        self.config_data = []

        # --- template names for config parsing
        self.TEMPLATE_NAMES = {"FoodTemplate", "OreTemplate", "ComponentsTemplate"}

        # --- NEW: Player management state
        self.known_players: Dict[str, Dict] = {}  # steam_id -> player_data cache

        # --- Ensure DB is initialized (in main thread is fine, but no connection kept)
        self._init_database()

    # ------------------------------------------------------------------
    # DB Setup (ENHANCED - now includes players table)
    # ------------------------------------------------------------------
    def _init_database(self):
        try:
            db_conn = sqlite3.connect('player_history.db')
            c = db_conn.cursor()
            
            # Existing player_events table
            c.execute('''CREATE TABLE IF NOT EXISTS player_events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT, steam_id TEXT, player_name TEXT,
                            playfield_name TEXT, event_type TEXT,
                            UNIQUE(timestamp, steam_id, event_type))''')
            
            # Existing entities table
            c.execute('''CREATE TABLE IF NOT EXISTS entities (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            entity_id TEXT, type TEXT, faction TEXT,
                            name TEXT, playfield TEXT)''')
            
            # NEW: Players registry table
            c.execute('''CREATE TABLE IF NOT EXISTS players (
                            steam_id TEXT PRIMARY KEY,
                            player_name TEXT NOT NULL,
                            faction TEXT,
                            role TEXT,
                            last_seen_online TEXT,
                            last_seen_offline TEXT,
                            first_seen TEXT,
                            last_updated TEXT)''')
            
            db_conn.commit()
            db_conn.close()
            self.logMessage.emit("Database initialized with enhanced player management")
        except Exception as e:
            self.logMessage.emit(f"Database error initializing: {e}")

    # ------------------------------------------------------------------
    # NEW: Player Database Operations
    # ------------------------------------------------------------------
    def _load_all_known_players(self) -> Dict[str, Dict]:
        """Load all known players from database into memory cache"""
        try:
            db_conn = sqlite3.connect('player_history.db')
            c = db_conn.cursor()
            c.execute('''SELECT steam_id, player_name, faction, role, 
                                last_seen_online, last_seen_offline, 
                                first_seen, last_updated FROM players''')
            
            players = {}
            for row in c.fetchall():
                steam_id, name, faction, role, last_online, last_offline, first_seen, last_updated = row
                players[steam_id] = {
                    'id': steam_id,
                    'name': name or 'Unknown',
                    'faction': faction or '',
                    'role': role or '',
                    'last_seen_online': last_online,
                    'last_seen_offline': last_offline,
                    'first_seen': first_seen,
                    'last_updated': last_updated,
                    'status': 'Offline',  # Default to offline, will be updated by live data
                    'ip': '',  # Live data only
                    'playfield': ''  # Live data only
                }
            
            db_conn.close()
            self.logMessage.emit(f"Loaded {len(players)} known players from database")
            return players
        except Exception as e:
            self.logMessage.emit(f"Error loading players from database: {e}")
            return {}

    def _update_player_in_db(self, player_data: Dict, status_changed: bool = False):
        """Update or insert player data in database"""
        try:
            db_conn = sqlite3.connect('player_history.db')
            c = db_conn.cursor()
            
            current_time = datetime.now().isoformat()
            steam_id = player_data['id']
            
            # Check if player exists
            c.execute('SELECT steam_id, last_seen_online, last_seen_offline FROM players WHERE steam_id = ?', (steam_id,))
            existing = c.fetchone()
            
            if existing:
                # Update existing player
                update_fields = [
                    'player_name = ?', 'faction = ?', 'role = ?', 'last_updated = ?'
                ]
                update_values = [
                    player_data['name'], player_data['faction'], 
                    player_data['role'], current_time
                ]
                
                # Update status timestamps if status changed
                if status_changed:
                    if player_data['status'] == 'Online':
                        update_fields.append('last_seen_online = ?')
                        update_values.append(current_time)
                    else:  # Offline
                        update_fields.append('last_seen_offline = ?')
                        update_values.append(current_time)
                
                query = f"UPDATE players SET {', '.join(update_fields)} WHERE steam_id = ?"
                update_values.append(steam_id)
                c.execute(query, update_values)
                
            else:
                # Insert new player
                initial_online = current_time if player_data['status'] == 'Online' else None
                initial_offline = current_time if player_data['status'] == 'Offline' else None
                
                c.execute('''INSERT INTO players 
                            (steam_id, player_name, faction, role, 
                             last_seen_online, last_seen_offline, first_seen, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (steam_id, player_data['name'], player_data['faction'], player_data['role'],
                          initial_online, initial_offline, current_time, current_time))
                
                self.logMessage.emit(f"New player registered: {player_data['name']} ({steam_id})")
            
            db_conn.commit()
            db_conn.close()
            
        except Exception as e:
            self.logMessage.emit(f"Error updating player in database: {e}")

    def _merge_live_data_with_known_players(self, live_players: List[Dict]) -> List[Dict]:
        """Merge live player data with known players from database"""
        # Create lookup for live players
        live_lookup = {p['id']: p for p in live_players}
        
        # Start with all known players from database
        merged_players = dict(self.known_players)
        
        # First: Update all known players with live data where available
        for steam_id, known_player in list(merged_players.items()):
            if steam_id in live_lookup:
                # Player is in live data - update with current info
                live_player = live_lookup[steam_id]
                old_status = known_player.get('status', 'Offline')
                old_name = known_player.get('name', '')
                old_faction = known_player.get('faction', '')
                old_role = known_player.get('role', '')
                
                # Merge live data
                merged_player = {
                    'id': steam_id,
                    'name': live_player['name'],
                    'faction': live_player['faction'],
                    'role': live_player['role'],
                    'status': live_player['status'],
                    'ip': live_player['ip'],
                    'playfield': live_player['playfield'],
                    # Preserve database timestamps
                    'last_seen_online': known_player.get('last_seen_online'),
                    'last_seen_offline': known_player.get('last_seen_offline'),
                    'first_seen': known_player.get('first_seen'),
                    'last_updated': known_player.get('last_updated')
                }
                
                # Detect changes that need database updates
                status_changed = (old_status != live_player['status'])
                data_changed = (old_name != live_player['name'] or 
                              old_faction != live_player['faction'] or 
                              old_role != live_player['role'])
                
                # Update database if needed
                if status_changed or data_changed:
                    self._update_player_in_db(merged_player, status_changed)
                    
                    if status_changed:
                        status_msg = f"{live_player['name']} went {live_player['status'].lower()}"
                        self.logMessage.emit(status_msg)
                
                merged_players[steam_id] = merged_player
            else:
                # Player NOT in live data - mark as offline if they were online
                if known_player.get('status') == 'Online':
                    known_player['status'] = 'Offline'
                    known_player['ip'] = ''
                    known_player['playfield'] = ''
                    self._update_player_in_db(known_player, status_changed=True)
                    self.logMessage.emit(f"{known_player['name']} went offline")
        
        # Second: Add any completely new players from live data
        for steam_id, live_player in live_lookup.items():
            if steam_id not in merged_players:
                # Brand new player
                new_player = {
                    'id': steam_id,
                    'name': live_player['name'],
                    'faction': live_player['faction'],
                    'role': live_player['role'],
                    'status': live_player['status'],
                    'ip': live_player['ip'],
                    'playfield': live_player['playfield'],
                    'last_seen_online': None,
                    'last_seen_offline': None,
                    'first_seen': None,
                    'last_updated': None
                }
                
                # Add to database
                self._update_player_in_db(new_player, status_changed=True)
                merged_players[steam_id] = new_player
        
        # Update cache
        self.known_players = merged_players
        
        # Return ALL players (online and offline) sorted by status then name
        all_players = list(merged_players.values())
        self.logMessage.emit(f"Merged player data: {len(live_players)} live players, {len(all_players)} total known players")
        
        return sorted(all_players, 
                     key=lambda p: (p['status'] != 'Online', p['name'].lower()))

    # ------------------------------------------------------------------
    # Telnet helpers
    # ------------------------------------------------------------------
    def _read_until(self, delim: bytes, timeout: int = 5) -> bytes:
        data, start = b'', time.time()
        while time.time() - start < timeout:
            try:
                chunk = self.socket.recv(1)
                if not chunk:
                    break
                data += chunk
                if data.endswith(delim):
                    break
            except socket.timeout:
                break
        return data

    # ------------------------------------------------------------------
    # Monitoring start/stop (ENHANCED)
    # ------------------------------------------------------------------
    @Slot()
    def start_monitoring(self):
        self._running = True
        try:
            self.statusMessage.emit('Connecting...', 0)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            if self.password:
                self._read_until(b'Password:')
                self.socket.send(f"{self.password}\r\n".encode())
            self._read_until(b'>')
            self.connected = True
            self.connectionStatusChanged.emit(True, 'Connected')
            self.logMessage.emit('Successfully connected to server')
        except Exception as e:
            self.connectionStatusChanged.emit(False, f'Connection failed: {e}')
            self.logMessage.emit(f'Connection failed: {e}')
            self._running = False
            return

        # NEW: Load known players from database first
        self.known_players = self._load_all_known_players()
        
        self.force_player_update()
        self.timer.start(self.update_interval * 1000)
        # IMPROVED: Check messages every 30 seconds instead of 60
        self.message_timer.start(30000)
        self.load_scheduled_messages()  # Auto-load messages

    @Slot()
    def stop_monitoring(self):
        self._running = False
        self.timer.stop()
        self.message_timer.stop()
        if self.socket:
            try:
                self.socket.send(b'exit\r\n')
                self.socket.close()
            except Exception:
                pass
        self.connected = False
        self.connectionStatusChanged.emit(False, 'Disconnected')
        self.logMessage.emit('Disconnected from server')

    # ------------------------------------------------------------------
    # send_command
    # ------------------------------------------------------------------
    def send_command(self, cmd: str) -> str:
        if not self.connected or not self.socket:
            return 'Not connected'
        try:
            self.socket.send(f"{cmd}\r\n".encode())
            txt = self._read_until(b'>', 20).decode('ascii', 'ignore').strip()
            return txt[:-1].strip() if txt.endswith('>') else txt
        except Exception as e:
            self.connected = False
            self.connectionStatusChanged.emit(False, 'Connection lost')
            self.logMessage.emit(f"Connection lost: {e}")
            return f'Error: {e}'

    # ------------------------------------------------------------------
    # force_player_update (ENHANCED)
    # ------------------------------------------------------------------
    @Slot()
    def force_player_update(self):
        if not self.connected:
            return
        
        # Get live player data from server
        live_players = self.get_player_list_from_plys()
        
        # Merge with known players and update database
        merged_players = self._merge_live_data_with_known_players(live_players)
        
        # Emit updated player list
        self.playersUpdated.emit(merged_players)
        
        # Store events (keeping existing functionality)
        self._store_player_events(live_players)

    # ------------------------------------------------------------------
    # get_player_list_from_plys (UNCHANGED - still works perfectly)
    # ------------------------------------------------------------------
    def get_player_list_from_plys(self) -> List[Dict]:
        rsp = self.send_command('plys')
        players: Dict[str, Dict] = {}

        # First: Parse "Players connected" to get who is actually online right now
        currently_online_ids = set()
        pc_re = re.compile(
            r"(\d+):\s*(-?\d+),\s*([^,]+),\s*([^,]+),\s*([\d\.]+)\|(\d+)"
        )
        in_conn = False
        for ln in rsp.splitlines():
            if 'Players connected' in ln:
                in_conn = True
                continue
            if not ln.strip():
                in_conn = False
            if in_conn and not ln.strip().startswith('-'):
                m = pc_re.search(ln.strip())
                if m:
                    _, pid, nm, pf, ip, _ = m.groups()
                    currently_online_ids.add(pid)
                    # Store online player with live data
                    players[pid] = {
                        'id': pid,
                        'name': nm.strip(),
                        'faction': '',  # Will be filled from global list
                        'role': '',     # Will be filled from global list
                        'status': 'Online',
                        'ip': ip,
                        'playfield': pf
                    }

        # Second: Parse "Global players list" to get ALL players with faction/role info
        gp_re = re.compile(r"id=([-\d]+) name=(.+?) fac=\[([^\]]+)\] role=(\w+)(?: online=(\d+))?")
        in_global = False
        for ln in rsp.splitlines():
            if 'Global players list' in ln:
                in_global = True
                continue
            if not ln.strip():
                in_global = False
            if in_global:
                m = gp_re.search(ln)
                if m:
                    pid, nm, fac, role, playtime = m.groups()
                    
                    # Determine if player is online or offline
                    is_online = pid in currently_online_ids
                    
                    if pid in players:
                        # Update existing online player with faction/role
                        players[pid]['faction'] = fac.strip()
                        players[pid]['role'] = role.strip()
                    else:
                        # Add offline player
                        players[pid] = {
                            'id': pid,
                            'name': nm.strip(),
                            'faction': fac.strip(),
                            'role': role.strip(),
                            'status': 'Offline',
                            'ip': '',
                            'playfield': ''
                        }

        # Third: Handle "Global online players list" (backup for faction/role if needed)
        go_re = re.compile(r"id=([-\d]+) name=(.+?) fac=\[([^\]]+)\] role=(\w+)")
        in_online = False
        for ln in rsp.splitlines():
            if 'Global online players list' in ln:
                in_online = True
                continue
            if not ln.strip():
                in_online = False
            if in_online:
                m = go_re.search(ln)
                if m:
                    pid, nm, fac, role = m.groups()
                    if pid in players:
                        # Update faction/role info if needed
                        players[pid]['faction'] = fac.strip()
                        players[pid]['role'] = role.strip()

        player_list = sorted(players.values(), key=lambda p: (p['status'] != 'Online', p['name'].lower()))
        self.logMessage.emit(f"Parsed plys command: {len(currently_online_ids)} online, {len(player_list)} total players")
        
        return player_list

    # ------------------------------------------------------------------
    # Server Actions (UNCHANGED)
    # ------------------------------------------------------------------
    @Slot()
    def save_server(self):
        """Save server state"""
        result = self.send_command('saveall')
        self.logMessage.emit(f"Server save command executed: {result}")
        self.statusMessage.emit('Server saved', 3000)

    @Slot()
    def kick_player(self, player_name: str, reason: str = ""):
        """Kick a player from the server"""
        cmd = f"kick '{player_name}'"
        if reason:
            cmd += f" {reason}"
        result = self.send_command(cmd)
        self.logMessage.emit(f"Kick command for {player_name}: {result}")
        self.statusMessage.emit(f'Player {player_name} kicked', 3000)

    @Slot()
    def ban_player(self, player_id: str, duration: str = "1h"):
        """Ban a player by ID"""
        cmd = f"ban {player_id} {duration}"
        result = self.send_command(cmd)
        self.logMessage.emit(f"Ban command for player ID {player_id}: {result}")
        self.statusMessage.emit(f'Player ID {player_id} banned for {duration}', 3000)

    @Slot()
    def unban_player(self, player_id: str):
        """Unban a player by ID"""
        cmd = f"unban {player_id}"
        result = self.send_command(cmd)
        self.logMessage.emit(f"Unban command for player ID {player_id}: {result}")
        self.statusMessage.emit(f'Player ID {player_id} unbanned', 3000)

    @Slot()
    def send_private_message(self, player_name: str, message: str):
        """Send private message to a player"""
        # FIXED: Add single quotes around the message text
        cmd = f"pm '{player_name}' '{message}'"
        result = self.send_command(cmd)
        self.logMessage.emit(f"Private message sent to {player_name}: {message}")
        self.statusMessage.emit(f'Message sent to {player_name}', 3000)

    @Slot()
    def send_global_message(self, message: str):
        """Send global message to all players"""
        if not message.strip():
            self.logMessage.emit("Cannot send empty global message")
            return
        # FIXED: Add single quotes around the message text
        cmd = f"say '{message}'"
        result = self.send_command(cmd)
        self.logMessage.emit(f"Global message sent: {message}")
        self.statusMessage.emit('Global message sent', 3000)

    # ------------------------------------------------------------------
    # Entity Management (UNCHANGED)
    # ------------------------------------------------------------------
    @Slot()
    def load_entities(self):
        """Load entities from server using gents command"""
        self.logMessage.emit("Loading entities from server...")
        result = self.send_command('gents')
        entities = self._parse_entities(result)
        self._store_entities(entities)
        self.entitiesUpdated.emit(entities)
        self.logMessage.emit(f"Loaded {len(entities)} entities")

    @Slot()
    def save_raw_gents_output(self):
        """Save raw gents command output to file"""
        result = self.send_command('gents')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"gents_output_{timestamp}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result)
            self.logMessage.emit(f"Raw gents output saved to {filename}")
            self.statusMessage.emit(f'Raw output saved to {filename}', 3000)
        except Exception as e:
            self.logMessage.emit(f"Error saving raw gents output: {e}")

    def _parse_entities(self, gents_output: str) -> List[Dict]:
        """Parse entities from gents command output"""
        entities = []
        current_playfield = ""

        for line in gents_output.splitlines():
            line = line.strip()
            if not line:
                continue

            # Check for playfield header
            if line.startswith('Playfield:'):
                current_playfield = line.replace('Playfield:', '').strip()
                continue

            # Parse entity lines - this is a basic parser, adjust regex as needed
            entity_match = re.match(r'(\d+):\s*(\w+)\s*\[([^\]]*)\]\s*(.*)', line)
            if entity_match:
                entity_id, entity_type, faction, name = entity_match.groups()
                entities.append({
                    'playfield': current_playfield,
                    'entity_id': entity_id.strip(),
                    'type': entity_type.strip(),
                    'faction': faction.strip(),
                    'name': name.strip()
                })

        return entities

    # ------------------------------------------------------------------
    # Config File Management (UNCHANGED)
    # ------------------------------------------------------------------
    @Slot()
    def load_config_file(self):
        """Load config files from server via FTP"""
        self.logMessage.emit("Loading config files from server...")

        try:
            config_items = self._fetch_config_from_ftp()
            self.config_data = config_items
            self.configDataUpdated.emit(config_items)
            self.logMessage.emit(f"Loaded {len(config_items)} config items")
        except Exception as e:
            self.logMessage.emit(f"Error loading config files: {e}")
            # Emit empty list if failed
            self.configDataUpdated.emit([])

    @Slot()
    def save_config_changes(self, config_data: List[Dict]):
        """Save config changes back to server"""
        self.logMessage.emit("Saving config changes to server...")

        try:
            self._upload_config_to_ftp(config_data)
            self.logMessage.emit("Config changes saved successfully")
            self.statusMessage.emit('Config changes saved', 3000)
        except Exception as e:
            self.logMessage.emit(f"Error saving config changes: {e}")

    def _fetch_config_from_ftp(self) -> List[Dict]:
        """Fetch config files from FTP server and parse them"""
        config_items = []

        if not self.ftp_host or not self.ftp_user:
            self.logMessage.emit("FTP not configured - returning sample config data")
            # Return sample data for testing
            return [
                {'name': 'FoodTemplate', 'stack_size': 100, 'category': 'Food', 'source_file': 'Config_Example.ecf'},
                {'name': 'IronIngot', 'stack_size': 500, 'category': 'Material', 'source_file': 'Config_Example.ecf'},
                {'name': 'SteelPlate', 'stack_size': 250, 'category': 'Component', 'source_file': 'Config_Example.ecf'},
            ]

        try:
            # Connect to FTP
            ftp = FTP_TLS()
            ftp.connect(self.ftp_host, self.ftp_port)
            ftp.login(self.ftp_user, self.ftp_password)
            ftp.prot_p()  # Enable encryption

            # Change to config directory
            ftp.cwd(self.remote_config_path)

            # Get list of .ecf files
            files = []
            ftp.retrlines('LIST *.ecf', files.append)

            # Parse each config file
            for file_line in files:
                filename = file_line.split()[-1]
                if filename.endswith('.ecf'):
                    config_items.extend(self._parse_config_file(ftp, filename))

            ftp.quit()

        except Exception as e:
            self.logMessage.emit(f"FTP error: {e}")
            raise

        return config_items

    def _parse_config_file(self, ftp, filename: str) -> List[Dict]:
        """Parse a single config file and return items"""
        items = []
        try:
            content = io.BytesIO()
            ftp.retrbinary(f'RETR {filename}', content.write)
            content.seek(0)
            lines = content.read().decode('utf-8').splitlines()

            current_item = None
            inside_block = False

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('{'):
                    name = line[1:].strip()
                    current_item = {
                        'name': name,
                        'stack_size': None,
                        'category': 'Unknown',
                        'source_file': filename,
                        'is_template': name in self.TEMPLATE_NAMES
                    }
                    inside_block = True
                    continue

                if line.startswith('}') and inside_block:
                    if current_item and current_item['stack_size'] is not None:
                        items.append(current_item)
                    current_item = None
                    inside_block = False
                    continue

                if inside_block:
                    if line.startswith('StackSize:'):
                        try:
                            current_item['stack_size'] = int(line.split(':')[1].strip())
                        except ValueError:
                            pass
                    elif line.startswith('Category:'):
                        current_item['category'] = line.split(':')[1].strip()

        except Exception as e:
            self.logMessage.emit(f"Error parsing {filename}: {e}")

        return items

    def _upload_config_to_ftp(self, config_data: List[Dict]):
        """Upload modified config files back to FTP"""
        if not self.ftp_host or not self.ftp_user:
            self.logMessage.emit("FTP not configured - simulating config save")
            return

        try:
            # Connect to FTP
            ftp = FTP_TLS()
            ftp.connect(self.ftp_host, self.ftp_port)
            ftp.login(self.ftp_user, self.ftp_password)
            ftp.prot_p()

            # Group changes by source file
            files_to_update = {}
            for item in config_data:
                source_file = item.get('source_file', 'Config_Example.ecf')
                if source_file not in files_to_update:
                    files_to_update[source_file] = []
                files_to_update[source_file].append(item)

            # Update each file
            for filename, items in files_to_update.items():
                self._update_config_file(ftp, filename, items)

            ftp.quit()

        except Exception as e:
            self.logMessage.emit(f"FTP upload error: {e}")
            raise

    def _update_config_file(self, ftp, filename: str, items: List[Dict]):
        """Update a single config file with new item data"""
        self.logMessage.emit(f"Preparing to update {filename} with {len(items)} items")

        try:
            content = io.BytesIO()
            content.write("# Auto-generated config update\n".encode('utf-8'))

            for item in items:
                content.write(f"{{ {item['name']}\n".encode('utf-8'))
                content.write(f"  StackSize: {item['stack_size']}\n".encode('utf-8'))
                if item['category']:
                    content.write(f"  Category: {item['category']}\n".encode('utf-8'))
                content.write(b"}\n\n")

            content.seek(0)

            # Check if original backup exists
            filenames = ftp.nlst()
            if f"{filename}.org" not in filenames:
                ftp.rename(filename, f"{filename}.org")
            else:
                if f"{filename}.bak" in filenames:
                    ftp.delete(f"{filename}.bak")
                ftp.rename(filename, f"{filename}.bak")

            # Upload new file
            ftp.storbinary(f'STOR {filename}', content)
            self.logMessage.emit(f"{filename} updated and uploaded successfully")

        except Exception as e:
            self.logMessage.emit(f"Error updating {filename}: {e}")

    # ------------------------------------------------------------------
    # Scheduled Messages (FIXED - NO MORE DOUBLE SENDS!)
    # ------------------------------------------------------------------
    @Slot()
    def check_scheduled_messages(self):
        """Check and send scheduled messages - IMPROVED to prevent double sends"""
        current_time = datetime.now()

        for i, msg_data in enumerate(self.scheduled_messages):
            # Ensure msg_data is a dict
            if not isinstance(msg_data, dict):
                continue

            if not msg_data.get('enabled', False):
                continue

            # Fix: Handle None values properly
            message_text = msg_data.get('text', '') or ''
            message = message_text.strip()
            if not message:
                continue

            schedule = msg_data.get('schedule', 'Every 5 minutes')

            # Check if it's time to send this message
            if self._should_send_message(i, schedule, current_time):
                self.send_global_message(message)
                self.last_message_check[i] = current_time
                self.logMessage.emit(f"Scheduled message {i+1} sent: {message}")

    def _should_send_message(self, msg_index: int, schedule: str, current_time: datetime) -> bool:
        """FIXED: Check if a scheduled message should be sent - NO first-time immediate send"""
        last_sent = self.last_message_check.get(msg_index)
        
        # FIXED: Don't send immediately on first run - wait for proper interval
        if not last_sent:
            # Set initial timestamp to prevent immediate sending
            self.last_message_check[msg_index] = current_time
            return False

        # SIMPLIFIED: Only handle minute and hour intervals (removed daily/custom)
        if 'minute' in schedule:
            try:
                minutes = int(re.search(r'(\d+)', schedule).group(1))
                time_diff = current_time - last_sent
                required_interval = timedelta(minutes=minutes)
                return time_diff >= required_interval
            except (AttributeError, ValueError):
                return False
        elif 'hour' in schedule:
            try:
                hours = int(re.search(r'(\d+)', schedule).group(1))
                time_diff = current_time - last_sent
                required_interval = timedelta(hours=hours)
                return time_diff >= required_interval
            except (AttributeError, ValueError):
                return False

        return False

    @Slot()
    def save_scheduled_messages(self, messages_data: List[Dict]):
        """Save scheduled messages to config file"""
        self.scheduled_messages = messages_data

        try:
            # Save to JSON file
            with open('scheduled_messages.json', 'w') as f:
                json.dump(messages_data, f, indent=2)

            self.logMessage.emit("Scheduled messages saved")
            self.statusMessage.emit('Scheduled messages saved', 3000)

        except Exception as e:
            self.logMessage.emit(f"Error saving scheduled messages: {e}")

    @Slot()
    def load_scheduled_messages(self):
        """Load scheduled messages from config file"""
        try:
            if os.path.exists('scheduled_messages.json'):
                with open('scheduled_messages.json', 'r') as f:
                    messages_data = json.load(f)

                # Validate and clean the data
                if not isinstance(messages_data, list):
                    messages_data = []

                # Ensure each message has required fields
                cleaned_messages = []
                for msg in messages_data:
                    if isinstance(msg, dict):
                        cleaned_msg = {
                            'enabled': bool(msg.get('enabled', False)),
                            'text': str(msg.get('text', '')),
                            'schedule': str(msg.get('schedule', 'Every 5 minutes'))
                        }
                        cleaned_messages.append(cleaned_msg)

                self.scheduled_messages = cleaned_messages
                self.scheduledMessagesLoaded.emit(cleaned_messages)
                self.logMessage.emit(f"Loaded {len(cleaned_messages)} scheduled messages")
            else:
                # Return empty messages if file doesn't exist
                empty_messages = [{'enabled': False, 'text': '', 'schedule': 'Every 5 minutes'} for _ in range(5)]
                self.scheduled_messages = empty_messages
                self.scheduledMessagesLoaded.emit(empty_messages)
                self.logMessage.emit("No scheduled messages file found, loaded empty configuration")

        except Exception as e:
            self.logMessage.emit(f"Error loading scheduled messages: {e}")
            # Return empty messages on error
            empty_messages = [{'enabled': False, 'text': '', 'schedule': 'Every 5 minutes'} for _ in range(5)]
            self.scheduled_messages = empty_messages
            self.scheduledMessagesLoaded.emit(empty_messages)

    # ------------------------------------------------------------------
    # Database Operations (ENHANCED + existing functionality maintained)
    # ------------------------------------------------------------------
    def _store_player_events(self, players: List[Dict]):
        """Store player events in database (new connection per use, thread-safe)"""
        try:
            db_conn = sqlite3.connect('player_history.db')
            c = db_conn.cursor()
            timestamp = datetime.now().isoformat()
            for player in players:
                c.execute('''INSERT OR IGNORE INTO player_events
                            (timestamp, steam_id, player_name, playfield_name, event_type)
                            VALUES (?, ?, ?, ?, ?)''',
                         (timestamp, player['id'], player['name'],
                          player['playfield'], player['status']))
            db_conn.commit()
            db_conn.close()
        except Exception as e:
            self.logMessage.emit(f"Database error storing player events: {e}")

    def _store_entities(self, entities: List[Dict]):
        """Store entities in database (new connection per use, thread-safe)"""
        try:
            db_conn = sqlite3.connect('player_history.db')
            c = db_conn.cursor()
            # Clear existing entities
            c.execute('DELETE FROM entities')
            # Insert new entities
            for entity in entities:
                c.execute('''INSERT INTO entities
                            (entity_id, type, faction, name, playfield)
                            VALUES (?, ?, ?, ?, ?)''',
                         (entity['entity_id'], entity['type'], entity['faction'],
                          entity['name'], entity['playfield']))
            db_conn.commit()
            db_conn.close()
        except Exception as e:
            self.logMessage.emit(f"Database error storing entities: {e}")
