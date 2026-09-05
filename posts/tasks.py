"""
Celery tasks for background post processing.

This module contains async tasks for handling large media uploads
and post creation in the background with progress tracking.
"""
from celery import shared_task
from celery import current_task
import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template.loader import render_to_string
import sys
import os

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def create_post_with_media(self, user_id, content, unit_id=None, group_id=None, 
                          gradient_class='none', images_data=None, video_data=None, 
                          docs_data=None, audio_data=None):
    """
    Create a post in the background with progress tracking.
    
    Args:
        user_id: ID of the user creating the post
        content: Post content text
        unit_id: Optional unit ID
        group_id: Optional group ID
        gradient_class: Background style class
        images_data: List of image file data
        video_data: Video file data
        docs_data: Document file data
        audio_data: Audio file data
    
    Returns:
        dict: Post creation result with post ID
    """
    from django.contrib.auth import get_user_model
    from posts.models import Post, PostImage
    from courses.models import Unit
    from groups.models import Group
    from io import BytesIO
    from django.core.files.uploadedfile import InMemoryUploadedFile
    import sys
    
    User = get_user_model()
    
    total_steps = 5
    current_step = 0
    
    try:
        # Step 1: Get user and validate
        current_step += 1
        self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': 'Validating user...'})
        user = User.objects.get(id=user_id)
        
        # Step 2: Create post
        current_step += 1
        self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': 'Creating post...'})
        
        post_data = {
            'author': user,
            'content': content,
            'gradient_class': gradient_class,
        }
        
        if unit_id:
            post_data['unit'] = Unit.objects.get(id=unit_id)
        if group_id:
            post_data['group'] = Group.objects.get(id=group_id)
            
        post = Post.objects.create(**post_data)
        
        # Step 3: Process images
        if images_data:
            current_step += 1
            self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': f'Processing {len(images_data)} images...'})
            
            for idx, image_data in enumerate(images_data):
                # Convert base64 or file data to InMemoryUploadedFile
                # This is a simplified version - you'll need to adapt based on your data format
                from PIL import Image
                img = Image.open(BytesIO(image_data))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                if img.height > 1080 or img.width > 1080:
                    img.thumbnail((1080, 1080))
                output = BytesIO()
                img.save(output, format='JPEG', quality=75)
                output.seek(0)
                file_name = f"post_{post.id}_image_{idx}.jpg"
                image_file = InMemoryUploadedFile(
                    output, 'ImageField', file_name,
                    'image/jpeg', sys.getsizeof(output), None
                )
                PostImage.objects.create(post=post, image=image_file, order=idx)
        
        # Step 4: Process video
        if video_data:
            current_step += 1
            self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': 'Processing video...'})
            # Process video file - adapt based on your data format
            post.video = video_data
            post.save()
        
        # Step 5: Process docs/audio
        if docs_data:
            self.update_state(state='PROGRESS', meta={'current': total_steps, 'total': total_steps, 'status': 'Processing document...'})
            post.docs = docs_data
            post.save()
        
        if audio_data:
            self.update_state(state='PROGRESS', meta={'current': total_steps, 'total': total_steps, 'status': 'Processing audio...'})
            post.audio = audio_data
            post.save()
        
        # Final step
        self.update_state(state='SUCCESS', meta={'current': total_steps, 'total': total_steps, 'status': 'Post created successfully!'})
        
        return {
            'post_id': post.id,
            'status': 'success',
            'message': 'Post created successfully'
        }
        
    except Exception as e:
        logger.error(f"Error creating post in background: {e}")
        self.update_state(state='FAILURE', meta={'current': current_step, 'total': total_steps, 'status': f'Error: {str(e)}'})
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_large_video(self, post_id):
    """
    Transcode an uploaded video into multi-bitrate HLS streams.

    Produces up to three renditions (360p / 480p / 720p) depending on
    the source resolution, writes a master playlist, and updates the
    Post model throughout.

    Progress is broadcast over Django Channels to the ``feed_{user_id}``
    group so the persistent upload banner can show live percentages.

    Args:
        post_id: Primary key of the Post whose ``video`` field should be
                 transcoded.
    """
    import subprocess
    import tempfile
    import shutil
    import json as _json
    from django.conf import settings
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from posts.models import Post

    FFMPEG  = '/usr/bin/ffmpeg'
    FFPROBE = '/usr/bin/ffprobe'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _emit(user_id, payload):
        """Send a video.progress message to the user's feed channel group."""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'feed_{user_id}',
                {'type': 'video_progress', **payload},
            )
        except Exception as exc:
            logger.warning('Could not emit video progress for user %s: %s', user_id, exc)

    def _probe(video_path):
        """Return (duration_seconds, width, height) via ffprobe."""
        cmd = [
            FFPROBE, '-v', 'quiet', '-print_format', 'json',
            '-show_streams', video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, check=True)
        info = _json.loads(result.stdout)
        video_stream = next(
            (s for s in info.get('streams', []) if s.get('codec_type') == 'video'),
            {}
        )
        duration = float(video_stream.get('duration', 0) or info.get('format', {}).get('duration', 0))
        width  = int(video_stream.get('width',  0))
        height = int(video_stream.get('height', 0))
        return duration, width, height

    # ------------------------------------------------------------------
    # Rendition ladder: (label, target_height, video_kbps, audio_kbps)
    # Renditions taller than the source are skipped automatically.
    # Higher audio bitrates (128k/160k/192k) prevent metallic/scratchy quantization artifacts.
    # ------------------------------------------------------------------
    RENDITIONS = [
        ('360p',  360,  800, 128),
        ('480p',  480, 1400, 160),
        ('720p',  720, 2800, 192),
    ]

    post = None
    tmp_dir = None
    try:
        post = Post.objects.get(id=post_id)
        user_id = post.author_id

        if not post.video:
            logger.info('[HLS] Post %s has no video, skipping', post_id)
            return

        # Mark as transcoding
        Post.objects.filter(id=post_id).update(video_status=Post.VIDEO_STATUS_TRANSCODING)
        _emit(user_id, {
            'post_id':  post_id,
            'status':   'transcoding',
            'progress': 0,
            'message':  'Starting video transcoding…',
        })

        # ------------------------------------------------------------------
        # Resolve source path (local filesystem or cloud storage download)
        # ------------------------------------------------------------------
        try:
            # Local filesystem — fastest path
            source_path = post.video.path
        except (NotImplementedError, ValueError):
            # Cloud storage: download to a temp file
            tmp_dir = tempfile.mkdtemp(prefix='pwani_hls_')
            ext = os.path.splitext(post.video.name)[1] or '.mp4'
            source_path = os.path.join(tmp_dir, f'source{ext}')
            with post.video.open('rb') as src, open(source_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)

        # Probe source
        duration, src_width, src_height = _probe(source_path)
        logger.info('[HLS] Post %s: duration=%.1fs  %dx%d', post_id, duration, src_width, src_height)

        # Update duration on post
        if duration:
            Post.objects.filter(id=post_id).update(video_duration=int(duration))

        # ------------------------------------------------------------------
        # Prepare output directory
        # ------------------------------------------------------------------
        hls_rel_dir = os.path.join('posts', 'videos', str(post_id), 'hls')
        hls_abs_dir = os.path.join(settings.MEDIA_ROOT, hls_rel_dir)
        os.makedirs(hls_abs_dir, exist_ok=True)

        # ------------------------------------------------------------------
        # Transcode renditions
        # ------------------------------------------------------------------
        produced = []   # list of (label, bandwidth_bps, playlist_rel_path)
        eligible  = [(lbl, h, vk, ak) for lbl, h, vk, ak in RENDITIONS if src_height == 0 or h <= src_height]
        if not eligible:
            eligible = [RENDITIONS[0]]  # always produce at least 360p

        total_steps = len(eligible)
        for step, (label, target_h, video_kbps, audio_kbps) in enumerate(eligible, start=1):
            _emit(user_id, {
                'post_id':  post_id,
                'status':   'transcoding',
                'progress': int((step - 1) / total_steps * 90),
                'message':  f'Encoding {label}…',
            })

            out_dir      = os.path.join(hls_abs_dir, label)
            os.makedirs(out_dir, exist_ok=True)
            playlist_abs = os.path.join(out_dir, 'index.m3u8')
            segment_tmpl = os.path.join(out_dir, 'seg%05d.ts')

            # Scale: keep aspect ratio, height = target_h, force even dims
            vf_scale = f'scale=-2:{target_h}'

            cmd = [
                FFMPEG, '-y',
                '-i', source_path,
                '-vf', vf_scale,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-maxrate', f'{video_kbps}k',
                '-bufsize', f'{video_kbps * 2}k',
                # Audio settings:
                # 1. Higher bitrates (128k+) prevent high-frequency swishing/scratchiness
                # 2. aresample=async=1 synchronizes timestamps across 6s HLS chunks
                # 3. -ar 48000 enforces broadcast-standard audio sample rate
                # 4. -profile:a aac_low ensures universal clean AAC-LC playback
                '-c:a', 'aac',
                '-b:a', f'{audio_kbps}k',
                '-ar', '48000',
                '-ac', '2',
                '-af', 'aresample=async=1:first_pts=0',
                '-profile:a', 'aac_low',
                # HLS muxer options
                '-f', 'hls',
                '-hls_time', '6',
                '-hls_list_size', '0',
                '-hls_segment_filename', segment_tmpl,
                '-hls_flags', 'independent_segments',
                playlist_abs,
            ]

            logger.info('[HLS] Running: %s', ' '.join(cmd))
            proc = subprocess.run(cmd, capture_output=True)

            if proc.returncode != 0:
                stderr_text = proc.stderr.decode('utf-8', errors='replace')
                logger.error('[HLS] FFmpeg failed for %s/%s: %s', post_id, label, stderr_text)
                raise RuntimeError(f'FFmpeg failed for {label}: {stderr_text[-500:]}')

            playlist_rel = os.path.join(hls_rel_dir, label, 'index.m3u8')
            produced.append((label, (video_kbps + audio_kbps) * 1000, playlist_rel))
            logger.info('[HLS] Post %s: %s done', post_id, label)

        # ------------------------------------------------------------------
        # Write master playlist
        # ------------------------------------------------------------------
        master_abs = os.path.join(hls_abs_dir, 'master.m3u8')
        master_rel = os.path.join(hls_rel_dir, 'master.m3u8')

        with open(master_abs, 'w') as f:
            f.write('#EXTM3U\n')
            f.write('#EXT-X-VERSION:3\n')
            for label, bandwidth, playlist_rel in produced:
                # Use a relative URL: ../360p/index.m3u8 etc.
                playlist_name = os.path.join(label, 'index.m3u8')
                f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},NAME="{label}"\n')
                f.write(f'{playlist_name}\n')

        # ------------------------------------------------------------------
        # Upload HLS files to Cloudflare R2 if cloud storage is active
        # ------------------------------------------------------------------
        if getattr(settings, 'USE_S3', False):
            _emit(user_id, {
                'post_id':  post_id,
                'status':   'transcoding',
                'progress': 95,
                'message':  'Uploading video streams to CDN…',
            })
            try:
                import boto3
                r2_cfg = getattr(settings, 'R2_BOTO3_CONFIG', {})
                s3_client = boto3.client('s3', **r2_cfg)
                bucket_name = settings.AWS_STORAGE_BUCKET_NAME

                for root, _, files in os.walk(hls_abs_dir):
                    for fname in files:
                        file_path = os.path.join(root, fname)
                        rel_to_media = os.path.relpath(file_path, settings.MEDIA_ROOT)
                        s3_key = f"media/{rel_to_media.replace(os.sep, '/')}"
                        content_type = 'application/vnd.apple.mpegurl' if fname.endswith('.m3u8') else 'video/mp2t'
                        extra_args = {
                            'ContentType': content_type,
                            'CacheControl': 'max-age=3600' if fname.endswith('.m3u8') else 'max-age=31536000, public',
                        }
                        s3_client.upload_file(file_path, bucket_name, s3_key, ExtraArgs=extra_args)
                logger.info('[HLS] Uploaded all HLS files to R2 bucket %s for post %s', bucket_name, post_id)
            except Exception as r2_err:
                logger.error('[HLS] Failed to upload HLS files to R2 for post %s: %s', post_id, r2_err)
                raise

        # ------------------------------------------------------------------
        # Persist & emit done
        # ------------------------------------------------------------------
        Post.objects.filter(id=post_id).update(
            video_status=Post.VIDEO_STATUS_READY,
            hls_playlist=master_rel,
        )
        final_hls_url = f"{settings.MEDIA_URL.rstrip('/')}/{master_rel.lstrip('/')}"
        _emit(user_id, {
            'post_id':    post_id,
            'status':     'ready',
            'progress':   100,
            'message':    'Video is ready!',
            'hls_url':    final_hls_url,
        })
        logger.info('[HLS] Post %s: all renditions complete → %s', post_id, master_rel)

    except Post.DoesNotExist:
        logger.error('[HLS] Post %s not found', post_id)

    except Exception as exc:
        logger.error('[HLS] Transcoding failed for post %s: %s', post_id, exc, exc_info=True)
        if post:
            Post.objects.filter(id=post_id).update(video_status=Post.VIDEO_STATUS_FAILED)
            try:
                _emit(post.author_id, {
                    'post_id':  post_id,
                    'status':   'failed',
                    'progress': 0,
                    'message':  'Video processing failed.',
                })
            except Exception:
                pass
        raise self.retry(exc=exc)

    finally:
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)



