"""
Link Preview Service

Handles server-side link preview generation with:
- URL detection and validation
- Specialized providers (YouTube, TikTok, Instagram, Twitter/X, Spotify) via oEmbed & direct resolvers
- Open Graph and Twitter Card metadata extraction for general websites
- Image download and local caching with remote URL fallback
- Resilient error handling
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
        r'(?:(?:https?://|www\.)[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+(?:/[^\s]*)?|(?:youtu\.be|tiktok\.com|instagram\.com)/[^\s]+)',
        re.IGNORECASE
    )
    
    # Platform patterns
    YOUTUBE_PATTERN = re.compile(
        r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?.*?v=|shorts/|embed/)|youtu\.be/)([a-zA-Z0-9_-]{11})',
        re.IGNORECASE
    )
    TIKTOK_PATTERN = re.compile(
        r'https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+',
        re.IGNORECASE
    )
    INSTAGRAM_PATTERN = re.compile(
        r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/([a-zA-Z0-9_-]+)',
        re.IGNORECASE
    )
    TWITTER_PATTERN = re.compile(
        r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/status/\d+',
        re.IGNORECASE
    )
    SPOTIFY_PATTERN = re.compile(
        r'https?://open\.spotify\.com/(?:track|album|playlist|episode)/[a-zA-Z0-9]+',
        re.IGNORECASE
    )

    # User agent for requests
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    # Request timeouts
    REQUEST_TIMEOUT = 8
    OEMBED_TIMEOUT = 5
    
    # Maximum image size (5MB)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    
    @classmethod
    def extract_urls(cls, text):
        """
        Extract URLs from message or post text.
        
        Args:
            text: Content string
            
        Returns:
            List of valid URLs
        """
        if not text:
            return []
        
        urls = []
        matches = cls.URL_PATTERN.findall(text)
        
        for match in matches:
            # Clean trailing punctuation often attached to URLs in prose
            cleaned = re.sub(r'[.,;!?)\]>]+$', '', match)
            url = cleaned if cleaned.startswith(('http://', 'https://')) else 'https://' + cleaned
            if cls.is_valid_url(url) and url not in urls:
                urls.append(url)
        
        logger.info(f"[LINK_PREVIEW] Extracted {len(urls)} URLs from text")
        return urls
    
    @classmethod
    def is_valid_url(cls, url):
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except Exception:
            return False
    
    @classmethod
    def normalize_url(cls, url):
        """Normalize URL (ensure scheme, strip trailing whitespace/slash)."""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if url.endswith('/') and len(urlparse(url).path) > 1:
            url = url[:-1]
        
        return url
    
    @classmethod
    def get_or_create_preview(cls, url):
        """
        Get existing preview or create a new one.
        
        Args:
            url: URL to generate preview for
            
        Returns:
            LinkPreview instance or None
        """
        url = cls.normalize_url(url)
        
        # Check cache first
        try:
            preview = LinkPreview.objects.get(url=url)
            logger.info(f"[LINK_PREVIEW] Cached preview reused for {url}")
            return preview
        except LinkPreview.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"[LINK_PREVIEW] Cache check error for {url}: {e}")
        
        # Create and fetch new preview
        return cls._fetch_and_create_preview(url)
    
    @classmethod
    def _fetch_and_create_preview(cls, url):
        """
        Fetch metadata and create new preview record.
        
        Args:
            url: Normalized URL
            
        Returns:
            LinkPreview instance
        """
        preview, _ = LinkPreview.objects.get_or_create(url=url)
        
        try:
            metadata = None
            
            # 1. Specialized platform handlers
            if cls.YOUTUBE_PATTERN.search(url):
                metadata = cls._extract_youtube(url)
            elif cls.TIKTOK_PATTERN.search(url):
                metadata = cls._extract_tiktok(url)
            elif cls.INSTAGRAM_PATTERN.search(url):
                metadata = cls._extract_instagram(url)
            elif cls.TWITTER_PATTERN.search(url):
                metadata = cls._extract_twitter(url)
            elif cls.SPOTIFY_PATTERN.search(url):
                metadata = cls._extract_spotify(url)
            
            # 2. General fallback via HTML OpenGraph scraping
            if not metadata:
                html = cls._fetch_html(url)
                if html:
                    metadata = cls._extract_metadata(html, url)
                else:
                    # Provide minimal domain fallback if fetch failed
                    parsed = urlparse(url)
                    metadata = {
                        'title': parsed.netloc,
                        'description': f'Visit {parsed.netloc}',
                        'site_name': parsed.netloc,
                        'domain': parsed.netloc,
                        'media_type': 'link',
                    }
                    preview.fetch_failed = True
                    preview.fetch_error = "Could not fetch target HTML"

            # Apply extracted metadata
            preview.title = (metadata.get('title') or '')[:500]
            preview.description = metadata.get('description', '')
            preview.site_name = (metadata.get('site_name') or '')[:255]
            preview.domain = (metadata.get('domain') or urlparse(url).netloc)[:255]
            preview.media_type = metadata.get('media_type', 'link')
            
            # Handle thumbnail: store remote URL as immediate fallback
            remote_img = metadata.get('image_url')
            if remote_img and not remote_img.startswith('data:'):
                preview.remote_image_url = remote_img[:2048]
                # Attempt to download and cache locally
                cached_file = cls._download_image(remote_img, url)
                if cached_file:
                    preview.image = cached_file

            # Handle favicon
            favicon_url = metadata.get('favicon_url')
            if favicon_url and not favicon_url.startswith('data:'):
                cached_favicon = cls._download_image(favicon_url, url)
                if cached_favicon:
                    preview.favicon = cached_favicon

            preview.fetch_failed = False
            preview.fetch_error = None
            preview.save()
            logger.info(f"[LINK_PREVIEW] Successfully populated preview for {url} ({preview.domain})")

        except Exception as e:
            logger.error(f"[LINK_PREVIEW] Error creating preview for {url}: {str(e)}")
            preview.fetch_failed = True
            preview.fetch_error = str(e)
            # Ensure domain is set even on error
            try:
                preview.domain = urlparse(url).netloc
            except Exception:
                pass
            preview.save()
        
        return preview

    @classmethod
    def _extract_youtube(cls, url):
        """Extract metadata for YouTube videos using oEmbed and direct fallback."""
        match = cls.YOUTUBE_PATTERN.search(url)
        video_id = match.group(1) if match else None
        
        fallback_thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else None
        
        metadata = {
            'title': 'YouTube Video',
            'description': 'Watch this video on YouTube',
            'site_name': 'YouTube',
            'domain': 'youtube.com',
            'image_url': fallback_thumbnail,
            'media_type': 'video',
            'favicon_url': 'https://www.youtube.com/favicon.ico'
        }
        
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            res = requests.get(oembed_url, headers={'User-Agent': cls.USER_AGENT}, timeout=cls.OEMBED_TIMEOUT)
            if res.status_code == 200:
                data = res.json()
                metadata['title'] = data.get('title') or metadata['title']
                author = data.get('author_name')
                if author:
                    metadata['site_name'] = f"YouTube • {author}"
                    metadata['description'] = f"Uploaded by {author} on YouTube"
                if data.get('thumbnail_url'):
                    metadata['image_url'] = data.get('thumbnail_url')
        except Exception as e:
            logger.warning(f"[LINK_PREVIEW] YouTube oEmbed failed for {url}: {e}")
            
        return metadata

    @classmethod
    def _extract_tiktok(cls, url):
        """Extract metadata for TikTok videos using TikTok's public oEmbed."""
        metadata = {
            'title': 'Watch on TikTok',
            'description': 'Watch trending short-form video on TikTok',
            'site_name': 'TikTok',
            'domain': 'tiktok.com',
            'media_type': 'video',
            'favicon_url': 'https://www.tiktok.com/favicon.ico'
        }
        
        target_url = url
        # If it's a short URL (vm.tiktok.com, vt.tiktok.com), follow redirect to canonical URL
        if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url or '/t/' in url:
            try:
                r = requests.head(url, allow_redirects=True, timeout=cls.OEMBED_TIMEOUT, headers={'User-Agent': cls.USER_AGENT})
                target_url = r.url.split('?')[0]
            except Exception:
                pass
        else:
            target_url = url.split('?')[0]

        # Extract author handle if visible in URL
        author_match = re.search(r'/@([a-zA-Z0-9_.-]+)', target_url)
        if author_match:
            author_handle = author_match.group(1)
            metadata['title'] = f"TikTok Video by @{author_handle}"
            metadata['site_name'] = f"TikTok • @{author_handle}"
            metadata['description'] = f"Video by @{author_handle} on TikTok"
        
        try:
            oembed_url = f"https://www.tiktok.com/oembed?url={target_url}"
            res = requests.get(oembed_url, headers={'User-Agent': cls.USER_AGENT}, timeout=cls.OEMBED_TIMEOUT)
            if res.status_code == 200:
                data = res.json()
                metadata['title'] = data.get('title') or metadata['title']
                author = data.get('author_unique_id') or data.get('author_name')
                if author:
                    metadata['site_name'] = f"TikTok • @{author}"
                    metadata['description'] = f"Video by @{author} on TikTok"
                if data.get('thumbnail_url'):
                    metadata['image_url'] = data.get('thumbnail_url')
        except Exception as e:
            logger.warning(f"[LINK_PREVIEW] TikTok oEmbed failed for {url}: {e}")
            
        return metadata

    @classmethod
    def _extract_instagram(cls, url):
        """Extract metadata for Instagram posts & reels."""
        match = cls.INSTAGRAM_PATTERN.search(url)
        shortcode = match.group(1) if match else ''
        is_reel = '/reel/' in url.lower()
        
        metadata = {
            'title': f"Instagram {'Reel' if is_reel else 'Post'}",
            'description': f"View this {'reel' if is_reel else 'post'} on Instagram",
            'site_name': 'Instagram',
            'domain': 'instagram.com',
            'media_type': 'video' if is_reel else 'photo',
            'favicon_url': 'https://www.instagram.com/favicon.ico'
        }
        
        # Try scraping HTML in case OG meta is exposed
        html = cls._fetch_html(url)
        if html:
            extracted = cls._extract_metadata(html, url)
            if extracted.get('title') and 'Login' not in extracted.get('title'):
                metadata['title'] = extracted['title']
            if extracted.get('description') and 'welcome back' not in extracted.get('description', '').lower():
                metadata['description'] = extracted['description']
            if extracted.get('image_url'):
                metadata['image_url'] = extracted['image_url']
                
        return metadata

    @classmethod
    def _extract_twitter(cls, url):
        """Extract metadata for Twitter / X tweets using publish oEmbed."""
        metadata = {
            'title': 'Post on X',
            'description': 'View post on X (formerly Twitter)',
            'site_name': 'X',
            'domain': 'x.com',
            'media_type': 'link',
            'favicon_url': 'https://abs.twimg.com/favicons/twitter.3.ico'
        }
        try:
            oembed_url = f"https://publish.twitter.com/oembed?url={url}"
            res = requests.get(oembed_url, headers={'User-Agent': cls.USER_AGENT}, timeout=cls.OEMBED_TIMEOUT)
            if res.status_code == 200:
                data = res.json()
                author = data.get('author_name')
                if author:
                    metadata['title'] = f"Post by {author} on X"
                    metadata['site_name'] = f"X • {author}"
                html = data.get('html', '')
                if html:
                    soup = BeautifulSoup(html, 'lxml')
                    metadata['description'] = soup.get_text()[:300].strip()
        except Exception as e:
            logger.warning(f"[LINK_PREVIEW] Twitter oEmbed failed for {url}: {e}")
        return metadata

    @classmethod
    def _extract_spotify(cls, url):
        """Extract metadata for Spotify music/podcasts."""
        metadata = {
            'title': 'Listen on Spotify',
            'description': 'Stream audio on Spotify',
            'site_name': 'Spotify',
            'domain': 'spotify.com',
            'media_type': 'audio',
            'favicon_url': 'https://open.spotifycdn.com/cdn/images/favicon.0f31d2ea.ico'
        }
        try:
            oembed_url = f"https://open.spotify.com/oembed?url={url}"
            res = requests.get(oembed_url, headers={'User-Agent': cls.USER_AGENT}, timeout=cls.OEMBED_TIMEOUT)
            if res.status_code == 200:
                data = res.json()
                metadata['title'] = data.get('title') or metadata['title']
                if data.get('thumbnail_url'):
                    metadata['image_url'] = data.get('thumbnail_url')
        except Exception as e:
            logger.warning(f"[LINK_PREVIEW] Spotify oEmbed failed for {url}: {e}")
        return metadata

    @classmethod
    def _fetch_html(cls, url):
        """Fetch HTML from URL."""
        try:
            headers = {
                'User-Agent': cls.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            response = requests.get(url, headers=headers, timeout=cls.REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                logger.warning(f"[LINK_PREVIEW] Non-HTML content type: {content_type}")
                return None
            
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"[LINK_PREVIEW] Request error for {url}: {str(e)}")
            return None
    
    @classmethod
    def _extract_metadata(cls, html, base_url):
        """Extract Open Graph and fallback metadata."""
        soup = BeautifulSoup(html, 'lxml')
        metadata = {}
        
        parsed = urlparse(base_url)
        metadata['domain'] = parsed.netloc
        metadata['media_type'] = 'link'
        
        # 1. Open Graph tags
        og_tags = {
            'title': soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'twitter:title'}),
            'description': soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'twitter:description'}),
            'image': soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'twitter:image'}),
            'site_name': soup.find('meta', property='og:site_name'),
            'type': soup.find('meta', property='og:type'),
        }
        
        for key, tag in og_tags.items():
            if tag and tag.get('content'):
                if key == 'image':
                    metadata['image_url'] = tag.get('content').strip()
                elif key == 'type':
                    og_type = tag.get('content', '').lower()
                    if 'video' in og_type:
                        metadata['media_type'] = 'video'
                    elif 'music' in og_type or 'audio' in og_type:
                        metadata['media_type'] = 'audio'
                else:
                    metadata[key] = tag.get('content').strip()
        
        # 2. Fallbacks
        if not metadata.get('title'):
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
        
        if not metadata.get('description'):
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag and desc_tag.get('content'):
                metadata['description'] = desc_tag.get('content').strip()
        
        if not metadata.get('site_name'):
            metadata['site_name'] = parsed.netloc.replace('www.', '')

        # Fallback image search
        if not metadata.get('image_url'):
            link_img = soup.find('link', rel='image_src')
            if link_img and link_img.get('href'):
                metadata['image_url'] = urljoin(base_url, link_img.get('href'))
            else:
                img_tag = soup.find('img')
                if img_tag and img_tag.get('src') and not img_tag.get('src').endswith('.svg'):
                    metadata['image_url'] = urljoin(base_url, img_tag.get('src'))

        # Favicon
        favicon_link = soup.find('link', rel=re.compile(r'^(shortcut )?icon$', re.I))
        if favicon_link and favicon_link.get('href'):
            metadata['favicon_url'] = urljoin(base_url, favicon_link.get('href'))
        else:
            metadata['favicon_url'] = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        
        # Sanitize metadata
        for key in ['title', 'description', 'site_name']:
            if key in metadata and metadata[key]:
                metadata[key] = strip_tags(metadata[key]).strip()
        
        return metadata
    
    @classmethod
    def _download_image(cls, image_url, base_url):
        """Download and cache image locally."""
        try:
            if not image_url or image_url.startswith('data:'):
                return None

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
            
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"[LINK_PREVIEW] Non-image content type: {content_type}")
                return None
            
            content_length = int(response.headers.get('content-length', 0))
            if content_length > cls.MAX_IMAGE_SIZE:
                logger.warning(f"[LINK_PREVIEW] Image too large: {content_length} bytes")
                return None
            
            image_content = response.content
            if not image_content:
                return None
                
            ext = content_type.split('/')[-1]
            if ext == 'jpeg':
                ext = 'jpg'
            elif ';' in ext:
                ext = ext.split(';')[0]
            
            filename = f"preview_{abs(hash(image_url))}.{ext}"
            uploaded_file = SimpleUploadedFile(
                filename,
                image_content,
                content_type=content_type
            )
            
            logger.info(f"[LINK_PREVIEW] Downloaded image: {image_url}")
            return uploaded_file
            
        except Exception as e:
            logger.warning(f"[LINK_PREVIEW] Error downloading image {image_url}: {str(e)}")
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
        
        urls = cls.extract_urls(message.content)
        if not urls:
            return None
        
        first_url = urls[0]
        preview = cls.get_or_create_preview(first_url)
        
        if preview:
            message.link_preview = preview
            message.save(update_fields=['link_preview'])
            logger.info(f"[LINK_PREVIEW] Attached preview {preview.id} to message {message.id}")
        
        return preview

    @classmethod
    def generate_preview_for_post(cls, post):
        """
        Generate link preview for a post.
        
        Args:
            post: Post instance
            
        Returns:
            LinkPreview instance or None
        """
        content = post.content or ''
        # If this is a repost with its own comment, prefer its own content, else original content
        if not content and post.repost_of and post.repost_of.content:
            content = post.repost_of.content
            
        if not content:
            return None
        
        urls = cls.extract_urls(content)
        if not urls:
            return None
        
        first_url = urls[0]
        preview = cls.get_or_create_preview(first_url)
        
        if preview:
            post.link_preview = preview
            post.save(update_fields=['link_preview'])
            logger.info(f"[LINK_PREVIEW] Attached preview {preview.id} to post {post.share_id}")
        
        return preview
