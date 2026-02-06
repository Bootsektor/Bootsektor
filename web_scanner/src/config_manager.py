import json
import os
from pathlib import Path
from typing import Dict, List, Any

class ConfigManager:
    """Configuration management for web scanner"""
    
    def __init__(self, config_file: str = "config/config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "scan_interval": 3600,  # 1 hour
            "websites": [
                {
                    "url": "https://example.com",
                    "selectors": {
                        "articles": "article",
                        "title": "h1, h2, .title",
                        "content": ".content, p",
                        "image": "img",
                        "link": "a"
                    }
                }
            ],
            "tor": {
                "enabled": True,
                "port": 9050,
                "control_port": 9051,
                "password": ""
            },
            "vpn": {
                "enabled": False,
                "protocol": "openvpn",
                "config_file": ""
            },
            "content_filter": {
                "keywords": ["important", "news", "update"],
                "blacklist": ["spam", "advertisement"],
                "min_content_length": 100,
                "learning_enabled": True
            },
            "image_processing": {
                "width": 800,
                "height": 600,
                "font_size": 24,
                "quality": 85
            },
            "telegram": {
                "enabled": True,
                "bot_token": "",
                "chat_id": "",
                "proxy": {
                    "enabled": False,
                    "url": ""
                }
            },
            "database": {
                "type": "sqlite",
                "path": "data/scanner.db"
            },
            "logging": {
                "level": "INFO",
                "max_files": 7
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                return {**default_config, **loaded_config}
            except Exception as e:
                print(f"Error loading config: {e}")
                return default_config
        else:
            # Create default config file
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save_config(self.config)