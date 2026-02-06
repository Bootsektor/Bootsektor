import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

class ScannerScheduler:
    """Scheduler for periodic website scanning"""
    
    def __init__(self, scraper, config):
        self.scraper = scraper
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Scheduler configuration
        self.scan_interval = config.get('scan_interval', 3600)  # Default: 1 hour
        self.enabled = True
        self.running = False
        self.thread = None
        
        # Statistics
        self.last_scan = None
        self.next_scan = None
        self.total_scans = 0
        self.successful_scans = 0
        self.failed_scans = 0
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.enabled = True
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        self.logger.info(f"Scheduler started with interval: {self.scan_interval} seconds")
        self._schedule_next_scan()
    
    def stop(self):
        """Stop the scheduler"""
        self.enabled = False
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        
        self.logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check if it's time to scan
                if self.next_scan and current_time >= self.next_scan:
                    asyncio.run(self._perform_scan())
                    self._schedule_next_scan()
                
                # Sleep for a short interval
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def _schedule_next_scan(self):
        """Schedule the next scan"""
        if self.last_scan:
            self.next_scan = self.last_scan + timedelta(seconds=self.scan_interval)
        else:
            self.next_scan = datetime.now() + timedelta(seconds=60)  # First scan in 1 minute
        
        self.logger.info(f"Next scan scheduled for: {self.next_scan}")
    
    async def _perform_scan(self):
        """Perform a website scan"""
        try:
            self.logger.info("Starting scheduled scan...")
            scan_start = datetime.now()
            
            # Rotate TOR IP before scanning
            if hasattr(self.scraper, 'tor_manager'):
                await self.scraper.tor_manager.rotate_ip()
            
            # Perform the scan
            results = await self.scraper.scan_websites()
            
            # Update statistics
            self.last_scan = datetime.now()
            self.total_scans += 1
            self.successful_scans += 1
            
            scan_duration = (self.last_scan - scan_start).total_seconds()
            self.logger.info(f"Scan completed successfully in {scan_duration:.1f} seconds. "
                            f"Found {len(results)} articles.")
            
            # Send summary notification if configured
            await self._send_scan_summary(results)
            
        except Exception as e:
            self.logger.error(f"Error during scheduled scan: {e}")
            self.total_scans += 1
            self.failed_scans += 1
            
            # Send error notification
            await self._send_error_notification(e)
    
    async def _send_scan_summary(self, results):
        """Send scan summary notification"""
        try:
            if not results:
                return
            
            # Create summary message
            message = f"""
📊 <b>Scan Summary</b>

🕒 Scan completed: {self.last_scan.strftime('%H:%M:%S')}
📰 Articles found: {len(results)}
🔄 IP rotated: {'✅' if hasattr(self.scraper, 'tor_manager') else '❌'}

📈 Statistics:
• Total scans: {self.total_scans}
• Successful: {self.successful_scans}
• Failed: {self.failed_scans}
            """
            
            # Send via Telegram notifier if available
            if hasattr(self.scraper, 'notifier') and self.scraper.notifier.is_enabled():
                await self.scraper.notifier.bot.send_message(
                    chat_id=self.scraper.notifier.chat_id,
                    text=message,
                    parse_mode='HTML'
                )
            
        except Exception as e:
            self.logger.error(f"Error sending scan summary: {e}")
    
    async def _send_error_notification(self, error):
        """Send error notification"""
        try:
            if hasattr(self.scraper, 'notifier') and self.scraper.notifier.is_enabled():
                await self.scraper.notifier.send_error_notification(str(error))
        except Exception as e:
            self.logger.error(f"Error sending error notification: {e}")
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            'running': self.running,
            'enabled': self.enabled,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None,
            'next_scan': self.next_scan.isoformat() if self.next_scan else None,
            'scan_interval': self.scan_interval,
            'total_scans': self.total_scans,
            'successful_scans': self.successful_scans,
            'failed_scans': self.failed_scans,
            'success_rate': self.successful_scans / max(self.total_scans, 1)
        }
    
    def set_scan_interval(self, interval: int):
        """Update scan interval"""
        if interval < 60:  # Minimum 1 minute
            raise ValueError("Scan interval must be at least 60 seconds")
        
        self.scan_interval = interval
        self.config.set('scan_interval', interval)
        
        # Reschedule next scan
        if self.running:
            self._schedule_next_scan()
        
        self.logger.info(f"Scan interval updated to: {interval} seconds")
    
    def trigger_scan_now(self):
        """Trigger an immediate scan"""
        if not self.running:
            raise RuntimeError("Scheduler is not running")
        
        self.next_scan = datetime.now()
        self.logger.info("Manual scan triggered")
    
    def get_next_scan_time(self) -> Optional[datetime]:
        """Get time of next scheduled scan"""
        return self.next_scan
    
    def get_time_until_next_scan(self) -> Optional[timedelta]:
        """Get time until next scan"""
        if not self.next_scan:
            return None
        
        return max(self.next_scan - datetime.now(), timedelta(0))
    
    def pause(self):
        """Pause the scheduler"""
        self.enabled = False
        self.logger.info("Scheduler paused")
    
    def resume(self):
        """Resume the scheduler"""
        if not self.running:
            raise RuntimeError("Cannot resume: scheduler is not running")
        
        self.enabled = True
        self._schedule_next_scan()
        self.logger.info("Scheduler resumed")
    
    def is_paused(self) -> bool:
        """Check if scheduler is paused"""
        return not self.enabled and self.running