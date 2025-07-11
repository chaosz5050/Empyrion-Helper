# Changelog

All notable changes to Empyrion Server Helper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.7-alpha] - 2025-07-12

### Added
- **Custom Player Status Messages** - Complete automated welcome/goodbye message system
  - Customizable welcome message when players join the server
  - Customizable goodbye message when players leave the server
  - Template support with `<playername>` placeholder for dynamic player names
  - Test functionality with "Test Welcome" and "Test Goodbye" buttons
  - Messages saved to configuration file for persistence across app restarts
  - Auto-loading of custom messages when app starts
  - Visual instructions for using the `<playername>` placeholder
- **Improved Update Frequency** - Reduced default player update interval from 30 to 20 seconds
  - Better responsiveness for player status changes
  - Faster detection of players joining/leaving
  - Still configurable via `update_interval` setting in config file

### Changed
- **Player Status Detection** - Enhanced real-time player monitoring
  - Welcome messages sent automatically when players come online
  - Goodbye messages sent automatically when players go offline
  - Smart detection prevents duplicate messages for status changes
- **UI Layout** - Extended Scheduled Messages tab
  - Added dedicated section for custom player status messages
  - Clear separation between scheduled messages and player status messages
  - Improved visual hierarchy with styled headers and instructions

### Technical
- **Message Template System** - Backend support for dynamic message generation
  - Secure placeholder replacement for player names
  - Integration with existing player tracking database
  - Thread-safe message delivery through Qt signals/slots
- **Configuration Management** - Extended config file support
  - New `[messages]` section for custom message templates
  - Backward compatibility with existing configuration files
  - Auto-creation of missing config sections

### Fixed
- **Emoji Character Issues** - Removed all emoji characters from code
  - Fixed syntax errors caused by Unicode emoji in source files
  - Replaced emoji icons with plain text labels (e.g., "TEMPLATES", "INDIVIDUAL ITEMS")
  - Improved cross-platform compatibility

## [0.2.6-alpha] - 2025-07-09
- Added a 'Last seen' column
- Player data is now saved to a local database and compared to live info on start
- The player tab now has filters
- fixed some minor bugs

## [Unreleased]

## [0.2.0-alpha] - 2025-07-04

### Added
- **Scheduled Messages Tab** - Complete automated messaging system
  - Schedule up to 5 recurring global messages
  - Flexible scheduling options (every X minutes/hours or daily at specific times)
  - Preset intervals from 5 minutes to 12 hours
  - Daily scheduling at common times (08:00, 12:00, 18:00, 20:00)
  - Enable/disable individual messages with checkboxes
  - Save/load scheduled messages to/from configuration file
  - Manual global messaging functionality (moved from Dashboard)
- **Autoconnect Feature** - Automatic server connection on startup
  - Autoconnect checkbox on Dashboard tab
  - Setting saved to configuration file
  - Auto-connects when app starts if enabled
- **Enhanced Global Messaging** - Improved message delivery
  - Support for BB code formatting (bold, underline, URLs)
  - Proper handling of multi-word messages
  - Special character support for Discord links and formatting

### Changed
- **Dashboard Tab** - Streamlined interface
  - Renamed "Connect and Start Monitoring" button to "Connect"
  - Moved global messaging functionality to Scheduled Messages tab
  - Added autoconnect checkbox for convenience

### Fixed
- **Message Delivery** - Resolved message truncation issues
  - Fixed command formatting for Empyrion RCON
  - Proper quote handling for messages with spaces
  - Improved special character escaping

### Technical
- **Configuration Management** - Enhanced config file handling
  - Added `[general]` section for app-wide settings
  - Added `[scheduled_messages]` section for message automation
  - Improved config file parsing and writing
- **Scheduler System** - Background message scheduling
  - Minute-based timer for scheduled message checking
  - Smart timing to prevent duplicate message sends
  - Amsterdam timezone support (UTC+1)

## [0.1.0-alpha] - 2025-07-03

### Added
- **Initial Release** - Core server administration functionality
- **Player Management** 
  - Real-time player monitoring with online/offline status
  - Player actions (kick, ban/unban, private messages)
  - Player details (Steam ID, faction, IP, playfield)
- **Entity Management**
  - Entity discovery across all playfields
  - Advanced filtering by playfield, type, faction, name
  - Raw entity data export functionality
- **Configuration Editor**
  - Live ECF file editing with FTP download/upload
  - Template management (FoodTemplate, OreTemplate, ComponentsTemplate)
  - Individual item StackSize editing
  - Smart backup system (.org for original, .bak for previous)
- **Server Communication**
  - RCON/Telnet integration for real-time commands
  - Secure FTP file operations
  - Multi-threaded backend for responsive GUI
- **User Interface**
  - Professional dark theme GUI with PySide6/Qt
  - Tabbed interface (Dashboard, Entities, Config Editor)
  - Real-time logging and status updates
  - Alternating row colors and modern styling

### Technical
- **Architecture** - Clean separation of GUI and backend logic
- **Database** - SQLite for local data caching
- **Configuration** - INI-based configuration file system
- **Platform** - Linux-focused development and testing
- **License** - Creative Commons BY-NC-SA 4.0 (non-commercial)

---

## Version Numbering Scheme

**Alpha Phase (0.x.y-alpha):**
- **0.x.0** - Major feature additions
- **0.x.y** - Minor features and bug fixes
- **-alpha** - Pre-release software, core features still in development

**Beta Phase (0.x.y-beta):** *Future*
- Feature-complete for core functionality
- Focus on bug fixes, performance, and stability

**Release Phase (1.x.y):** *Future*
- Stable, production-ready software
- Semantic versioning for public releases