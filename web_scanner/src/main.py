#!/usr/bin/env python3
"""
Web Scanner with TOR/VPN support
Periodically scans websites, filters content, creates summary images and sends notifications
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime
from pathlib import Path

from src.config_manager import ConfigManager
from src.tor_manager import TorManager
from src.web_scraper import WebScraper
from src.content_filter import ContentFilter
from src.image_processor import ImageProcessor
from src.learning_database import LearningDatabase
from src.telegram_notifier import TelegramNotifier
from src.scheduler import ScannerScheduler

def setup_logging():
    """Setup logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f"scanner_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )

async def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Web Scanner...")
        
        # Initialize components
        config = ConfigManager()
        tor_manager = TorManager(config)
        content_filter = ContentFilter(config)
        image_processor = ImageProcessor(config)
        learning_db = LearningDatabase(config)
        telegram_notifier = TelegramNotifier(config)
        
        # Initialize web scraper with TOR support
        scraper = WebScraper(
            config=config,
            tor_manager=tor_manager,
            content_filter=content_filter,
            image_processor=image_processor,
            learning_db=learning_db,
            notifier=telegram_notifier
        )
        
        # Setup scheduler
        scheduler = ScannerScheduler(scraper, config)
        scheduler.start()
        
        logger.info("Web Scanner started successfully")
        
        # Keep the main thread alive
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if 'scheduler' in locals():
            scheduler.stop()
        if 'tor_manager' in locals():
            await tor_manager.stop()
        logger.info("Web Scanner stopped")

if __name__ == "__main__":
    asyncio.run(main())