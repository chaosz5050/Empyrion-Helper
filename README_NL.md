# Empyrion Server Helper

Een uitgebreide beheer tool voor Empyrion: Galactic Survival dedicated servers. Monitor spelers, beheer entiteiten en bewerk game configuraties in real-time via een intuïtieve GUI interface.

![Empyrion Server Helper](https://img.shields.io/badge/Platform-Linux-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![Version](https://img.shields.io/badge/Version-0.2.0--alpha-red)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-orange)

## Functionaliteiten

### 🎮 Speler Beheer
- **Real-time speler monitoring** - Bekijk online/offline spelers met live updates
- **Speler acties** - Kick, ban/unban, stuur privé berichten
- **Globale berichten** - Verstuur berichten naar alle spelers
- **Speler details** - Steam ID, factie, IP adres, huidige playfield

### 🏗️ Entiteit Beheer
- **Entiteit ontdekking** - Bekijk alle structuren, voertuigen en POI's over alle playfields
- **Geavanceerd filteren** - Filter op playfield, type, factie of naam
- **Entiteit details** - ID, type, factie eigendom, locatie
- **Ruwe data export** - Sla complete entiteit lijsten op voor analyse

### ⚙️ Configuratie Editor
- **Live config bewerken** - Wijzig ItemsConfig.ecf en andere ECF bestanden
- **Template beheer** - Bewerk templates die meerdere items beïnvloeden (FoodTemplate, OreTemplate, etc.)
- **Individuele item bewerking** - Pas specifieke item stack groottes aan
- **Veilig backup systeem** - Automatische backups met origineel behoud
- **Real-time updates** - Wijzigingen gelden direct op de live server

### 📅 Geplande Berichten
- **Geautomatiseerde aankondigingen** - Plan tot 5 terugkerende globale berichten
- **Flexibele planning** - Stel intervallen in (minuten/uren) of dagelijks op specifieke tijden
- **Eenvoudig beheer** - Schakel berichten in/uit met eenvoudige checkboxes
- **Handmatige berichten** - Verstuur directe globale berichten wanneer nodig
- **Config bestand opslag** - Berichten opgeslagen in configuratie voor eenvoudige bewerking

### 🛡️ Veiligheids Functies
- **Slim backup systeem** - Creëert `.org` (origineel) en `.bak` (vorige) bestanden
- **FTP beveiliging** - Versleutelde FTP verbindingen met authenticatie
- **Fout afhandeling** - Uitgebreide logging en fout herstel
- **Wijziging tracking** - Visuele indicatoren voor gewijzigde items

## Installatie

### Vereisten
- Python 3.8 of hoger
- PySide6 (Qt for Python)
- Toegang tot je Empyrion server's telnet/RCON poort
- FTP toegang tot je server's configuratie directory

### Setup
1. Clone deze repository:
   ```bash
   git clone https://github.com/yourusername/empyrion-server-helper.git
   cd empyrion-server-helper
   ```

2. Creëer en activeer een virtual environment:
   ```bash
   # Creëer virtual environment
   python3 -m venv venv
   
   # Activeer virtual environment
   # Voor bash/zsh:
   source venv/bin/activate
   
   # Voor fish shell:
   source venv/bin/activate.fish
   ```

3. Installeer dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Creëer je configuratie bestand (zie Configuratie sectie hieronder)

5. Start de applicatie:
   ```bash
   python main_app.py
   ```

## Configuratie

Creëer een bestand genaamd `empyrion_helper.conf` in de project directory met je server details:

```ini
[server]
host = jouw.server.ip.adres
telnet_port = 30004
telnet_password = jouw_telnet_wachtwoord

[monitoring]
update_interval = 30
log_file = empyrion_helper.log

[ftp]
host = jouw.server.ip.adres:21
user = jouw_ftp_gebruikersnaam
password = jouw_ftp_wachtwoord
remote_log_path = /pad/naar/empyrion/Content/Scenarios/JouwScenario/Content/Configuration
```

### Configuratie Parameters

| Parameter | Beschrijving | Voorbeeld |
|-----------|--------------|-----------|
| `host` | Server IP adres | `192.168.1.100` |
| `telnet_port` | RCON/Telnet poort | `30004` (standaard) |
| `telnet_password` | RCON wachtwoord | `jouw_wachtwoord` |
| `update_interval` | Speler refresh interval (seconden) | `30` |
| `ftp.host` | FTP server met optionele poort | `192.168.1.100:21` |
| `ftp.user` | FTP gebruikersnaam | `empyrion` |
| `ftp.password` | FTP wachtwoord | `jouw_ftp_wachtwoord` |
| `remote_log_path` | Pad naar configuratie bestanden | `/ServerData/Scenarios/.../Configuration` |

## Gebruik

### Dashboard Tab
1. **Verbinden** - Klik "Connect" om server verbinding te maken
2. **Speler Beheer** - Rechts-klik spelers voor acties (kick, ban, bericht)
3. **Server Acties** - Sla server status op
4. **Monitoring** - Bekijk real-time speler status en activiteit
5. **Autoconnect** - Schakel automatische verbinding bij opstarten in

### Entiteiten Tab
1. **Laad Entiteiten** - Klik "Load/Refresh Entities" om alle server entiteiten te scannen
2. **Filteren** - Gebruik kolom filters om specifieke structuren of voertuigen te vinden
3. **Export Data** - Sla ruwe entiteit data op voor externe analyse

### Config Editor Tab
1. **Laad Configs** - Klik "Load All Config Files from Server"
2. **Bewerk Templates** - Wijzig templates om meerdere items te beïnvloeden (bijv. FoodTemplate wijzigt alle voedsel stack groottes)
3. **Bewerk Individuele Items** - Dubbelklik StackSize waarden om specifieke items te wijzigen
4. **Sla Wijzigingen Op** - Klik "Save Changes to Server" om wijzigingen toe te passen
5. **Backup Veiligheid** - Originele bestanden behouden als `.org`, vorige versies als `.bak`

### Geplande Berichten Tab
1. **Handmatige Berichten** - Verstuur directe globale berichten naar alle spelers
2. **Plan Berichten** - Configureer tot 5 automatische terugkerende berichten
3. **Stel Intervallen In** - Kies uit vooraf ingestelde intervallen (5 min tot 12 uur) of dagelijks op specifieke tijden
4. **In-/Uitschakelen** - Gebruik checkboxes om te bepalen welke berichten actief zijn
5. **Opslaan/Laden** - Bewaar geplande berichten in configuratie bestand voor persistentie

## Hoe Het Werkt

### Architectuur
- **Frontend**: PySide6 (Qt) GUI met tabbed interface
- **Backend**: Multi-threaded worker voor server communicatie
- **Communicatie**: RCON/Telnet voor commando's, FTP voor bestand operaties
- **Data Opslag**: Lokale SQLite database voor caching

### Server Communicatie
1. **RCON Verbinding** - Zet telnet verbinding op voor real-time commando's
2. **Commando Uitvoering** - Verstuurt `plys` (spelers), `gents` (entiteiten), en admin commando's
3. **Response Parsing** - Verwerkt server responses met regex pattern matching
4. **FTP Operaties** - Download/upload configuratie bestanden veilig

### Configuratie Bewerkings Proces
1. **Download** - Haalt alle `.ecf` bestanden van server via FTP
2. **Parse** - Extraheert items met StackSize eigenschappen met regex
3. **Categoriseer** - Scheidt templates van individuele items
4. **Bewerk** - Biedt GUI voor het wijzigen van waarden
5. **Backup** - Creëert veiligheids backups (`.org` voor origineel, `.bak` voor vorige)
6. **Upload** - Past wijzigingen toe op live server configuratie

### Backup Strategie
- **Eerste Opslag**: `bestand.ecf` → `bestand.ecf.org` (permanent origineel)
- **Volgende Opslagen**: `bestand.ecf` → `bestand.ecf.bak` (vorige versie)
- **Resultaat**: Altijd origineel en vorige versie voor herstel

## Bestand Structuur

```
empyrion-server-helper/
├── main_app.py              # Hoofd GUI applicatie
├── backend.py               # Server communicatie logica
├── requirements.txt         # Python dependencies
├── empyrion_helper.conf     # Configuratie bestand (creëer dit)
├── player_history.db        # Lokale database (auto-gecreëerd)
├── gents_raw_output.txt     # Entiteit data export (optioneel)
└── README.md                # Dit bestand
```

## Vereisten

### Systeem Vereisten
- **OS**: Linux distributies
- **Python**: 3.8 of hoger
- **RAM**: 512MB minimum
- **Netwerk**: Toegang tot Empyrion server poorten

### Server Vereisten
- **Empyrion**: Dedicated server met RCON ingeschakeld
- **RCON Poort**: Meestal 30004 (configureerbaar)
- **FTP Toegang**: Tot server configuratie directory
- **Permissies**: Lees/schrijf toegang tot ECF bestanden

## Probleemoplossing

### Verbindings Problemen
- **Controleer server IP en poorten** - Verifieer RCON en FTP instellingen
- **Firewall regels** - Zorg dat poorten open zijn
- **Credentials** - Verifieer RCON en FTP wachtwoorden

### Configuratie Problemen
- **Bestand paden** - Controleer dat `remote_log_path` naar juiste directory wijst
- **Permissies** - Zorg dat FTP gebruiker ECF bestanden kan lezen/schrijven
- **Backups** - Controleer server schijfruimte voor backup bestanden

### Prestaties
- **Update interval** - Verhoog `update_interval` voor langzamere servers
- **Grote servers** - Entiteit laden kan tijd kosten met veel structuren

## Community & Ondersteuning

### 🎮 Live Test Server
Wil je deze tool in actie zien? Doe mee met onze **Space Cowboys RE2B1.12** server in de EU regio:

**Server Details:**
- **Naam**: Space Cowboys RE2B1.12 [NoVol|NoCPU|EACOff|PvE][CHZ]
- **Regio**: Europa
- **Scenario**: Space Cowboys Reforged Eden 2 Beta 1.12
- **Features**: Geen Volume limieten, Geen CPU limieten, EAC Uit, PvE gericht
- **Platform**: Linux-gehost (bewijst cross-platform compatibiliteit)

Deze server draait de exacte configuratie beheerd door Empyrion Server Helper, wat real-world gebruik van de tool's config bewerkings mogelijkheden demonstreert.

### 💬 Discord Community
Doe mee met onze Discord voor ondersteuning, discussies en server community:

**🔗 [Discord Server](https://discord.gg/WFtZRWVB)**

Krijg hulp met:
- Tool setup en configuratie
- Server administratie tips
- Bug reports en feature requests
- Algemeen Empyrion server beheer

## Bijdragen

1. Fork de repository
2. Creëer een feature branch (`git checkout -b feature/geweldige-feature`)
3. Commit je wijzigingen (`git commit -m 'Voeg geweldige feature toe'`)
4. Push naar de branch (`git push origin feature/geweldige-feature`)
5. Open een Pull Request

## Licentie

Dit project is gelicenseerd onder de **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

### Wat dit betekent:
- ✅ **Je kunt vrijelijk gebruiken** deze software voor persoonlijke en niet-commerciële doeleinden
- ✅ **Je kunt wijzigen** en herverspreiden van de code
- ✅ **Je kunt delen** met anderen
- 🚫 **Je kunt niet verkopen** deze software of gebruiken voor commerciële doeleinden
- 🔄 **Alle wijzigingen** moeten gedeeld worden onder dezelfde licentie
- 👤 **Je moet credit geven** aan de originele auteur

**Volledige licentie tekst**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

### Commercieel Gebruik
Als je geïnteresseerd bent in commercieel gebruik of licenties, neem dan contact op met de onderhouders via onze Discord community.

## Dankbetuigingen

- **Eleon Game Studios** - Voor het creëren van Empyrion: Galactic Survival
- **Community** - Voor server administratie inzichten en testen
- **Bijdragers** - Dank aan iedereen die heeft geholpen deze tool te verbeteren

## Disclaimer

Deze tool wijzigt live server configuratie bestanden. Altijd:
- **Test eerst op ontwikkel servers**
- **Houd regelmatige backups**
- **Monitor server stabiliteit na wijzigingen**
- **Begrijp de impact van je wijzigingen**

Gebruik op eigen risico. De auteurs zijn niet verantwoordelijk voor server problemen of data verlies.

---

**Veel plezier met server administratie!** 🚀

Voor ondersteuning, open een issue op GitHub of neem contact op met de onderhouders.