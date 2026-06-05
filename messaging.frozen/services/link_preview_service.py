"""
Link Preview Service

Handles server-side link preview generation with:
- URL detection and validation
- Open Graph metadata extraction
- Image download and local caching
- Fallback systems for missing metadata
"""

import re
import logging
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.utils.html import strip_tags
from ..models import LinkPreview

logger = logging.getLogger(__name__)


class LinkPreviewService:
    """Service for generating and caching link previews."""
    
    # URL pattern for detecting URLs in text
    URL_PATTERN = re.compile(
        r'https?://(?:www\.)?[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+[^\s]*'
    )
    
    # User agent for requests
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    # Request timeout
    REQUEST_TIMEOUT = 10
    
    # Maximum image size (5MB)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    
    @classmethod
    def extract_urls(cls, text):
        """
        Extract URLs from message text.
        
        Args:
            text: Message content
            
        Returns:
            List of valid URLs
        """
        if not text:
            return []
        
        urls = []
        matches = cls.URL_PATTERN.findall(text)
        
        for match in matches:
            url = match if match.startswith('http') else 'https://' + match
            if cls.is_valid_url(url):
                urls.append(url)
        
        logger.info(f"[LINK_PREVIEW] Extracted {len(urls)} URLs from text")
        return urls
    
    @classmethod
    def is_valid_url(cls, url):
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            bool: True if valid
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @classmethod
    def normalize_url(cls, url):
        """
        Normalize URL (add scheme if missing, remove trailing slash).
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Remove trailing slash
        if url.endswith('/'):
            url = url[:-1]
        
        return url
    
    @classmethod
    def get_or_create_preview(cls, url):
        """
        Get existing preview or create new one.
        
        Args:
            url: URL to generate preview for
            
        Returns:
            LinkPreview instance
        """
        url = cls.normalize_url(url)
        
        # Check cache first
        try:
            preview = LinkPreview.objects.get(url=url)
            logger.info(f"[LINK_PREVIEW] Cached preview reused for {url}")
            return preview
        except LinkPreview.DoesNotExist:
            pass
        
        # Create new preview
        logger.info(f"[LINK_PREVIEW] Fetching metadata for {url}")
        preview = cls._fetch_and_create_preview(url)
        
        return preview
    
    @classmethod
    def _fetch_and_create_preview(cls, url):
        """
        Fetch metadata and create new preview.
        
        Args:
            url: URL to fetch
            
        Returns:
            LinkPreview instance
        """
        preview = LinkPreview.objects.create(url=url)
        
        try:
            # Fetch HTML
            html = cls._fetch_html(url)
            if not html:
                preview.fetch_failed = True
                preview.fetch_error = "Failed to fetch HTML"
                preview.save()
                return preview
            
            # Parse metadata
            metadata = cls._extract_metadata(html, url)
            
            # Update preview with metadata
            preview.title = metadata.get('title', '')[:500]
            preview.description = metadata.get('description', '')
            preview.site_name = metadata.get('site_name', '')
            preview.domain = metadata.get('domain', '')
            
            # Download and cache images
            if metadata.get('image_url'):
                preview.image = cls._download_image(
                    metadata['image_url'],
                    url
                )
            
            if metadata.get('favicon_url'):
                preview.favicon = cls._download_image(
                    metadata['favicon_url'],
                    url
                )
            
            preview.save()
            logger.info(f"[LINK_PREVIEW] Preview created successfully for {url}")
            
        except Exception as e:
            logger.error(f"[LINK_PREVIEW] Error creating preview for {url}: {str(e)}")
            preview.fetch_failed = True
            preview.fetch_error = str(e)
            preview.save()
        
        return preview
    
    @classmethod
    def _fetch_html(cls, url):
        """
        Fetch HTML from URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML string or None
        """
        try:
            headers = {'User-Agent': cls.USER_AGENT}
            response = requests.get(url, headers=headers, timeout=cls.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type:
                logger.warning(f"[LINK_PREVIEW] Non-HTML content type: {content_type}")
                return None
            
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"[LINK_PREVIEW] Request error for {url}: {str(e)}")
            return None
    
    @classmethod
    def _extract_metadata(cls, html, base_url):
        """
        Extract Open Graph and fallback metadata.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Dict with metadata
        """
        soup = BeautifulSoup(html, 'lxml')
        metadata = {}
        
        # Extract domain
        parsed = urlparse(base_url)
        metadata['domain'] = parsed.netloc
        
        # Open Graph tags
        og_tags = {
            'title': soup.find('meta', property='og:title'),
            'description': soup.find('meta', property='og:description'),
            'image': soup.find('meta', property='og:image'),
            'site_name': soup.find('meta', property='og:site_name'),
        }
        
        # Extract OG metadata
        for key, tag in og_tags.items():
            if tag and tag.get('content'):
                metadata[f'{key}_url' if key in ['image'] else key] = tag.get('content')
        
        # Fallback to standard meta tags
        if not metadata.get('title'):
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
        
        if not metadata.get('description'):
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag and desc_tag.get('content'):
                metadata['description'] = desc_tag.get('content')
        
        # Fallback for image
        if not metadata.get('image_url'):
            # Try to find first large image
            img_tag = soup.find('img')
            if img_tag and img_tag.get('src'):
                metadata['image_url'] = urljoin(base_url, img_tag.get('src'))
        
        # Favicon
        favicon_link = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        if favicon_link and favicon_link.get('href'):
            metadata['favicon_url'] = urljoin(base_url, favicon_link.get('href'))
        
        # Sanitize metadata
        for key in ['title', 'description', 'site_name']:
            if key in metadata and metadata[key]:
                metadata[key] = strip_tags(metadata[key]).strip()
        
        # Log warnings for missing metadata
        if not metadata.get('image_url'):
            logger.warning(f"[LINK_PREVIEW] No OG image found for {base_url}")
        
        return metadata
    
    @classmethod
    def _download_image(cls, image_url, base_url):
        """
        Download and cache image locally.
        
        Args:
            image_url: URL of image to download
            base_url: Base URL for resolving relative URLs
            
        Returns:
            SimpleUploadedFile or None
        """
        try:
            # Resolve relative URLs
            if not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(base_url, image_url)
            
            headers = {'User-Agent': cls.USER_AGENT}
            response = requests.get(
                image_url,
                headers=headers,
                timeout=cls.REQUEST_TIMEOUT,
                stream=True
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"[LINK_PREVIEW] Non-image content type: {content_type}")
                return None
            
            # Check file size
            content_length = int(response.headers.get('content-length', 0))
            if content_length > cls.MAX_IMAGE_SIZE:
                logger.warning(f"[LINK_PREVIEW] Image too large: {content_length} bytes")
                return None
            
            # Download content
            image_content = response.content
            
            # Determine extension
            ext = content_type.split('/')[-1]
            if ext == 'jpeg':
                ext = 'jpg'
            
            # Create uploaded file
            filename = f"preview_{hash(image_url)}.{ext}"
            uploaded_file = SimpleUploadedFile(
                filename,
                image_content,
                content_type=content_type
            )
            
            logger.info(f"[LINK_PREVIEW] Downloaded image: {image_url}")
            return uploaded_file
            
        except Exception as e:
            logger.error(f"[LINK_PREVIEW] Error downloading image {image_url}: {str(e)}")
            return None
    
    @classmethod
    def generate_preview_for_message(cls, message):
        """
        Generate link preview for a message.
        
        Args:
            message: Message instance
            
        Returns:
            LinkPreview instance or None
        """
        if not message.content:
            return None
        
        # Extract URLs from message content
        urls = cls.extract_urls(message.content)
        
        if not urls:
            return None
        
        # Generate preview for first URL only
        first_url = urls[0]
        preview = cls.get_or_create_preview(first_url)
        
        # Attach preview to message
        message.link_preview = preview
        message.save(update_fields=['link_preview'])
        
        logger.info(f"[LINK_PREVIEW] Generated preview for message {message.id}")
        return preview
