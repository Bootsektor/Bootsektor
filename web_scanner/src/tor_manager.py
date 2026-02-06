import asyncio
import logging
import socket
from typing import Optional

from stem import Signal
from stem.control import Controller
from stem.connection import AuthenticationFailure

class TorManager:
    """Manages TOR connection and IP rotation"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enabled = config.get('tor.enabled', False)
        self.tor_port = config.get('tor.port', 9050)
        self.control_port = config.get('tor.control_port', 9051)
        self.password = config.get('tor.password', '')
        self._controller = None
        self._connected = False
    
    async def start(self):
        """Start TOR connection"""
        if not self.enabled:
            self.logger.info("TOR is disabled, skipping connection")
            return True
        
        try:
            # Test TOR connection
            if await self._test_tor_connection():
                self._connected = True
                self.logger.info("TOR connection established successfully")
                return True
            else:
                self.logger.error("Failed to establish TOR connection")
                return False
        except Exception as e:
            self.logger.error(f"Error starting TOR: {e}")
            return False
    
    async def stop(self):
        """Stop TOR connection"""
        if self._controller:
            try:
                self._controller.close()
            except:
                pass
        self._connected = False
        self.logger.info("TOR connection stopped")
    
    async def _test_tor_connection(self) -> bool:
        """Test if TOR is working"""
        try:
            # Check if TOR control port is accessible
            with Controller.from_port(port=self.control_port) as controller:
                if self.password:
                    controller.authenticate(password=self.password)
                else:
                    controller.authenticate()
                
                # Get current IP through TOR
                import requests
                proxies = {
                    'http': f'socks5://127.0.0.1:{self.tor_port}',
                    'https': f'socks5://127.0.0.1:{self.tor_port}'
                }
                
                response = requests.get('https://check.torproject.org/', proxies=proxies, timeout=30)
                if 'Congratulations' in response.text:
                    self.logger.info("TOR is working correctly")
                    return True
                else:
                    self.logger.error("TOR connection test failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"TOR connection test error: {e}")
            return False
    
    async def rotate_ip(self):
        """Rotate TOR IP address"""
        if not self._connected or not self.enabled:
            return False
        
        try:
            with Controller.from_port(port=self.control_port) as controller:
                if self.password:
                    controller.authenticate(password=self.password)
                else:
                    controller.authenticate()
                
                # Send NEWNYM signal to get new IP
                controller.signal(Signal.NEWNYM)
                self.logger.info("TOR IP rotated successfully")
                return True
                
        except AuthenticationFailure:
            self.logger.error("TOR authentication failed")
            return False
        except Exception as e:
            self.logger.error(f"Error rotating TOR IP: {e}")
            return False
    
    def get_proxies(self) -> Optional[dict]:
        """Get proxy configuration for requests"""
        if not self._connected or not self.enabled:
            return None
        
        return {
            'http': f'socks5://127.0.0.1:{self.tor_port}',
            'https': f'socks5://127.0.0.1:{self.tor_port}'
        }
    
    async def check_ip(self) -> str:
        """Get current IP address"""
        try:
            import requests
            proxies = self.get_proxies()
            if proxies:
                response = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=30)
                return response.json().get('ip', 'Unknown')
            else:
                response = requests.get('https://api.ipify.org?format=json', timeout=30)
                return response.json().get('ip', 'Unknown')
        except Exception as e:
            self.logger.error(f"Error checking IP: {e}")
            return "Error"