@shared_task
def generate_post_thumbnail_playwright(post_id):
    """
    Generate thumbnail for posts with gradients using Playwright for exact CSS rendering.
    
    This approach uses a headless browser to render the actual HTML/CSS exactly as it appears
    in the feed, capturing gradients, SVG overlays, and text styling with pixel-perfect accuracy.
    
    Args:
        post_id: ID of the post to generate thumbnail for
    """
    from posts.models import Post
    import threading
    
    try:
        post = Post.objects.get(id=post_id)
        
        # Skip if post already has a thumbnail or has images/video
        if post.thumbnail or post.images.exists() or post.video:
            logger.info(f"Post {post_id} already has media or thumbnail, skipping thumbnail generation")
            return
        
        # Render the thumbnail template with post data
        html_content = render_to_string('posts/partials/post_thumbnail.html', {'post': post})
        
        # Use Playwright to capture screenshot in a separate thread to avoid async context issues
        try:
            from playwright.sync_api import sync_playwright
            
            screenshot_result = [None]
            error_result = [None]
            
            def run_playwright():
                try:
                    with sync_playwright() as p:
                        # Try to use system Chrome first, fallback to bundled Chromium
                        try:
                            browser = p.chromium.launch(
                                channel='chrome',  # Use system Chrome
                                args=['--no-sandbox', '--disable-setuid-sandbox'],
                                headless=True
                            )
                        except:
                            # Fallback to bundled Chromium if system Chrome not found
                            browser = p.chromium.launch(
                                args=['--no-sandbox', '--disable-setuid-sandbox'],
                                headless=True
                            )
                        
                        page = browser.new_page(viewport={'width': 800, 'height': 600})
                        
                        # Set the HTML content
                        page.set_content(html_content, wait_until='networkidle')
                        
                        # Take screenshot
                        screenshot_bytes = page.screenshot(
                            type='png',
                            full_page=False,
                            animations='disabled'
                        )
                        
                        browser.close()
                        screenshot_result[0] = screenshot_bytes
                except Exception as e:
                    error_result[0] = e
            
            # Run Playwright in a separate thread
            thread = threading.Thread(target=run_playwright)
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            if thread.is_alive():
                logger.error(f"Playwright thumbnail generation timed out for post {post_id}")
                generate_post_thumbnail_pil(post_id)
                return
            
            if error_result[0]:
                raise error_result[0]
            
            if not screenshot_result[0]:
                logger.error(f"Playwright thumbnail generation failed for post {post_id}: No screenshot generated")
                generate_post_thumbnail_pil(post_id)
                return
            
            # Save screenshot as thumbnail
            output = BytesIO(screenshot_result[0])
            output.seek(0)
            
            file_name = f"post_{post.id}_thumbnail.png"
            post.thumbnail = InMemoryUploadedFile(
                output, 'ImageField', file_name,
                'image/png', sys.getsizeof(output), None
            )
            post.save(update_fields=['thumbnail'])
            
            logger.info(f"Generated Playwright thumbnail for post {post_id}")
                
        except ImportError:
            logger.warning("Playwright not installed, falling back to PIL-based thumbnail generation")
            generate_post_thumbnail_pil(post_id)
        except Exception as e:
            logger.error(f"Playwright thumbnail generation failed for post {post_id}: {e}, falling back to PIL")
            generate_post_thumbnail_pil(post_id)
        
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found for thumbnail generation")
    except Exception as e:
        logger.error(f"Error generating thumbnail for post {post_id}: {e}")


