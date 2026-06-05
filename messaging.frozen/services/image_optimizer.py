"""
Image optimization service for chat themes
Handles image compression, resizing, and format optimization
"""

from PIL import Image, ImageOps
from io import BytesIO
import os
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
import hashlib


class ImageOptimizer:
    """Optimize images for chat themes with size and quality constraints"""
    
    MAX_WIDTH = 1920
    MAX_HEIGHT = 1080
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    QUALITY = 85
    THUMBNAIL_SIZE = (400, 300)
    
    @classmethod
    def optimize_theme_image(cls, image_file):
        """
        Optimize uploaded theme image
        
        Args:
            image_file: Uploaded image file
            
        Returns:
            Optimized InMemoryUploadedFile
        """
        try:
            # Open image
            img = Image.open(image_file)
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Auto-orient image based on EXIF data
            img = ImageOps.exif_transpose(img)
            
            # Calculate new dimensions maintaining aspect ratio
            width, height = img.size
            if width > cls.MAX_WIDTH or height > cls.MAX_HEIGHT:
                ratio = min(cls.MAX_WIDTH / width, cls.MAX_HEIGHT / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create thumbnail for preview
            thumbnail = img.copy()
            thumbnail.thumbnail(cls.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            
            # Save optimized image
            output = BytesIO()
            
            # Determine best format
            if img.size[0] * img.size[1] < 500 * 500:  # Small images
                format = 'PNG'
                img.save(output, format=format, optimize=True)
            else:  # Larger images
                format = 'JPEG'
                img.save(output, format=format, quality=cls.QUALITY, optimize=True, progressive=True)
            
            output.seek(0)
            
            # Create optimized file
            optimized_file = InMemoryUploadedFile(
                output,
                'ImageField',
                f"optimized_{image_file.name}",
                f'image/{format.lower()}',
                output.tell(),
                None
            )
            
            return optimized_file
            
        except Exception as e:
            print(f"Image optimization error: {e}")
            return image_file
    
    @classmethod
    def generate_image_hash(cls, image_file):
        """Generate hash for image deduplication"""
        try:
            img = Image.open(image_file)
            img = ImageOps.exif_transpose(img)
            img.thumbnail((100, 100), Image.Resampling.LANCZOS)
            
            # Convert to bytes for hashing
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return hashlib.md5(img_bytes.read()).hexdigest()
        except Exception:
            return None
    
    @classmethod
    def get_image_info(cls, image_file):
        """Get image information"""
        try:
            img = Image.open(image_file)
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'size': image_file.size
            }
        except Exception:
            return None


class ThemeImageCache:
    """Cache for theme images with invalidation"""
    
    CACHE_DIR = os.path.join(settings.MEDIA_ROOT, 'cache', 'theme_images')
    CACHE_DURATION = 86400 * 7  # 7 days
    
    @classmethod
    def get_cache_key(cls, conversation_id, user_id, theme_mode):
        """Generate cache key for theme image"""
        return f"theme_{conversation_id}_{user_id}_{theme_mode}"
    
    @classmethod
    def get_cached_image_path(cls, cache_key):
        """Get cached image path"""
        return os.path.join(cls.CACHE_DIR, f"{cache_key}.jpg")
    
    @classmethod
    def is_cached(cls, cache_key):
        """Check if image is cached and not expired"""
        cache_path = cls.get_cached_image_path(cache_key)
        if not os.path.exists(cache_path):
            return False
        
        # Check if cache is expired
        import time
        file_age = time.time() - os.path.getmtime(cache_path)
        return file_age < cls.CACHE_DURATION
    
    @classmethod
    def cache_image(cls, original_image, cache_key):
        """Cache optimized image"""
        try:
            # Ensure cache directory exists
            os.makedirs(cls.CACHE_DIR, exist_ok=True)
            
            # Optimize and cache image
            optimized = ImageOptimizer.optimize_theme_image(original_image)
            
            cache_path = cls.get_cached_image_path(cache_key)
            with open(cache_path, 'wb') as f:
                f.write(optimized.read())
            
            return cache_path
        except Exception as e:
            print(f"Cache error: {e}")
            return None
    
    @classmethod
    def clear_cache(cls, conversation_id=None, user_id=None):
        """Clear cache for specific conversation/user or all"""
        import glob
        import time
        
        if conversation_id and user_id:
            # Clear specific conversation themes
            pattern = f"theme_{conversation_id}_{user_id}_*"
        elif conversation_id:
            # Clear all themes for conversation
            pattern = f"theme_{conversation_id}_*"
        elif user_id:
            # Clear all themes for user
            pattern = f"theme_*_{user_id}_*"
        else:
            # Clear all cache
            pattern = "theme_*"
        
        cache_files = glob.glob(os.path.join(cls.CACHE_DIR, pattern))
        current_time = time.time()
        
        for cache_file in cache_files:
            # Remove expired files
            file_age = current_time - os.path.getmtime(cache_file)
            if file_age > cls.CACHE_DURATION:
                try:
                    os.remove(cache_file)
                except OSError:
                    pass
