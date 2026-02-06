import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from PIL import Image, ImageDraw, ImageFont
import textwrap

class ImageProcessor:
    """Image processing for creating summary images"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Image configuration
        self.width = config.get('image_processing.width', 800)
        self.height = config.get('image_processing.height', 600)
        self.font_size = config.get('image_processing.font_size', 24)
        self.quality = config.get('image_processing.quality', 85)
        
        # Create output directory
        self.output_dir = Path("data/summaries")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to load fonts
        self._load_fonts()
    
    def _load_fonts(self):
        """Load fonts for text rendering"""
        try:
            # Try to use system fonts
            self.title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
                                                 self.font_size + 8)
            self.text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 
                                               self.font_size)
        except:
            try:
                # Fallback to default fonts
                self.title_font = ImageFont.load_default()
                self.text_font = ImageFont.load_default()
            except:
                self.logger.warning("Could not load fonts, using default")
                self.title_font = None
                self.text_font = None
    
    async def create_summary(self, article: Dict[str, Any]) -> Optional[str]:
        """Create summary image with headline and featured image"""
        try:
            # Create base image
            img = Image.new('RGB', (self.width, self.height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add featured image if available
            image_y = 0
            if article.get('local_image_path'):
                image_y = await self._add_featured_image(img, draw, article['local_image_path'])
            
            # Add title
            title_y = await self._add_title(draw, article['title'], image_y)
            
            # Add summary text
            await self._add_summary_text(draw, article['cleaned_content'], title_y)
            
            # Add timestamp and source
            await self._add_metadata(draw, article)
            
            # Save image
            filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(article['title']) % 10000}.jpg"
            filepath = self.output_dir / filename
            
            img.save(filepath, 'JPEG', quality=self.quality)
            self.logger.info(f"Created summary image: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Error creating summary image: {e}")
            return None
    
    async def _add_featured_image(self, img: Image.Image, draw: ImageDraw.ImageDraw, 
                                 image_path: str) -> int:
        """Add featured image to summary"""
        try:
            # Open and resize featured image
            with Image.open(image_path) as featured_img:
                # Calculate dimensions (top half of image)
                img_width, img_height = img.size
                featured_height = img_height // 2
                
                # Resize and crop to fit
                featured_img = self._resize_and_crop(featured_img, img_width, featured_height)
                
                # Paste onto main image
                img.paste(featured_img, (0, 0))
                
                # Add subtle gradient overlay for better text readability
                overlay = Image.new('RGBA', (img_width, featured_height), (0, 0, 0, 0))
                draw_overlay = ImageDraw.Draw(overlay)
                
                for y in range(featured_height):
                    alpha = int(50 * (1 - y / featured_height))  # Gradient from 50 to 0
                    draw_overlay.line([(0, y), (img_width, y)], fill=(0, 0, 0, alpha))
                
                img.paste(Image.alpha_composite(img.convert('RGBA'), overlay), 
                         (0, 0), overlay)
            
            return featured_height
            
        except Exception as e:
            self.logger.error(f"Error adding featured image: {e}")
            return 0
    
    def _resize_and_crop(self, img: Image.Image, target_width: int, 
                        target_height: int) -> Image.Image:
        """Resize and crop image to target dimensions"""
        # Calculate aspect ratios
        img_ratio = img.width / img.height
        target_ratio = target_width / target_height
        
        if img_ratio > target_ratio:
            # Image is wider - crop width
            new_height = target_height
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop center
            left = (new_width - target_width) // 2
            img = img.crop((left, 0, left + target_width, target_height))
        else:
            # Image is taller - crop height
            new_width = target_width
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop center
            top = (new_height - target_height) // 2
            img = img.crop((0, top, target_width, top + target_height))
        
        return img
    
    async def _add_title(self, draw: ImageDraw.ImageDraw, title: str, 
                        start_y: int) -> int:
        """Add article title to image"""
        try:
            # Wrap title to fit width
            max_width = self.width - 40  # 20px margin on each side
            wrapped_title = textwrap.fill(title, width=50)  # Approximate character limit
            
            # Calculate text position
            if self.title_font:
                bbox = draw.textbbox((0, 0), wrapped_title, font=self.title_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(wrapped_title) * 10  # Approximate
                text_height = self.font_size + 8
            
            x = (self.width - text_width) // 2
            y = start_y + 20
            
            # Add text with shadow for better readability
            shadow_offset = 2
            draw.text((x + shadow_offset, y + shadow_offset), wrapped_title, 
                     fill='black', font=self.title_font)
            draw.text((x, y), wrapped_title, fill='white', font=self.title_font)
            
            return y + text_height + 20
            
        except Exception as e:
            self.logger.error(f"Error adding title: {e}")
            return start_y + 50
    
    async def _add_summary_text(self, draw: ImageDraw.ImageDraw, content: str, 
                               start_y: int):
        """Add summary text to image"""
        try:
            # Truncate content for summary
            max_chars = 200
            if len(content) > max_chars:
                content = content[:max_chars] + "..."
            
            # Wrap text
            wrapped_text = textwrap.fill(content, width=60)
            
            # Calculate position
            x = 20
            y = start_y
            
            # Add text
            draw.text((x, y), wrapped_text, fill='black', font=self.text_font)
            
        except Exception as e:
            self.logger.error(f"Error adding summary text: {e}")
    
    async def _add_metadata(self, draw: ImageDraw.ImageDraw, article: Dict[str, Any]):
        """Add metadata (timestamp, source) to image"""
        try:
            # Format timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            source = article.get('source_url', 'Unknown')
            
            # Extract domain from source URL
            if source != 'Unknown':
                from urllib.parse import urlparse
                domain = urlparse(source).netloc
            else:
                domain = 'Unknown'
            
            metadata_text = f"{timestamp} | {domain}"
            
            # Position at bottom right
            if self.text_font:
                bbox = draw.textbbox((0, 0), metadata_text, font=self.text_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(metadata_text) * 8
                text_height = self.font_size
            
            x = self.width - text_width - 20
            y = self.height - text_height - 20
            
            # Add text with subtle background
            padding = 5
            draw.rectangle([x - padding, y - padding, 
                           x + text_width + padding, y + text_height + padding],
                          fill='lightgray')
            draw.text((x, y), metadata_text, fill='black', font=self.text_font)
            
        except Exception as e:
            self.logger.error(f"Error adding metadata: {e}")
    
    async def create_placeholder_image(self, title: str) -> str:
        """Create placeholder image when no featured image is available"""
        try:
            img = Image.new('RGB', (self.width, self.height), color='lightblue')
            draw = ImageDraw.Draw(img)
            
            # Add title
            wrapped_title = textwrap.fill(title, width=40)
            
            if self.title_font:
                bbox = draw.textbbox((0, 0), wrapped_title, font=self.title_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(wrapped_title) * 10
                text_height = self.font_size + 8
            
            x = (self.width - text_width) // 2
            y = (self.height - text_height) // 2
            
            draw.text((x, y), wrapped_title, fill='darkblue', font=self.title_font)
            
            # Save
            filename = f"placeholder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self.output_dir / filename
            img.save(filepath, 'JPEG', quality=self.quality)
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Error creating placeholder image: {e}")
            return None