@shared_task
def generate_post_thumbnail_pil(post_id):
    """
    Generate thumbnail for posts with gradients using PIL (fallback method).
    
    This is the legacy PIL-based approach that approximates gradients but doesn't
    capture SVG overlays or exact CSS rendering. Used as fallback when Playwright fails.
    
    Args:
        post_id: ID of the post to generate thumbnail for
    """
    from posts.models import Post
    
    try:
        post = Post.objects.get(id=post_id)
        
        # Skip if post already has a thumbnail or has images/video
        if post.thumbnail or post.images.exists() or post.video:
            logger.info(f"Post {post_id} already has media or thumbnail, skipping thumbnail generation")
            return
        
        # Create thumbnail based on gradient class
        img_width, img_height = 800, 600
        img = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Apply gradient background
        if post.gradient_class != 'none':
            gradient_colors = get_gradient_colors(post.gradient_class, post)
            if gradient_colors:
                draw_gradient(img, gradient_colors[0], gradient_colors[1])
        
        # Add text content
        if post.content:
            try:
                # Try to use a default font
                font_size = 32
                try:
                    # Try to load a system font
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                
                # Wrap text to fit width
                text = post.content[:200]  # Limit text length
                lines = wrap_text(text, font, img_width - 40)
                
                # Draw text
                y_offset = 50
                text_color = get_text_color(post)
                for line in lines[:5]:  # Max 5 lines
                    draw.text((20, y_offset), line, font=font, fill=text_color)
                    y_offset += font_size + 10
            except Exception as e:
                logger.warning(f"Could not render text on thumbnail: {e}")
        
        # Save thumbnail
        output = BytesIO()
        img.save(output, format='WEBP', quality=80, method=6)
        output.seek(0)
        
        file_name = f"post_{post.id}_thumbnail.webp"
        post.thumbnail = InMemoryUploadedFile(
            output, 'ImageField', file_name,
            'image/webp', sys.getsizeof(output), None
        )
        post.save(update_fields=['thumbnail'])
        
        logger.info(f"Generated PIL thumbnail for post {post_id}")
        
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found for thumbnail generation")
    except Exception as e:
        logger.error(f"Error generating thumbnail for post {post_id}: {e}")


