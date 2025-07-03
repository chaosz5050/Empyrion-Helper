# Empyrion Server Helper

A comprehensive administration tool for Empyrion: Galactic Survival dedicated servers. Monitor players, manage entities, and edit game configurations in real-time through an intuitive GUI interface.

![Empyrion Server Helper](https://img.shields.io/badge/Platform-Linux-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![Version](https://img.shields.io/badge/Version-0.2.0--alpha-red)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-orange)

## Features

### 🎮 Player Management
- **Real-time player monitoring** - View online/offline players with live updates
- **Player actions** - Kick, ban/unban, send private messages
- **Global messaging** - Broadcast messages to all players
- **Player details** - Steam ID, faction, IP address, current playfield

### 🏗️ Entity Management
- **Entity discovery** - Browse all structures, vehicles, and POIs across playfields
- **Advanced filtering** - Filter by playfield, type, faction, or name
- **Entity details** - ID, type, faction ownership, location
- **Raw data export** - Save complete entity lists for analysis

### ⚙️ Configuration Editor
- **Live config editing** - Modify ItemsConfig.ecf and other ECF files
- **Template management** - Edit templates that affect multiple items (FoodTemplate, OreTemplate, etc.)
- **Individual item editing** - Customize specific item stack sizes
- **Safe backup system** - Automatic backups with original preservation
- **Real-time updates** - Changes apply immediately to the live server

### 📅 Scheduled Messages
- **Automated announcements** - Schedule up to 5 recurring global messages
- **Flexible scheduling** - Set intervals (minutes/hours) or daily at specific times
- **Easy management** - Enable/disable messages with simple checkboxes
- **Manual messaging** - Send immediate global messages when needed
- **Config file storage** - Messages saved in configuration for easy editing

### 🛡️ Safety Features
- **Smart backup system** - Creates `.org` (original) and `.bak` (previous) files
- **FTP security** - Encrypted FTP connections with authentication
- **Error handling** - Comprehensive logging and error recovery
- **Change tracking** - Visual indicators for modified items

## Installation

### Prerequisites
- Python 3.8 or higher
- PySide6 (Qt for Python)
- Access to your Empyrion server's telnet/RCON port
- FTP access to your server's configuration directory

### Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/empyrion-server-helper.git
   cd empyrion-server-helper
   ```

2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   # For bash/zsh:
   source venv/bin/activate
   
   # For fish shell:
   source venv/bin/activate.fish
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your configuration file (see Configuration section below)

5. Run the application:
   ```bash
   python main_app.py
   ```

## Configuration

Create a file named `empyrion_helper.conf` in the project directory with your server details:

```ini
[server]
host = your.server.ip.address
telnet_port = 30004
telnet_password = your_telnet_password

[monitoring]
update_interval = 30
log_file = empyrion_helper.log

[ftp]
host = your.server.ip.address:21
user = your_ftp_username
password = your_ftp_password
remote_log_path = /path/to/empyrion/Content/Scenarios/YourScenario/Content/Configuration
```

### Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `host` | Server IP address | `192.168.1.100` |
| `telnet_port` | RCON/Telnet port | `30004` (default) |
| `telnet_password` | RCON password | `your_password` |
| `update_interval` | Player refresh interval (seconds) | `30` |
| `ftp.host` | FTP server with optional port | `192.168.1.100:21` |
| `ftp.user` | FTP username | `empyrion` |
| `ftp.password` | FTP password | `your_ftp_password` |
| `remote_log_path` | Path to configuration files | `/ServerData/Scenarios/.../Configuration` |

## Usage

### Dashboard Tab
1. **Connect** - Click "Connect and Start Monitoring" to establish server connection
2. **Player Management** - Right-click players for actions (kick, ban, message)
3. **Server Actions** - Send global messages or save server state
4. **Monitoring** - View real-time player status and activity

### Entities Tab
1. **Load Entities** - Click "Load/Refresh Entities" to scan all server entities
2. **Filtering** - Use column filters to find specific structures or vehicles
3. **Export Data** - Save raw entity data for external analysis

### Config Editor Tab
1. **Load Configs** - Click "Load All Config Files from Server" 
2. **Edit Templates** - Modify templates to affect multiple items (e.g., FoodTemplate changes all food stack sizes)
3. **Edit Individual Items** - Double-click StackSize values to modify specific items
4. **Save Changes** - Click "Save Changes to Server" to apply modifications
5. **Backup Safety** - Original files are preserved as `.org`, previous versions as `.bak`

### Scheduled Messages Tab
1. **Manual Messages** - Send immediate global messages to all players
2. **Schedule Messages** - Configure up to 5 automatic recurring messages
3. **Set Intervals** - Choose from preset intervals (5 min to 12 hours) or daily at specific times
4. **Enable/Disable** - Use checkboxes to control which messages are active
5. **Save/Load** - Store scheduled messages in configuration file for persistence

## How It Works

### Architecture
- **Frontend**: PySide6 (Qt) GUI with tabbed interface
- **Backend**: Multi-threaded worker for server communication
- **Communication**: RCON/Telnet for commands, FTP for file operations
- **Data Storage**: Local SQLite database for caching

### Server Communication
1. **RCON Connection** - Establishes telnet connection for real-time commands
2. **Command Execution** - Sends `plys` (players), `gents` (entities), and admin commands
3. **Response Parsing** - Processes server responses with regex pattern matching
4. **FTP Operations** - Downloads/uploads configuration files securely

### Configuration Editing Process
1. **Download** - Retrieves all `.ecf` files from server via FTP
2. **Parse** - Extracts items with StackSize properties using regex
3. **Categorize** - Separates templates from individual items
4. **Edit** - Provides GUI for modifying values
5. **Backup** - Creates safety backups (`.org` for original, `.bak` for previous)
6. **Upload** - Applies changes to live server configuration

### Backup Strategy
- **First Save**: `file.ecf` → `file.ecf.org` (permanent original)
- **Subsequent Saves**: `file.ecf` → `file.ecf.bak` (previous version)
- **Result**: Always have original and previous version for recovery

## File Structure

```
empyrion-server-helper/
├── main_app.py              # Main GUI application
├── backend.py               # Server communication logic
├── requirements.txt         # Python dependencies
├── empyrion_helper.conf     # Configuration file (create this)
├── player_history.db        # Local database (auto-created)
├── gents_raw_output.txt     # Entity data export (optional)
└── README.md                # This file
```

## Requirements

### System Requirements
- **OS**: Linux distributions
- **Python**: 3.8 or higher
- **RAM**: 512MB minimum
- **Network**: Access to Empyrion server ports

### Server Requirements
- **Empyrion**: Dedicated server with RCON enabled
- **RCON Port**: Usually 30004 (configurable)
- **FTP Access**: To server configuration directory
- **Permissions**: Read/write access to ECF files

## Troubleshooting

### Connection Issues
- **Check server IP and ports** - Verify RCON and FTP settings
- **Firewall rules** - Ensure ports are open
- **Credentials** - Verify RCON and FTP passwords

### Configuration Problems
- **File paths** - Check `remote_log_path` points to correct directory
- **Permissions** - Ensure FTP user can read/write ECF files
- **Backups** - Check server disk space for backup files

### Performance
- **Update interval** - Increase `update_interval` for slower servers
- **Large servers** - Entity loading may take time with many structures

## Community & Support

### 🎮 Live Test Server
Want to see this tool in action? Join our **Space Cowboys RE2B1.12** server running in the EU region:

**Server Details:**
- **Name**: Space Cowboys RE2B1.12 [NoVol|NoCPU|EACOff|PvE][CHZ]
- **Region**: Europe
- **Scenario**: Space Cowboys Reforged Eden 2 Beta 1.12
- **Features**: No Volume limits, No CPU limits, EAC Off, PvE focused
- **Platform**: Linux-hosted (proving cross-platform compatibility)

This server runs the exact configuration managed by Empyrion Server Helper, demonstrating real-world usage of the tool's config editing capabilities.

### 💬 Discord Community
Join our Discord for support, discussions, and server community:

**🔗 [Discord Server](https://discord.gg/WFtZRWVB)**

Get help with:
- Tool setup and configuration
- Server administration tips
- Bug reports and feature requests
- General Empyrion server management

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

### What this means:
- ✅ **You can freely use** this software for personal and non-commercial purposes
- ✅ **You can modify** and redistribute the code
- ✅ **You can share** it with others
- 🚫 **You cannot sell** this software or use it for commercial purposes
- 🔄 **Any modifications** must be shared under the same license
- 👤 **You must give credit** to the original author

**Full license text**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

### Commercial Use
If you're interested in commercial use or licensing, please contact the maintainers through our Discord community.

## Acknowledgments

- **Eleon Game Studios** - For creating Empyrion: Galactic Survival
- **Community** - For server administration insights and testing
- **Contributors** - Thanks to everyone who helped improve this tool

## Disclaimer

This tool modifies live server configuration files. Always:
- **Test on development servers first**
- **Keep regular backups**
- **Monitor server stability after changes**
- **Understand the impact of your modifications**

Use at your own risk. The authors are not responsible for server issues or data loss.

---

**Happy server administration!** 🚀

For support, please open an issue on GitHub or contact the maintainers.
