# main_app.py
import sys
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QPushButton, QTabWidget, QTextEdit, QLabel,
                               QLineEdit, QHBoxLayout, QFormLayout, QTableWidget,
                               QTableWidgetItem, QMenu, QInputDialog, QHeaderView,
                               QComboBox, QStatusBar, QMessageBox)
from PySide6.QtCore import QThread, Slot, Qt
from backend import Worker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Empyrion Server Helper")
        self.setGeometry(100, 100, 900, 700)

        self.thread = None
        self.worker = None
        self.all_entities_data = []
        self.all_config_data = []

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_dashboard_tab()
        self.create_entities_tab()
        self.create_config_editor_tab()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.permanent_status_label = QLabel("Status: Not Connected")
        self.statusBar.addPermanentWidget(self.permanent_status_label)

    def create_dashboard_tab(self):
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)

        # --- Connection Controls ---
        control_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect and Start Monitoring")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        control_layout.addWidget(self.connect_button)
        control_layout.addWidget(self.disconnect_button)
        control_layout.addStretch()

        # --- Player Table ---
        player_list_layout = QVBoxLayout()

        player_header_layout = QHBoxLayout()
        player_header_layout.addWidget(QLabel("Players (Online & Offline):"))
        player_header_layout.addStretch()
        self.refresh_players_button = QPushButton("Refresh")
        self.refresh_players_button.setEnabled(False)
        player_header_layout.addWidget(self.refresh_players_button)
        player_list_layout.addLayout(player_header_layout)

        self.player_table = QTableWidget()
        self.player_table.setColumnCount(6)
        self.player_table.setHorizontalHeaderLabels(["ID", "Name", "Status", "Faction", "IP Address", "Playfield"])
        self.player_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.player_table.setEditTriggers(QTableWidget.EditTriggers.NoEditTriggers)
        self.player_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.player_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.player_table.customContextMenuRequested.connect(self.open_player_menu)
        player_list_layout.addWidget(self.player_table)

        # --- Server Actions ---
        actions_layout = QFormLayout()
        self.message_input = QLineEdit()
        self.send_message_button = QPushButton("Send Global Message")
        self.save_button = QPushButton("Save Server")
        actions_layout.addRow("Message:", self.message_input)
        actions_layout.addRow(self.send_message_button)
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

        self.thread.started.connect(self.worker.start_monitoring)
        self.send_message_button.clicked.connect(lambda: self.worker.send_global_message(self.message_input.text()))
        self.save_button.clicked.connect(self.worker.save_server)
        self.refresh_players_button.clicked.connect(self.worker.force_player_update)
        self.load_entities_button.clicked.connect(self.on_load_entities_clicked)
        self.save_raw_gents_button.clicked.connect(self.on_save_raw_gents_clicked)
        self.load_config_button.clicked.connect(self.on_load_config_clicked)
        self.save_config_button.clicked.connect(self.on_save_config_clicked)

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
        """Updates the player table with data from the 'plys' command."""
        self.player_table.setSortingEnabled(False)
        self.player_table.setRowCount(0)
        self.player_table.setRowCount(len(players))
        for row, player in enumerate(players):
            self.player_table.setItem(row, 0, QTableWidgetItem(str(player.get('id', 'N/A'))))
            self.player_table.setItem(row, 1, QTableWidgetItem(player.get('name', 'N/A')))
            self.player_table.setItem(row, 2, QTableWidgetItem(player.get('status', 'N/A')))
            self.player_table.setItem(row, 3, QTableWidgetItem(player.get('faction', 'N/A')))
            self.player_table.setItem(row, 4, QTableWidgetItem(player.get('ip', '')))
            self.player_table.setItem(row, 5, QTableWidgetItem(player.get('playfield', '')))

        self.player_table.setSortingEnabled(True)
        self.player_table.resizeColumnsToContents()

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

        # Create mapping from table row to data index
        self._table_to_data_map = {}

        # Prepare table data
        self.config_table.setSortingEnabled(False)
        self.config_table.setRowCount(0)

        current_row = 0

        # Add templates section if we have any
        if templates:
            # Add one row for the header
            self.config_table.setRowCount(current_row + 1)

            # Section header - no special colors, just bold text
            header_item = QTableWidgetItem("📋 TEMPLATES (affects multiple items)")
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
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

                current_row += 1

        # Add individuals section if we have any
        if individuals:
            # Add one row for the header
            self.config_table.setRowCount(current_row + 1)

            # Section header - no special colors, just normal
            header_item = QTableWidgetItem("⚙️ INDIVIDUAL ITEMS (custom values)")
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
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

                current_row += 1

        self.config_table.setSortingEnabled(True)

        # Reconnect the itemChanged signal AFTER populating
        self.config_table.itemChanged.connect(self.on_config_item_changed)

        self.log_message(f"Config table updated successfully with {current_row} total rows")
        self.log_message(f"Table to data mapping: {len(self._table_to_data_map)} entries")

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