@shared_task
def generate_post_thumbnail(post_id):
    """
    Generate thumbnail for posts with gradients, text, or other non-media content.
    
    This is the main entry point that uses Playwright for exact CSS rendering
    with PIL as fallback.
    
    Args:
        post_id: ID of the post to generate thumbnail for
    """
    generate_post_thumbnail_playwright(post_id)


@shared_task
def generate_video_poster(post_id):
    """
    Generate video poster image from video file to prevent black screen.
    
    Args:
        post_id: ID of the post with video
    """
    from posts.models import Post
    
    try:
        post = Post.objects.get(id=post_id)
        
        if not post.video or post.video_poster:
            logger.info(f"Post {post_id} has no video or already has poster, skipping")
            return
        
        import subprocess
        import tempfile
        import shutil
        from django.conf import settings

        tmp_video_path = None
        try:
            video_path = post.video.path
        except (NotImplementedError, ValueError, AttributeError):
            # Cloud storage: download to temporary file
            ext = os.path.splitext(post.video.name)[1] or '.mp4'
            tmp_fd, tmp_video_path = tempfile.mkstemp(prefix=f'poster_{post.id}_', suffix=ext)
            os.close(tmp_fd)
            with post.video.open('rb') as src, open(tmp_video_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)
            video_path = tmp_video_path

        poster_path = os.path.join(settings.MEDIA_ROOT, 'posts/videos/posters', f"post_{post.id}_poster.jpg")

        # Ensure directory exists
        os.makedirs(os.path.dirname(poster_path), exist_ok=True)

        # Use ffmpeg to extract first frame as poster
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vframes', '1',
                '-vf', 'scale=800:-1',
                '-y',
                poster_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            # Update post with poster (uses Django storage backend, saves to R2 automatically if USE_S3=1)
            with open(poster_path, 'rb') as f:
                post.video_poster.save(f"post_{post.id}_poster.jpg", f, save=True)

            logger.info(f"Generated video poster for post {post_id}")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error for post {post_id}: {e.stderr.decode() if e.stderr else str(e)}")
        except FileNotFoundError:
            logger.warning("FFmpeg not found, skipping video poster generation")
        finally:
            if tmp_video_path and os.path.exists(tmp_video_path):
                try:
                    os.remove(tmp_video_path)
                except Exception:
                    pass

            logger.warning("FFmpeg not found, skipping video poster generation")
            
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found for video poster generation")
    except Exception as e:
        logger.error(f"Error generating video poster for post {post_id}: {e}")


