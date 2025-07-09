# main_app.py - Enhanced with Player Management Filters
import sys
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QPushButton, QTabWidget, QTextEdit, QLabel,
                               QLineEdit, QHBoxLayout, QFormLayout, QTableWidget,
                               QTableWidgetItem, QMenu, QInputDialog, QHeaderView,
                               QComboBox, QStatusBar, QMessageBox, QCheckBox)
from PySide6.QtCore import QThread, Slot, Qt
from backend import Worker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Empyrion Server Helper v0.2.6-alpha")
        self.setGeometry(100, 100, 1000, 700)

        self.thread = None
        self.worker = None
        self.all_entities_data = []
        self.all_config_data = []
        self.all_players_data = []  # NEW: Store all player data for filtering

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_dashboard_tab()
        self.create_entities_tab()
        self.create_config_editor_tab()
        self.create_scheduled_messages_tab()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.permanent_status_label = QLabel("Status: Not Connected")
        self.statusBar.addPermanentWidget(self.permanent_status_label)

        # Load autoconnect setting and connect if enabled (after all tabs are created)
        self.load_autoconnect_setting()
        if self.autoconnect_checkbox.isChecked():
            self.start_worker()

    def create_dashboard_tab(self):
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)

        # --- Connection Controls ---
        control_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.autoconnect_checkbox = QCheckBox("Autoconnect")
        self.autoconnect_checkbox.stateChanged.connect(self.on_autoconnect_changed)

        control_layout.addWidget(self.connect_button)
        control_layout.addWidget(self.disconnect_button)
        control_layout.addWidget(self.autoconnect_checkbox)
        control_layout.addStretch()

        # --- Player Table with Filters (ENHANCED) ---
        player_list_layout = QVBoxLayout()

        player_header_layout = QHBoxLayout()
        player_header_layout.addWidget(QLabel("Players (All Known Players):"))
        player_header_layout.addStretch()
        self.refresh_players_button = QPushButton("Refresh")
        self.refresh_players_button.setEnabled(False)
        player_header_layout.addWidget(self.refresh_players_button)
        player_list_layout.addLayout(player_header_layout)

        # NEW: Player filters (like entity tab) - Updated for new Last Seen column
        player_filter_layout = QHBoxLayout()
        self.player_column_headers = ["Steam ID", "Name", "Status", "Faction", "IP Address", "Playfield", "Last Seen"]
        self.player_filter_inputs = []
        for header in self.player_column_headers:
            filter_input = QLineEdit()
            filter_input.setPlaceholderText(f"Filter {header}...")
            filter_input.textChanged.connect(self.filter_players_table)
            self.player_filter_inputs.append(filter_input)
            player_filter_layout.addWidget(filter_input)
        player_list_layout.addLayout(player_filter_layout)

        self.player_table = QTableWidget()
        self.player_table.setColumnCount(7)  # Added Last Seen column
        self.player_table.setHorizontalHeaderLabels(["Steam ID", "Name", "Status", "Faction", "IP Address", "Playfield", "Last Seen"])
        self.player_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.player_table.setEditTriggers(QTableWidget.EditTriggers.NoEditTriggers)
        self.player_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.player_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.player_table.customContextMenuRequested.connect(self.open_player_menu)
        self.player_table.setSortingEnabled(True)  # Enable sorting
        player_list_layout.addWidget(self.player_table)

        # --- Server Actions ---
        actions_layout = QFormLayout()
        self.save_button = QPushButton("Save Server")
        actions_layout.addRow(self.save_button)

        # --- Log venster ---
        log_layout = QVBoxLayout()
        log_layout.addWidget(QLabel("Logs:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        log_layout.addWidget(self.log_box)

        layout.addLayout(control_layout)
        layout.addLayout(player_list_layout)
        layout.addLayout(actions_layout)
        layout.addLayout(log_layout)

        self.tabs.addTab(dashboard_widget, "Dashboard")

        self.connect_button.clicked.connect(self.start_worker)
        self.disconnect_button.clicked.connect(self.stop_worker)

    def create_entities_tab(self):
        """Creates the tab for viewing and filtering game entities."""
        entities_widget = QWidget()
        layout = QVBoxLayout(entities_widget)

        top_control_panel = QHBoxLayout()
        self.load_entities_button = QPushButton("Load/Refresh Entities")
        self.load_entities_button.setEnabled(False)
        top_control_panel.addWidget(self.load_entities_button)

        self.save_raw_gents_button = QPushButton("Save Raw 'gents' Output to File")
        self.save_raw_gents_button.setEnabled(False)
        top_control_panel.addWidget(self.save_raw_gents_button)

        top_control_panel.addStretch()
        layout.addLayout(top_control_panel)

        filter_panel_layout = QHBoxLayout()
        self.entity_column_headers = ["Playfield", "Entity ID", "Type", "Faction", "Name"]
        self.entity_filter_inputs = []
        for header in self.entity_column_headers:
            filter_input = QLineEdit()
            filter_input.setPlaceholderText(f"Filter {header}...")
            filter_input.textChanged.connect(self.filter_entities_table)
            self.entity_filter_inputs.append(filter_input)
            filter_panel_layout.addWidget(filter_input)
        layout.addLayout(filter_panel_layout)

        self.entities_table = QTableWidget()
        self.entities_table.setColumnCount(len(self.entity_column_headers))
        self.entities_table.setHorizontalHeaderLabels(self.entity_column_headers)
        self.entities_table.setEditTriggers(QTableWidget.EditTriggers.NoEditTriggers)
        self.entities_table.setSortingEnabled(True)
        header = self.entities_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.entities_table)
        self.tabs.addTab(entities_widget, "Entities")

    def create_config_editor_tab(self):
        """Creates the tab for viewing and editing config files."""
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)

        # Control buttons
        control_layout = QHBoxLayout()
        self.load_config_button = QPushButton("Load All Config Files from Server")
        self.load_config_button.setEnabled(False)

        self.save_config_button = QPushButton("Save Changes to Server")
        self.save_config_button.setEnabled(False)
        self.save_config_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")

        control_layout.addWidget(self.load_config_button)
        control_layout.addWidget(self.save_config_button)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Filter for config items
        filter_layout = QHBoxLayout()
        self.config_filter_input = QLineEdit()
        self.config_filter_input.setPlaceholderText("Filter items by name...")
        self.config_filter_input.textChanged.connect(self.filter_config_table)
        filter_layout.addWidget(QLabel("Filter:"))
        filter_layout.addWidget(self.config_filter_input)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Config table
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(5)
        self.config_table.setHorizontalHeaderLabels(["Type", "Item Name", "StackSize", "Category", "Source File"])
        self.config_table.setSortingEnabled(True)
        self.config_table.itemChanged.connect(self.on_config_item_changed)

        # Match the player table styling exactly - no custom CSS
        self.config_table.setAlternatingRowColors(True)
        self.config_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.config_table.setEditTriggers(QTableWidget.EditTriggers.DoubleClicked)

        header = self.config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)

        layout.addWidget(self.config_table)
        self.tabs.addTab(config_widget, "Config Editor")

        # Track changes
        self.config_changes_made = False

    def create_scheduled_messages_tab(self):
        """Creates the tab for managing scheduled global messages - SIMPLIFIED SCHEDULING."""
        messages_widget = QWidget()
        layout = QVBoxLayout(messages_widget)

        # Manual message section
        manual_layout = QFormLayout()
        manual_layout.addWidget(QLabel("Manual Global Message:"))

        manual_input_layout = QHBoxLayout()
        self.manual_message_input = QLineEdit()
        self.manual_message_input.setPlaceholderText("Enter message to send immediately...")
        self.send_manual_message_button = QPushButton("Send Global Message")
        manual_input_layout.addWidget(self.manual_message_input)
        manual_input_layout.addWidget(self.send_manual_message_button)
        manual_layout.addRow(manual_input_layout)

        layout.addLayout(manual_layout)

        # Separator
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("Scheduled Messages (Interval-based only):"))

        # Scheduled messages section
        self.scheduled_messages = []

        for i in range(5):
            message_layout = QHBoxLayout()

            # Enable checkbox
            enabled_checkbox = QCheckBox(f"Message {i+1}:")
            enabled_checkbox.stateChanged.connect(lambda state, idx=i: self.on_message_enabled_changed(idx, state))

            # Message text input
            message_input = QLineEdit()
            message_input.setPlaceholderText("Enter scheduled message...")
            message_input.textChanged.connect(lambda text, idx=i: self.on_message_text_changed(idx, text))

            # Schedule type combo - SIMPLIFIED: Only interval-based scheduling
            schedule_combo = QComboBox()
            schedule_combo.addItems([
                "Every 5 minutes", "Every 10 minutes", "Every 15 minutes", "Every 30 minutes",
                "Every 1 hour", "Every 2 hours", "Every 3 hours", "Every 6 hours", "Every 12 hours"
            ])
            schedule_combo.currentTextChanged.connect(lambda text, idx=i: self.on_schedule_changed(idx, text))

            # Delete button
            delete_button = QPushButton("Clear")
            delete_button.clicked.connect(lambda checked, idx=i: self.on_delete_message(idx))

            message_layout.addWidget(enabled_checkbox)
            message_layout.addWidget(message_input)
            message_layout.addWidget(schedule_combo)
            message_layout.addWidget(delete_button)

            layout.addLayout(message_layout)

            # Store references
            self.scheduled_messages.append({
                'enabled_checkbox': enabled_checkbox,
                'message_input': message_input,
                'schedule_combo': schedule_combo,
                'delete_button': delete_button
            })

        # Control buttons
        control_layout = QHBoxLayout()
        self.save_schedule_button = QPushButton("Save Schedule Configuration")
        self.load_schedule_button = QPushButton("Load Schedule Configuration")
        control_layout.addWidget(self.load_schedule_button)
        control_layout.addWidget(self.save_schedule_button)
        control_layout.addStretch()

        layout.addLayout(control_layout)
        layout.addStretch()

        self.tabs.addTab(messages_widget, "Scheduled Messages")

    def on_message_enabled_changed(self, index, state):
        """Called when a scheduled message is enabled/disabled."""
        enabled = state == Qt.CheckState.Checked.value
        self.log_message(f"Message {index+1} {'enabled' if enabled else 'disabled'}")

    def on_message_text_changed(self, index, text):
        """Called when message text changes."""
        pass  # We'll save when user clicks save button

    def on_schedule_changed(self, index, schedule_text):
        """Called when schedule type changes."""
        self.log_message(f"Message {index+1} schedule changed to: {schedule_text}")

    def on_delete_message(self, index):
        """Called when clear button is clicked."""
        reply = QMessageBox.question(self, "Clear Message",
                                   f"Are you sure you want to clear Message {index+1}?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Clear the message
            msg = self.scheduled_messages[index]
            msg['enabled_checkbox'].setChecked(False)
            msg['message_input'].clear()
            msg['schedule_combo'].setCurrentIndex(0)
            self.log_message(f"Message {index+1} cleared")

    def on_save_schedule_clicked(self):
        """Save scheduled messages to config file."""
        if self.worker:
            self.worker.save_scheduled_messages(self.get_scheduled_messages_data())

    def on_load_schedule_clicked(self):
        """Load scheduled messages from config file."""
        if self.worker:
            self.worker.load_scheduled_messages()

    def get_scheduled_messages_data(self):
        """Get current scheduled messages data from UI."""
        messages_data = []
        for i, msg in enumerate(self.scheduled_messages):
            data = {
                'enabled': msg['enabled_checkbox'].isChecked(),
                'text': msg['message_input'].text(),
                'schedule': msg['schedule_combo'].currentText()
            }
            messages_data.append(data)
        return messages_data

    def update_scheduled_messages_ui(self, messages_data):
        """Update UI with loaded scheduled messages data."""
        for i, data in enumerate(messages_data):
            if i < len(self.scheduled_messages):
                msg = self.scheduled_messages[i]
                msg['enabled_checkbox'].setChecked(data.get('enabled', False))
                msg['message_input'].setText(data.get('text', ''))
                schedule_text = data.get('schedule', 'Every 5 minutes')
                index = msg['schedule_combo'].findText(schedule_text)
                if index >= 0:
                    msg['schedule_combo'].setCurrentIndex(index)
                else:
                    # If old schedule format found, default to 5 minutes
                    msg['schedule_combo'].setCurrentIndex(0)

    # NEW: Player table filtering (like entity filtering)
    def filter_players_table(self):
        """Hides or shows player rows based on the content of all filter inputs."""
        filters = [f.text().lower() for f in self.player_filter_inputs]

        for row in range(self.player_table.rowCount()):
            show_row = True
            for col_index, filter_text in enumerate(filters):
                if not filter_text:
                    continue

                item = self.player_table.item(row, col_index)
                if not item or filter_text not in item.text().lower():
                    show_row = False
                    break

            self.player_table.setRowHidden(row, not show_row)

    def start_worker(self):
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)

        self.worker.logMessage.connect(self.log_message)
        self.worker.connectionStatusChanged.connect(self.update_connection_status)
        self.worker.playersUpdated.connect(self.update_player_list)
        self.worker.entitiesUpdated.connect(self.update_entities_table)
        self.worker.configDataUpdated.connect(self.update_config_table)
        self.worker.statusMessage.connect(self.show_temporary_status)
        self.worker.scheduledMessagesLoaded.connect(self.update_scheduled_messages_ui)

        self.thread.started.connect(self.worker.start_monitoring)
        self.save_button.clicked.connect(self.worker.save_server)
        self.refresh_players_button.clicked.connect(self.worker.force_player_update)
        self.load_entities_button.clicked.connect(self.on_load_entities_clicked)
        self.save_raw_gents_button.clicked.connect(self.on_save_raw_gents_clicked)
        self.load_config_button.clicked.connect(self.on_load_config_clicked)
        self.save_config_button.clicked.connect(self.on_save_config_clicked)
        self.send_manual_message_button.clicked.connect(lambda: self.worker.send_global_message(self.manual_message_input.text()))
        self.save_schedule_button.clicked.connect(self.on_save_schedule_clicked)
        self.load_schedule_button.clicked.connect(self.on_load_schedule_clicked)

        self.thread.start()
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.refresh_players_button.setEnabled(True)
        self.load_entities_button.setEnabled(True)
        self.save_raw_gents_button.setEnabled(True)
        self.load_config_button.setEnabled(True)

    def stop_worker(self):
        if self.worker:
            self.worker.stop_monitoring()
        if self.thread:
            self.thread.quit()
            self.thread.wait()

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.refresh_players_button.setEnabled(False)
        self.load_entities_button.setEnabled(False)
        self.save_raw_gents_button.setEnabled(False)
        self.load_config_button.setEnabled(False)

    def closeEvent(self, event):
        self.stop_worker()
        event.accept()

    def open_player_menu(self, position):
        selected_row = self.player_table.rowAt(position.y())
        if selected_row < 0: return

        player_id_item = self.player_table.item(selected_row, 0)
        player_name_item = self.player_table.item(selected_row, 1)
        status_item = self.player_table.item(selected_row, 2)

        if not all([player_id_item, player_name_item, status_item]):
            return

        player_id = player_id_item.text()
        player_name = player_name_item.text()
        is_online = (status_item.text() == 'Online')

        menu = QMenu()

        kick_action = menu.addAction(f"Kick '{player_name}'")
        ban_action = menu.addAction(f"Ban '{player_name}' (1h)")
        pm_action = menu.addAction(f"Send Private Message to '{player_name}'")
        menu.addSeparator()
        unban_action = menu.addAction(f"Unban Player ID: {player_id}")

        if not is_online:
            kick_action.setEnabled(False)
            pm_action.setEnabled(False)

        action = menu.exec(self.player_table.mapToGlobal(position))

        if self.worker:
            if action == kick_action:
                reason, ok = QInputDialog.getText(self, "Kick Player", f"Reason to kick {player_name}:")
                if ok: self.worker.kick_player(player_name, reason)
            elif action == ban_action:
                self.worker.ban_player(player_id)
            elif action == pm_action:
                message, ok = QInputDialog.getText(self, "Private Message", f"Message for {player_name}:")
                if ok and message: self.worker.send_private_message(player_name, message)
            elif action == unban_action:
                self.worker.unban_player(player_id)

    def on_load_entities_clicked(self):
        self.log_message("'Load/Refresh Entities' button clicked.")
        if self.worker:
            self.worker.load_entities()

    def on_save_raw_gents_clicked(self):
        self.log_message("'Save Raw Gents' button clicked.")
        if self.worker:
            self.worker.save_raw_gents_output()

    def on_load_config_clicked(self):
        self.log_message("'Load Config' button clicked.")
        if self.worker:
            self.worker.load_config_file()

    def on_save_config_clicked(self):
        self.log_message("'Save Config Changes' button clicked.")
        if self.worker and self.config_changes_made:
            reply = QMessageBox.question(self, "Save Changes",
                                       "This will backup the original file and upload your changes.\nAre you sure?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.save_config_changes(self.all_config_data)

    def on_config_item_changed(self, item):
        """Called when a config table item is edited."""
        if item.column() == 2:  # StackSize column
            try:
                new_value = int(item.text())
                if new_value <= 0:
                    raise ValueError("StackSize must be positive")

                # Find the corresponding data item
                row = item.row()
                table_to_data_map = getattr(self, '_table_to_data_map', {})

                if row in table_to_data_map:
                    data_index = table_to_data_map[row]
                    if data_index < len(self.all_config_data):
                        old_value = self.all_config_data[data_index].get('stack_size', 0)
                        self.all_config_data[data_index]['stack_size'] = new_value

                        # Mark as changed
                        self.config_changes_made = True
                        self.save_config_button.setEnabled(True)

                        # Highlight changed row with yellow background
                        for col in range(self.config_table.columnCount()):
                            cell_item = self.config_table.item(row, col)
                            if cell_item:
                                cell_item.setBackground(Qt.GlobalColor.yellow)

                        self.log_message(f"Changed {self.all_config_data[data_index]['name']} StackSize: {old_value} → {new_value}")
                    else:
                        self.log_message(f"Error: data_index {data_index} out of range for config data")
                else:
                    self.log_message(f"Error: row {row} not found in table mapping")

            except ValueError as e:
                self.log_message(f"Invalid StackSize value: {e}")
                # Revert invalid changes
                row = item.row()
                table_to_data_map = getattr(self, '_table_to_data_map', {})
                if row in table_to_data_map:
                    data_index = table_to_data_map[row]
                    if data_index < len(self.all_config_data):
                        item.setText(str(self.all_config_data[data_index].get('stack_size', 0)))
                QMessageBox.warning(self, "Invalid Value", f"StackSize must be a positive integer!\nError: {e}")

    def on_autoconnect_changed(self, state):
        """Called when autoconnect checkbox state changes."""
        enabled = state == Qt.CheckState.Checked.value
        self.save_autoconnect_setting(enabled)
        self.log_message(f"Autoconnect {'enabled' if enabled else 'disabled'}")

    def load_autoconnect_setting(self):
        """Load autoconnect setting from config file."""
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read("empyrion_helper.conf")

            autoconnect = config.getboolean('general', 'autoconnect', fallback=False)
            self.autoconnect_checkbox.setChecked(autoconnect)

        except Exception as e:
            self.log_message(f"Could not load autoconnect setting: {e}")
            self.autoconnect_checkbox.setChecked(False)

    def save_autoconnect_setting(self, enabled):
        """Save autoconnect setting to config file."""
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read("empyrion_helper.conf")

            if not config.has_section('general'):
                config.add_section('general')

            config.set('general', 'autoconnect', str(enabled).lower())

            with open("empyrion_helper.conf", 'w') as configfile:
                config.write(configfile)

            self.log_message("Autoconnect setting saved.")

        except Exception as e:
            self.log_message(f"Could not save autoconnect setting: {e}")

    @Slot(str)
    def log_message(self, message):
        self.log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    @Slot(bool, str)
    def update_connection_status(self, is_connected, message):
        status_text = "Connected" if is_connected else "Disconnected"
        self.permanent_status_label.setText(f"Status: {status_text}")
        self.log_message(f"Connection status: {message}")
        if not is_connected:
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.refresh_players_button.setEnabled(False)
            self.load_entities_button.setEnabled(False)
            self.save_raw_gents_button.setEnabled(False)
            self.load_config_button.setEnabled(False)
            self.player_table.setRowCount(0)

    @Slot(str, int)
    def show_temporary_status(self, message, timeout):
        self.statusBar.showMessage(message, timeout)

    @Slot(list)
    def update_player_list(self, players):
        """ENHANCED: Updates the player table with all known players + live data."""
        try:
            # Store all player data for filtering
            self.all_players_data = players
            
            # DEBUG: Log what we received
            self.log_message(f"Frontend received {len(players)} players for display")
            
            # Clear filters when new data arrives
            for filter_input in self.player_filter_inputs:
                filter_input.blockSignals(True)
                filter_input.clear()
                filter_input.blockSignals(False)

            self.log_message("DEBUG: Cleared filters")

            self.player_table.setSortingEnabled(False)
            self.player_table.setRowCount(0)
            self.player_table.setRowCount(len(players))
            
            self.log_message(f"DEBUG: Set table row count to {len(players)}")
            
            # DEBUG: Log first few players
            for i, player in enumerate(players[:3]):
                self.log_message(f"Player {i+1}: {player.get('name', 'NO_NAME')} - {player.get('status', 'NO_STATUS')}")
            
            self.log_message("DEBUG: Starting to populate table rows...")
            
            for row, player in enumerate(players):
                try:
                    # Steam ID (partial match search friendly)
                    steam_id = str(player.get('id', 'N/A'))
                    self.player_table.setItem(row, 0, QTableWidgetItem(steam_id))
                    
                    # Player name
                    self.player_table.setItem(row, 1, QTableWidgetItem(player.get('name', 'N/A')))
                    
                    # Status - NO COLOR CHANGE, just plain text
                    status = player.get('status', 'N/A')
                    status_item = QTableWidgetItem(status)
                    self.player_table.setItem(row, 2, status_item)
                    
                    # Faction
                    self.player_table.setItem(row, 3, QTableWidgetItem(player.get('faction', 'N/A')))
                    
                    # IP Address - show for ALL players, not just online
                    ip = player.get('ip', '')
                    self.player_table.setItem(row, 4, QTableWidgetItem(ip))
                    
                    # Playfield - show for ALL players, not just online
                    playfield = player.get('playfield', '')
                    self.player_table.setItem(row, 5, QTableWidgetItem(playfield))
                    
                    # Last Seen - format the timestamp nicely in LOCAL TIME
                    last_seen = ''
                    if status == 'Online':
                        last_seen = 'Currently Online'
                    else:
                        # Show last seen offline time converted to local timezone
                        last_offline = player.get('last_seen_offline')
                        if last_offline:
                            try:
                                from datetime import datetime, timezone
                                # Parse UTC timestamp
                                if last_offline.endswith('Z'):
                                    dt_utc = datetime.fromisoformat(last_offline[:-1]).replace(tzinfo=timezone.utc)
                                else:
                                    # Handle old format without 'Z'
                                    dt_utc = datetime.fromisoformat(last_offline).replace(tzinfo=timezone.utc)
                                
                                # Convert to local time
                                dt_local = dt_utc.astimezone()
                                last_seen = dt_local.strftime('%Y-%m-%d %H:%M')
                            except Exception as e:
                                self.log_message(f"Error parsing timestamp for {player.get('name', 'Unknown')}: {e}")
                                last_seen = 'Unknown'
                        else:
                            last_seen = 'Never seen offline'
                    
                    self.player_table.setItem(row, 6, QTableWidgetItem(last_seen))
                    
                    # DEBUG: Log every 5th player
                    if row % 5 == 0:
                        self.log_message(f"DEBUG: Added row {row}: {player.get('name', 'NO_NAME')} - IP: {ip} - Playfield: {playfield}")
                        
                except Exception as e:
                    self.log_message(f"ERROR adding row {row} (player {player.get('name', 'UNKNOWN')}): {e}")

            self.log_message("DEBUG: Finished populating table rows")

            self.player_table.setSortingEnabled(True)
            self.player_table.resizeColumnsToContents()
            
            self.log_message("DEBUG: About to apply filters...")
            
            # Apply any existing filters
            self.filter_players_table()
            
            # DEBUG: Log final table state
            visible_rows = sum(1 for row in range(self.player_table.rowCount()) 
                              if not self.player_table.isRowHidden(row))
            self.log_message(f"Player table updated: {self.player_table.rowCount()} total rows, {visible_rows} visible rows")
            
        except Exception as e:
            self.log_message(f"CRITICAL ERROR in update_player_list: {e}")
            import traceback
            self.log_message(f"Traceback: {traceback.format_exc()}")

    @Slot(list)
    def update_entities_table(self, entities):
        """Stores the full entity list and populates the table."""
        self.all_entities_data = entities

        for filter_input in self.entity_filter_inputs:
            filter_input.blockSignals(True)
            filter_input.clear()
            filter_input.blockSignals(False)

        self.entities_table.setSortingEnabled(False)
        self.entities_table.setRowCount(0)
        self.entities_table.setRowCount(len(entities))

        for row, entity in enumerate(entities):
            self.entities_table.setItem(row, 0, QTableWidgetItem(entity.get('playfield', '')))
            self.entities_table.setItem(row, 1, QTableWidgetItem(entity.get('entity_id', '')))
            self.entities_table.setItem(row, 2, QTableWidgetItem(entity.get('type', '')))
            self.entities_table.setItem(row, 3, QTableWidgetItem(entity.get('faction', '')))
            self.entities_table.setItem(row, 4, QTableWidgetItem(entity.get('name', '')))

        self.entities_table.setSortingEnabled(True)
        for row in range(len(entities)):
            self.entities_table.setRowHidden(row, False)

    @Slot(list)
    def update_config_table(self, config_items):
        """Updates the config table with parsed config data."""
        self.log_message(f"Updating config table with {len(config_items)} items")

        if not config_items:
            self.log_message("No config items received!")
            return

        # Temporarily disconnect the itemChanged signal to prevent auto-triggering
        self.config_table.itemChanged.disconnect()

        self.all_config_data = config_items
        self.config_changes_made = False
        self.save_config_button.setEnabled(False)

        # Clear filter
        self.config_filter_input.blockSignals(True)
        self.config_filter_input.clear()
        self.config_filter_input.blockSignals(False)

        # Separate templates from individual items
        templates = []
        individuals = []

        template_names = ['FoodTemplate', 'OreTemplate', 'ComponentsTemplate']

        for item in config_items:
            item_name = item.get('name', '')
            if item_name in template_names:
                templates.append(item)
            else:
                individuals.append(item)

        self.log_message(f"Found {len(templates)} templates and {len(individuals)} individual items")
        
        # DEBUG: Log what templates we found
        for template in templates:
            self.log_message(f"Template found: {template.get('name', 'UNKNOWN')}")

        # Create mapping from table row to data index
        self._table_to_data_map = {}

        # Prepare table data
        self.config_table.setSortingEnabled(False)
        self.config_table.setRowCount(0)

        current_row = 0

        # Add templates section if we have any
        if templates:
            self.log_message(f"Adding templates section with {len(templates)} templates")
            
            # Add one row for the header
            self.config_table.setRowCount(current_row + 1)

            # Section header - bold text with clear visual separation
            header_item = QTableWidgetItem("📋 TEMPLATES (affects multiple items)")
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            # Make header stand out
            font = header_item.font()
            font.setBold(True)
            header_item.setFont(font)
            self.config_table.setItem(current_row, 0, header_item)

            for col in range(1, 5):
                empty_item = QTableWidgetItem("")
                empty_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.config_table.setItem(current_row, col, empty_item)

            current_row += 1

            # Add template rows
            for template in templates:
                # Find this template in the original data
                data_index = config_items.index(template)

                self.config_table.setRowCount(current_row + 1)
                self._table_to_data_map[current_row] = data_index

                type_item = QTableWidgetItem("📋 Template")
                name_item = QTableWidgetItem(template.get('name', ''))
                stack_item = QTableWidgetItem(str(template.get('stack_size', '')))
                category_item = QTableWidgetItem(template.get('category', ''))
                source_item = QTableWidgetItem(template.get('source_file', ''))

                # Make only StackSize editable
                type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                stack_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                category_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                source_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                self.config_table.setItem(current_row, 0, type_item)
                self.config_table.setItem(current_row, 1, name_item)
                self.config_table.setItem(current_row, 2, stack_item)
                self.config_table.setItem(current_row, 3, category_item)
                self.config_table.setItem(current_row, 4, source_item)

                self.log_message(f"Added template row {current_row}: {template.get('name', '')}")
                current_row += 1

        # Add individuals section if we have any
        if individuals:
            self.log_message(f"Adding individuals section with {len(individuals)} items")
            
            # Add one row for the header
            self.config_table.setRowCount(current_row + 1)

            # Section header
            header_item = QTableWidgetItem("⚙️ INDIVIDUAL ITEMS (custom values)")
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            # Make header stand out
            font = header_item.font()
            font.setBold(True)
            header_item.setFont(font)
            self.config_table.setItem(current_row, 0, header_item)

            for col in range(1, 5):
                empty_item = QTableWidgetItem("")
                empty_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.config_table.setItem(current_row, col, empty_item)

            current_row += 1

            # Add individual item rows
            for individual in individuals:
                # Find this individual in the original data
                data_index = config_items.index(individual)

                self.config_table.setRowCount(current_row + 1)
                self._table_to_data_map[current_row] = data_index

                type_item = QTableWidgetItem("⚙️ Item")
                name_item = QTableWidgetItem(individual.get('name', ''))
                stack_item = QTableWidgetItem(str(individual.get('stack_size', '')))
                category_item = QTableWidgetItem(individual.get('category', ''))
                source_item = QTableWidgetItem(individual.get('source_file', ''))

                # Make only StackSize editable
                type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                stack_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                category_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                source_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                self.config_table.setItem(current_row, 0, type_item)
                self.config_table.setItem(current_row, 1, name_item)
                self.config_table.setItem(current_row, 2, stack_item)
                self.config_table.setItem(current_row, 3, category_item)
                self.config_table.setItem(current_row, 4, source_item)

                # DEBUG: Log every 10th individual item
                if (current_row - (len(templates) + 2)) % 10 == 0:  # Account for headers
                    self.log_message(f"Added individual row {current_row}: {individual.get('name', '')}")
                    
                current_row += 1

        self.config_table.setSortingEnabled(True)

        # Reconnect the itemChanged signal AFTER populating
        self.config_table.itemChanged.connect(self.on_config_item_changed)

        self.log_message(f"Config table updated successfully with {current_row} total rows")
        self.log_message(f"Table to data mapping: {len(self._table_to_data_map)} entries")
        
        # DEBUG: Final verification
        if templates:
            self.log_message("✅ Templates section should be visible at the top")
        if individuals:
            self.log_message("✅ Individual items section should be visible below templates")

    def filter_entities_table(self):
        """Hides or shows rows based on the content of all filter inputs."""
        filters = [f.text().lower() for f in self.entity_filter_inputs]

        for row in range(self.entities_table.rowCount()):
            show_row = True
            for col_index, filter_text in enumerate(filters):
                if not filter_text:
                    continue

                item = self.entities_table.item(row, col_index)
                if not item or filter_text not in item.text().lower():
                    show_row = False
                    break

            self.entities_table.setRowHidden(row, not show_row)

    def filter_config_table(self):
        """Filters the config table based on item name."""
        filter_text = self.config_filter_input.text().lower()

        for row in range(self.config_table.rowCount()):
            if not filter_text:
                self.config_table.setRowHidden(row, False)
            else:
                item = self.config_table.item(row, 1)  # Item name column
                if item and filter_text in item.text().lower():
                    self.config_table.setRowHidden(row, False)
                else:
                    self.config_table.setRowHidden(row, True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())