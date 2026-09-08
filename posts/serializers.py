from rest_framework import serializers
from .models import Post, PostImage, Like, Comment, CommentLike, Report, Repost, HiddenPost, AuthorPreference, SharedPost
from django.contrib.auth import get_user_model
from .tasks import generate_post_thumbnail, generate_video_poster, process_large_video
import logging
import os

logger = logging.getLogger(__name__)

from groups.serializers import GroupSerializer, UserMinimalSerializer
from courses.models import Course, Unit
from notifications.models import NotificationObject
from notifications.notifications.registry import NotificationTypes, NotificationCategories


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'name']


class PostSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="share_id", read_only=True)
    author = UserMinimalSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    unit = UnitSerializer(read_only=True)
    like_count = serializers.ReadOnlyField()
    is_liked = serializers.SerializerMethodField()
    repost_count = serializers.ReadOnlyField()
    is_reposted = serializers.SerializerMethodField()
    repost_of = serializers.PrimaryKeyRelatedField(read_only=True)
    post_id = serializers.IntegerField(source="id", read_only=True)
    share_id = serializers.UUIDField(read_only=True)
    video_status = serializers.CharField(read_only=True)
    video_duration = serializers.IntegerField(read_only=True)
    hls_playlist = serializers.CharField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'post_id', 'share_id', 'author', 'group', 'course', 'unit', 'content',
            'video', 'docs', 'audio', 'gradient_class', 'has_signature',
            'video_status', 'video_duration', 'hls_playlist',
            'created_at', 'updated_at', 'like_count', 'is_liked',
            'repost_count', 'is_reposted', 'repost_of'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at', 'post_id', 'share_id', 'video_status', 'video_duration', 'hls_playlist']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
        return False

    def get_is_reposted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_reposted_by(request.user)
        return False

    def create(self, validated_data):
        request = self.context['request']
        group = validated_data.get('group')
        
        # Check if user is approved member of the group
        if group:
            from groups.models import Membership, MembershipStatus
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                raise serializers.ValidationError(
                    "You must be an approved member to post in this group."
                )
        
        post = Post.objects.create(author=request.user, **validated_data)
        return post


class PostCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="share_id", read_only=True)
    post_id = serializers.IntegerField(source="id", read_only=True)
    share_id = serializers.UUIDField(read_only=True)
    video_status = serializers.CharField(read_only=True)
    """Serializer for creating posts"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )
    custom_gradient_text = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    custom_gradient_color1 = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=7)
    custom_gradient_color2 = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=7)

    class Meta:
        model = Post
        fields = [
            'id', 'post_id', 'share_id', 'author', 'group', 'course', 'unit', 'content',
            'images', 'video', 'docs', 'audio', 'gradient_class', 'has_signature',
            'video_status',
            'custom_gradient_text', 'custom_gradient_color1', 'custom_gradient_color2', 'custom_gradient_text_color'
        ]
        read_only_fields = ['id', 'post_id', 'share_id', 'video_status', 'author']

    def validate_content(self, value):
        if value and len(value) > 2500:
            raise serializers.ValidationError(
                "Post content cannot exceed 2500 characters."
            )
        return value

    def validate_group(self, value):
        request = self.context['request']
        if value:
            from groups.models import Membership, MembershipStatus
            try:
                Membership.objects.get(
                    user=request.user,
                    group=value,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                raise serializers.ValidationError(
                    "You must be an approved member to post in this group."
                )
        return value

    def validate(self, attrs):
        # Ensure post has at least some content
        has_content = bool(attrs.get('content'))
        has_images = bool(attrs.get('images'))
        has_video = bool(attrs.get('video'))
        has_docs = bool(attrs.get('docs'))
        has_audio = bool(attrs.get('audio'))
        
        if not (has_content or has_images or has_video or has_docs or has_audio):
            raise serializers.ValidationError(
                "Post must have at least text content, images, video, documents, or audio."
            )
        return attrs

    def to_internal_value(self, data):
        for key in ('video', 'docs', 'audio'):
            file_obj = data.get(key)
            if hasattr(file_obj, 'name') and file_obj.name and len(file_obj.name) > 200:
                name, ext = os.path.splitext(file_obj.name)
                file_obj.name = f"{name[:180]}{ext}"
        if hasattr(data, 'getlist'):
            for img in data.getlist('images'):
                if hasattr(img, 'name') and img.name and len(img.name) > 200:
                    name, ext = os.path.splitext(img.name)
                    img.name = f"{name[:180]}{ext}"
        return super().to_internal_value(data)

    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        logger.info('[PostCreateSerializer] Starting post creation with validated_data: %s', validated_data)

        images_data = validated_data.pop('images', [])

        has_media = bool(images_data or validated_data.get('video') or validated_data.get('docs') or validated_data.get('audio'))
        if has_media:
            validated_data['gradient_class'] = 'none'
            logger.info('[PostCreateSerializer] Has media, setting gradient_class to none')

        # Validate gradient_class is a valid choice
        from posts.models import GRADIENT_CHOICES
        gradient_choices = [choice[0] for choice in GRADIENT_CHOICES]
        if validated_data.get('gradient_class') not in gradient_choices:
            validated_data['gradient_class'] = 'grad-ocean'  # Default fallback
            logger.warning('[PostCreateSerializer] Invalid gradient_class, defaulting to grad-ocean')

        # Handle custom gradient fields - keep empty strings as empty strings, only convert to None if not provided
        if 'custom_gradient_text' in validated_data:
            validated_data['custom_gradient_text'] = validated_data['custom_gradient_text'] if validated_data['custom_gradient_text'] else None
        if 'custom_gradient_color1' in validated_data:
            validated_data['custom_gradient_color1'] = validated_data['custom_gradient_color1'] if validated_data['custom_gradient_color1'] else None
        if 'custom_gradient_color2' in validated_data:
            validated_data['custom_gradient_color2'] = validated_data['custom_gradient_color2'] if validated_data['custom_gradient_color2'] else None
        if 'custom_gradient_text_color' in validated_data:
            validated_data['custom_gradient_text_color'] = validated_data['custom_gradient_text_color'] if validated_data['custom_gradient_text_color'] else None

        logger.info('[PostCreateSerializer] Custom gradient fields - text: %s, color1: %s, color2: %s, text_color: %s',
                    validated_data.get('custom_gradient_text'),
                    validated_data.get('custom_gradient_color1'),
                    validated_data.get('custom_gradient_color2'),
                    validated_data.get('custom_gradient_text_color'))
        logger.info('[PostCreateSerializer] All validated_data keys: %s', list(validated_data.keys()))

        request = self.context.get('request')
        author = validated_data.get('author') or (request.user if request else None)

        if author:
            validated_data['course'] = getattr(author, 'course', None)
            validated_data['author'] = author
        else:
            logger.error('[PostCreateSerializer] No author found in request or validated_data')
            raise serializers.ValidationError("Author is required to create a post")

        logger.info('[PostCreateSerializer] Creating post with final validated_data')
        post = Post.objects.create(**validated_data)
        logger.info('[PostCreateSerializer] Post created successfully with ID: %s', post.id)

        if post.unit:
            post.course = post.unit.course
            post.save(update_fields=['course'])

        from posts.models import PostImage
        for idx, image_data in enumerate(images_data[:15]):
            PostImage.objects.create(post=post, image=image_data, order=idx)

        logger.info('[PostCreateSerializer] Created %s PostImage objects', len(images_data[:15]))

        # Handle docs upload - integrate with document repo (aligned with document repo pipeline)
        docs_file = validated_data.get('docs')
        if docs_file:
            logger.info('[PostCreateSerializer] Docs file found: %s', docs_file.name if hasattr(docs_file, 'name') else 'Unknown')
            try:
                # Create document in document repo for proper processing
                # This follows the same pattern as documents/views.py upload_document
                from documents.models import Document, DocumentFile, DocumentVersion, DocumentAcademicUnit, DocumentTag, Tag, Category
                from documents.tasks.processing import process_document
                from documents.academic.models import AcademicUnit, Semester, AcademicYear, AcademicLevel
                
                # Get or create default category for post uploads
                default_category, _ = Category.objects.get_or_create(
                    code='other',
                    defaults={'name': 'Other', 'description': 'Documents shared via posts'}
                )
                
                # Generate title from filename (same as document repo)
                title = docs_file.name.replace('.pdf', '').replace('.docx', '').replace('.pptx', '')
                description = f"Shared via post by {author.username}"
                
                # Check if document with same title already exists for this user (same as document repo)
                existing_doc = Document.objects.filter(
                    title=title,
                    uploaded_by=author
                ).first()
                
                if existing_doc:
                    logger.info('[PostCreateSerializer] Document with title "%s" already exists, linking to existing document', title)
                    # Link to existing document instead of creating duplicate (don't set post.docs to avoid duplicate rendering)
                    post.shared_document = existing_doc
                    post.save(update_fields=['shared_document'])
                    
                    # Trigger processing for existing document if needed
                    if existing_doc.status == 'draft' or existing_doc.status == 'processing':
                        logger.info('[PostCreateSerializer] Triggering processing for existing document %s', existing_doc.id)
                        task = process_document.delay(existing_doc.id)
                        logger.info('[PostCreateSerializer] Celery task triggered with ID: %s for existing document %s', task.id, existing_doc.id)
                else:
                    # Create document record (aligned with document repo pipeline)
                    document = Document.objects.create(
                        title=title,
                        description=description,
                        uploaded_by=author,
                        status='processing',  # Start as processing, Celery will update to ready
                        visibility='public',
                        category=default_category
                    )
                    
                    # Create document version (same as document repo)
                    document_version = DocumentVersion.objects.create(
                        document=document,
                        version_number=1,
                        is_latest=True,
                        created_by=author
                    )
                    
                    # Create document file (same as document repo)
                    document_file = DocumentFile.objects.create(
                        document_version=document_version,
                        file=docs_file,
                        original_filename=docs_file.name,
                        size_bytes=docs_file.size,
                        mime_type=docs_file.content_type,
                        extension=docs_file.name.split('.')[-1].lower() if '.' in docs_file.name else '',
                        storage_path=docs_file.name,
                        uploaded_by=author,
                        processing_status='pending',
                        checksum=None  # Will be generated by background processing
                    )
                    
                    # Try to infer academic metadata from user profile and post unit
                    # This bridges the gap between post uploads and document repo metadata
                    try:
                        academic_unit_id = None
                        semester_id = None
                        academic_year_id = None
                        academic_level_id = None
                        
                        # If post has a unit, try to get academic unit from it
                        if post.unit:
                            try:
                                academic_unit = AcademicUnit.objects.filter(unit=post.unit).first()
                                if academic_unit:
                                    academic_unit_id = academic_unit.id
                                    logger.info('[PostCreateSerializer] Found academic unit %s from post unit %s', academic_unit_id, post.unit.id)
                            except Exception as e:
                                logger.warning('[PostCreateSerializer] Could not find academic unit for post unit: %s', e)
                        
                        # Try to infer semester from user's year
                        if hasattr(author, 'year'):
                            try:
                                semester = Semester.objects.filter(name__icontains=str(author.year)).first()
                                if semester:
                                    semester_id = semester.id
                                    logger.info('[PostCreateSerializer] Inferred semester %s from user year %s', semester_id, author.year)
                            except Exception as e:
                                logger.warning('[PostCreateSerializer] Could not infer semester from user year: %s', e)
                        
                        # Try to infer academic year from user's year
                        if hasattr(author, 'year'):
                            try:
                                academic_year = AcademicYear.objects.filter(name__icontains=str(author.year)).first()
                                if academic_year:
                                    academic_year_id = academic_year.id
                                    logger.info('[PostCreateSerializer] Inferred academic year %s from user year %s', academic_year_id, author.year)
                            except Exception as e:
                                logger.warning('[PostCreateSerializer] Could not infer academic year from user year: %s', e)
                        
                        # Try to infer academic level from user's course
                        if hasattr(author, 'course'):
                            try:
                                academic_level = AcademicLevel.objects.filter(name__icontains=str(author.course)).first()
                                if academic_level:
                                    academic_level_id = academic_level.id
                                    logger.info('[PostCreateSerializer] Inferred academic level %s from user course %s', academic_level_id, author.course)
                            except Exception as e:
                                logger.warning('[PostCreateSerializer] Could not infer academic level from user course: %s', e)
                        
                        # Create academic unit relationship if we have enough data
                        if academic_unit_id and semester_id and academic_year_id and academic_level_id:
                            DocumentAcademicUnit.objects.create(
                                document=document,
                                academic_unit_id=academic_unit_id,
                                semester_id=semester_id,
                                academic_year_id=academic_year_id,
                                academic_level_id=academic_level_id,
                                is_primary=True
                            )
                            logger.info('[PostCreateSerializer] Created DocumentAcademicUnit for document %s', document.id)
                        else:
                            logger.info('[PostCreateSerializer] Could not create DocumentAcademicUnit - missing metadata. unit=%s, semester=%s, year=%s, level=%s', 
                                       academic_unit_id, semester_id, academic_year_id, academic_level_id)
                    
                    except Exception as e:
                        # Don't fail document creation if academic metadata inference fails
                        logger.warning('[PostCreateSerializer] Could not infer academic metadata: %s', e)
                    
                    # Add default tag for post-uploaded documents
                    try:
                        post_tag, _ = Tag.objects.get_or_create(
                            name='Post Share',
                            defaults={'slug': 'post-share'}
                        )
                        DocumentTag.objects.create(document=document, tag=post_tag)
                        logger.info('[PostCreateSerializer] Added default tag "Post Share" to document %s', document.id)
                    except Exception as e:
                        logger.warning('[PostCreateSerializer] Could not add default tag: %s', e)
                    
                    # Link post to document (don't set post.docs to avoid duplicate rendering)
                    post.shared_document = document
                    post.save(update_fields=['shared_document'])
                    
                    # Trigger Celery background processing (same as document repo)
                    logger.info('[PostCreateSerializer] About to trigger Celery task for document %s', document.id)
                    task = process_document.delay(document.id)
                    logger.info('[PostCreateSerializer] Celery task triggered with ID: %s for document %s', task.id, document.id)
                    
                    logger.info('[PostCreateSerializer] Document created with ID: %s and linked to post %s', document.id, post.id)
                
            except Exception as e:
                # Log error but don't fail the entire post creation
                logger.error('[PostCreateSerializer] Error creating document from post upload: %s', e)
                import traceback
                logger.error('[PostCreateSerializer] Traceback: %s', traceback.format_exc())
                # Fallback: keep the file reference on post
                logger.info('[PostCreateSerializer] Fallback: Keeping docs file reference on post')

        if author:
            try:
                from users.services.feed_service import invalidate_home_feed_context
                invalidate_home_feed_context(author.id)
            except Exception:
                pass
                

        # Trigger thumbnail generation for gradient/text posts
        if not post.images.exists() and not post.video and not post.shared_document:
            logger.info('[PostCreateSerializer] Triggering thumbnail generation for post %s', post.id)
            generate_post_thumbnail.delay(post.id)
        
        # Trigger HLS transcoding + poster generation for video posts.
        # process_large_video handles: ffprobe → 360p/480p/720p renditions →
        # master.m3u8 → video_status/hls_playlist/video_duration update →
        # real-time progress events over Channels (feed_{user_id} group).
        if post.video:
            logger.info('[PostCreateSerializer] Triggering HLS transcoding for post %s', post.id)
            process_large_video.delay(post.id)
            # Also generate a quick poster from first frame while HLS encodes
            generate_video_poster.delay(post.id)

                
        return post


class PostUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating posts"""
    class Meta:
        model = Post
        fields = ['content', 'video', 'docs', 'audio', 'gradient_class', 'has_signature']

    def to_internal_value(self, data):
        for key in ('video', 'docs', 'audio'):
            file_obj = data.get(key)
            if hasattr(file_obj, 'name') and file_obj.name and len(file_obj.name) > 200:
                name, ext = os.path.splitext(file_obj.name)
                file_obj.name = f"{name[:180]}{ext}"
        return super().to_internal_value(data)