def get_gradient_colors(gradient_class, post):
    """Get gradient colors based on gradient class"""
    # Default colors for predefined gradients
    gradient_map = {
        'grad-ocean': ['#1e3c72', '#2a5298'],
        'grad-forest': ['#134e5e', '#71b280'],
        'grad-magma': ['#833ab4', '#fd1d1d'],
        'grad-midnight': ['#0f0c29', '#302b63'],
        'grad-desert': ['#f2994a', '#f2c94c'],
        'grad-stealth': ['#232526', '#414345'],
    }
    
    if gradient_class in gradient_map:
        return gradient_map[gradient_class]
    elif gradient_class == 'bg-username-pattern' and post.custom_gradient_color1 and post.custom_gradient_color2:
        return [post.custom_gradient_color1, post.custom_gradient_color2]
    else:
        return ['#1e3c72', '#2a5298']  # Default ocean


def draw_gradient(img, color1, color2):
    """Draw gradient on image"""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    
    # Parse hex colors
    c1 = tuple(int(color1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    c2 = tuple(int(color2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    # Simple vertical gradient
    for y in range(height):
        ratio = y / height
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def get_text_color(post):
    """Get text color based on gradient or custom setting"""
    if post.custom_gradient_text_color:
        return tuple(int(post.custom_gradient_text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    # Default white text for dark gradients
    return (255, 255, 255)
