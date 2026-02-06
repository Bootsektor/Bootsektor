# Web Scanner

Ein automatischer Web-Scanner mit TOR/VPN Unterstützung, der periodisch Webseiten durchsucht, relevante Inhalte filtert, Zusammenfassungs-Bilder erstellt und Benachrichtigungen über Telegram sendet.

## Features

- 🔍 **Automatisches Web-Scraping**: Periodische Überwachung konfigurierter Webseiten
- 🛡️ **Anonymität**: TOR und VPN Unterstützung für privates Browsing
- 🧠 **Lernalgorithmus**: Maschinelles Lernen zur Verbesserung der Relevanzfilterung
- 🖼️ **Bild-Zusammenfassungen**: Automatische Erstellung von Übersichtsbildern mit Headline und Featured Image
- 📱 **Telegram-Benachrichtigungen**: Direkte Benachrichtigungen bei interessanten Beiträgen
- ⚙️ **Konfigurierbar**: Anpassbare Filter, Keywords und Scan-Intervalle
- 📊 **Statistiken**: Detaillierte Statistiken über Scan-Ergebnisse und Nutzerpräferenzen

## Installation

### 1. System-Voraussetzungen

- Python 3.8 oder höher
- TOR (für anonymes Browsing)
- ImageMagick (für Bildverarbeitung)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip tor imagemagick

# CentOS/RHEL
sudo yum install python3 python3-pip tor ImageMagick

# Arch Linux
sudo pacman -S python python-pip tor imagemagick
```

### 2. Installation

```bash
# Klonen oder Download des Projekts
cd web_scanner

# Installationsskript ausführen
chmod +x install.sh
./install.sh
```

### 3. Konfiguration

Bearbeiten Sie `config/config.json`:

```json
{
  "scan_interval": 3600,
  "websites": [
    {
      "url": "https://beispiel-website.com",
      "name": "Beispiel Website",
      "selectors": {
        "articles": "article",
        "title": "h1, h2, .title",
        "content": ".content, p",
        "image": "img",
        "link": "a"
      },
      "enabled": true
    }
  ],
  "content_filter": {
    "keywords": ["wichtig", "nachricht", "update"],
    "blacklist": ["spam", "werbung"],
    "min_content_length": 100
  },
  "telegram": {
    "enabled": true,
    "bot_token": "IHR_BOT_TOKEN",
    "chat_id": "IHR_CHAT_ID"
  }
}
```

### 4. Telegram Bot Setup

1. Erstellen Sie einen Telegram Bot via @BotFather
2. Erhalten Sie den Bot Token
3. Finden Sie Ihre Chat ID (senden Sie eine Nachricht an @userinfobot)
4. Tragen Sie die Daten in die Konfiguration ein

## Nutzung

### Starten

```bash
./start.sh
```

### Status prüfen

```bash
./status.sh
```

### Stoppen

```bash
./stop.sh
```

### Manuelles Scannen

```bash
# Im web_scanner Verzeichnis
source venv/bin/activate
python src/main.py
```

## Konfiguration

### Webseiten hinzufügen

```json
{
  "websites": [
    {
      "url": "https://news-site.com",
      "name": "News Site",
      "selectors": {
        "articles": "article.post",
        "title": ".post-title",
        "content": ".post-content",
        "image": ".featured-image img",
        "link": ".read-more"
      },
      "enabled": true
    }
  ]
}
```

### Content Filter

```json
{
  "content_filter": {
    "keywords": ["technologie", "künstliche intelligenz", "programmierung"],
    "blacklist": ["werbung", "gesponsert", "clickbait"],
    "min_content_length": 200,
    "learning_enabled": true
  }
}
```

### TOR/VPN Einstellungen

```json
{
  "tor": {
    "enabled": true,
    "port": 9050,
    "control_port": 9051,
    "password": "IHR_TOR_PASSWORD"
  },
  "vpn": {
    "enabled": false,
    "protocol": "openvpn",
    "config_file": "/path/to/vpn.conf"
  }
}
```

## Architektur

### Komponenten

- **main.py**: Hauptanwendung und Koordination
- **web_scraper.py**: Web-Scraping mit TOR-Unterstützung
- **content_filter.py**: Inhaltsfilterung und Relevanzprüfung
- **image_processor.py**: Bildverarbeitung und Zusammenfassungen
- **learning_database.py**: Lernalgorithmus und Nutzerpräferenzen
- **telegram_notifier.py**: Telegram-Benachrichtigungen
- **tor_manager.py**: TOR-Verbindung und IP-Rotation
- **scheduler.py**: Periodische Ausführung

### Datenbank

Die Anwendung verwendet SQLite für:
- Artikel-Metadaten
- Nutzer-Feedback
- Lern-Daten
- Performance-Metriken

## Lernalgorithmus

Der Scanner lernt aus Ihrem Feedback:

1. **Initial**: Basierend auf konfigurierten Keywords
2. **Training**: Aus Nutzer-Feedback (👍/👎)
3. **Vorhersage**: Maschinelles Lernen zur Relevanzbewertung
4. **Optimierung**: Kontinuierliche Verbesserung der Filter

## Sicherheit

- **Anonymität**: TOR/VPN Unterstützung
- **Keine Logs**: Keine Speicherung von sensiblen Daten
- **Konfiguration**: Passwörter und Tokens in separater Konfigurationsdatei
- **Sandbox**: Isolierte Ausführungsumgebung

## Fehlerbehebung

### TOR-Verbindungsprobleme

```bash
# TOR-Status prüfen
sudo systemctl status tor

# TOR neu starten
sudo systemctl restart tor

# TOR-Logs anzeigen
sudo journalctl -u tor
```

### Python-Abhängigkeiten

```bash
# Neuinstallation der Abhängigkeiten
pip install -r requirements.txt --upgrade

# Virtuelle Umgebung neu erstellen
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Bildverarbeitungsprobleme

```bash
# ImageMagick prüfen
convert --version

# System-Fonts installieren
sudo apt install fonts-dejavu-core
```

## Systemd Service

Für automatischen Start beim Systemboot:

```bash
# Service installieren
sudo cp web-scanner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable web-scanner
sudo systemctl start web-scanner

# Service-Status
sudo systemctl status web-scanner
```

## Performance

- **Scan-Intervall**: Standard 1 Stunde (anpassbar)
- **Parallelität**: Mehrere Webseiten gleichzeitig
- **Caching**: Vermeidung von Duplikaten
- **Resource Management**: Speicher- und CPU-Optimierung

## Erweiterungen

Mögliche Erweiterungen:
- **RSS-Feed Unterstützung**
- **API-Integrationen**
- **Erweiterte Bild-Analyse**
- **Multi-Sprachen Unterstützung**
- **Web-Interface**

## Lizenz

MIT License - siehe LICENSE Datei

## Beitrag

Für Beiträge und Bug-Reports:
1. Issues auf GitHub erstellen
2. Pull Requests einreichen
3. Code-Style beachten

## Support

Bei Problemen:
1. Logs prüfen (`logs/` Verzeichnis)
2. Konfiguration validieren
3. System-Voraussetzungen prüfen
4. Issue auf GitHub erstellen