class CommentSerializer(serializers.ModelSerializer):
    author = UserMinimalSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    reply_count = serializers.ReadOnlyField()
    parent_comment_id = serializers.ReadOnlyField(source='parent_comment.id')

    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'created_at', 'like_count', 'is_liked', 'reply_count', 'parent_comment_id']
        read_only_fields = ['author', 'created_at']

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
        return False


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments"""
    class Meta:
        model = Comment
        fields = ['post', 'content']

    def validate_post(self, value):
        request = self.context['request']
        if value.group:
            from groups.models import Membership, MembershipStatus
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=value.group,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                raise serializers.ValidationError(
                    "You must be an approved member to comment on posts in this group."
                )
        return value

    def create(self, validated_data):
        request = self.context['request']
        comment = Comment.objects.create(author=request.user, **validated_data)
        return comment


class ReportSerializer(serializers.ModelSerializer):
    reporter = UserMinimalSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'reporter', 'post', 'reason', 'created_at']
        read_only_fields = ['reporter', 'created_at']

    def create(self, validated_data):
        request = self.context['request']
        report = Report.objects.create(reporter=request.user, **validated_data)
        return report


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reports"""
    class Meta:
        model = Report
        fields = ['post', 'reason', 'description']

    def validate_post(self, value):
        request = self.context['request']
        # Check if user already reported this post
        if Report.objects.filter(reporter=request.user, post=value).exists():
            raise serializers.ValidationError("You have already reported this post.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        report = Report.objects.create(reporter=request.user, **validated_data)
        return report


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'created_at']
        read_only_fields = ['user', 'created_at']


class RepostSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="share_id", read_only=True)
    original_post = PostSerializer(read_only=True)
    reposter = UserMinimalSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    post_count = serializers.ReadOnlyField(source='original_post.like_count')

    class Meta:
        model = Repost
        fields = ['id', 'original_post', 'reposter', 'group', 'content', 'created_at', 'post_count']
        read_only_fields = ['reposter', 'created_at']


class RepostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reposts"""
    class Meta:
        model = Repost
        fields = ['original_post', 'group', 'content']

    def validate_original_post(self, value):
        request = self.context['request']
        if value.author == request.user:
            raise serializers.ValidationError("You cannot repost your own post.")
        return value

    def validate_group(self, value):
        request = self.context['request']
        if value:
            from groups.models import Membership, MembershipStatus
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=value,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                raise serializers.ValidationError(
                    "You must be an approved member to repost to this group."
                )
        return value

    def create(self, validated_data):
        request = self.context['request']
        original_post = validated_data['original_post']
        group = validated_data.get('group')
        
        # Check if already reposted
        if Repost.objects.filter(
            original_post=original_post,
            reposter=request.user,
            group=group
        ).exists():
            raise serializers.ValidationError("You have already reposted this post.")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'[RepostCreateSerializer] Creating repost by {request.user.username} for post {original_post.id}')
        
        repost = Repost.objects.create(reposter=request.user, **validated_data)
        
        logger.info(f'[RepostCreateSerializer] Repost created with ID {repost.id}')
        
        # Emit event directly for notification
        from notifications.events import publish_event, EventTypes, EventSources, EventActions
        
        # Get thumbnail URL for notification preview
        thumbnail_url = None
        if original_post.thumbnail:
            thumbnail_url = original_post.thumbnail.url
        elif original_post.images.exists():
            thumbnail_url = original_post.images.first().get_thumbnail_url('400')
        elif original_post.video_poster:
            thumbnail_url = original_post.video_poster.url
        elif original_post.shared_document:
            try:
                from documents.models import DocumentFile
                if original_post.shared_document.latest_version:
                    first_file = original_post.shared_document.latest_version.files.first()
                    if first_file and first_file.preview_path:
                        thumbnail_url = f"/media/{first_file.preview_path}"
            except:
                pass
        
        logger.info(f'[RepostCreateSerializer] Publishing repost notification event')
        
        publish_event(
            event_type=EventTypes.POSTS_POST_REPOSTED.value,
            source=EventSources.POSTS.value,
            action=EventActions.SHARED.value,
            actor=request.user,
            target_type='Post',
            target_id=str(original_post.id),
            context_type='GROUP' if group else None,
            context_id=str(group.id) if group else None,
            metadata={
                'actor_username': request.user.username,
                'original_post_author_id': original_post.author.id,
                'original_post_author_username': original_post.author.username,
                'repost_content': validated_data.get('content', '')[:100] if validated_data.get('content') else None,
                'thumbnail_url': thumbnail_url,
                'resource_type': 'POST',
                'post_content': original_post.content[:100] if original_post.content else '',
            }
        )
        
        logger.info(f'[RepostCreateSerializer] Repost notification event published')
        
        return repost


class HiddenPostSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    post = PostSerializer(read_only=True)

    class Meta:
        model = HiddenPost
        fields = ['id', 'user', 'post', 'created_at']
        read_only_fields = ['user', 'created_at']


class HiddenPostCreateSerializer(serializers.ModelSerializer):
    """Serializer for hiding posts"""
    class Meta:
        model = HiddenPost
        fields = ['post']

    def create(self, validated_data):
        request = self.context['request']
        post = validated_data['post']
        
        # Check if already hidden
        if HiddenPost.objects.filter(user=request.user, post=post).exists():
            raise serializers.ValidationError("You have already hidden this post.")
        
        hidden_post = HiddenPost.objects.create(user=request.user, **validated_data)
        return hidden_post


class AuthorPreferenceSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    author = UserMinimalSerializer(read_only=True)

    class Meta:
        model = AuthorPreference
        fields = ['id', 'user', 'author', 'preference', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class AuthorPreferenceCreateSerializer(serializers.ModelSerializer):
    """Serializer for setting author preferences"""
    class Meta:
        model = AuthorPreference
        fields = ['author', 'preference']

    def validate_author(self, value):
        request = self.context['request']
        if value == request.user:
            raise serializers.ValidationError("You cannot set preferences for yourself.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        author = validated_data['author']
        preference = validated_data['preference']
        
        # Update or create preference
        preference_obj, created = AuthorPreference.objects.update_or_create(
            user=request.user,
            author=author,
            defaults={'preference': preference}
        )
        return preference_obj


class SharedPostSerializer(serializers.ModelSerializer):
    original_post = PostSerializer(read_only=True)
    sharer = UserMinimalSerializer(read_only=True)
    shared_to = UserMinimalSerializer(read_only=True)
    shared_to_group = GroupSerializer(read_only=True)

    class Meta:
        model = SharedPost
        fields = ['id', 'original_post', 'sharer', 'shared_to', 'shared_to_group', 'message', 'created_at', 'is_viewed']
        read_only_fields = ['sharer', 'created_at', 'is_viewed']


class SharedPostCreateSerializer(serializers.ModelSerializer):
    """Serializer for sharing posts to users or groups"""
    class Meta:
        model = SharedPost
        fields = ['original_post', 'shared_to', 'shared_to_group', 'message']

    def validate(self, attrs):
        request = self.context['request']
        shared_to = attrs.get('shared_to')
        shared_to_group = attrs.get('shared_to_group')
        
        # Ensure either user or group is provided, but not both
        if not shared_to and not shared_to_group:
            raise serializers.ValidationError("You must share to either a user or a group.")
        if shared_to and shared_to_group:
            raise serializers.ValidationError("You can only share to either a user or a group, not both.")
        
        return attrs

    def validate_original_post(self, value):
        request = self.context['request']
        # Check if user can view the post
        if value.group:
            from groups.models import Membership, MembershipStatus
            try:
                Membership.objects.get(
                    user=request.user,
                    group=value.group,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                raise serializers.ValidationError("You cannot share posts from groups you're not a member of.")
        return value

    def validate_shared_to(self, value):
        request = self.context['request']
        if value == request.user:
            raise serializers.ValidationError("You cannot share posts to yourself.")
        return value

    def validate_shared_to_group(self, value):
        request = self.context['request']
        from groups.models import Membership, MembershipStatus
        try:
            Membership.objects.get(
                user=request.user,
                group=value,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            raise serializers.ValidationError("You can only share to groups you're a member of.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        original_post = validated_data['original_post']
        shared_to = validated_data.get('shared_to')
        shared_to_group = validated_data.get('shared_to_group')
        
        # Check if already shared to user
        if shared_to:
            if SharedPost.objects.filter(
                original_post=original_post,
                sharer=request.user,
                shared_to=shared_to
            ).exists():
                raise serializers.ValidationError("You have already shared this post to this user.")
        
        # Check if already shared to group
        if shared_to_group:
            if SharedPost.objects.filter(
                original_post=original_post,
                sharer=request.user,
                shared_to_group=shared_to_group
            ).exists():
                raise serializers.ValidationError("You have already shared this post to this group.")
        
        shared_post = SharedPost.objects.create(sharer=request.user, **validated_data)
        return shared_post
