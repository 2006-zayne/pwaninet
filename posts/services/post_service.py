from django.shortcuts import get_object_or_404
from django.db import transaction
from groups.models import Group, Membership, MembershipStatus
from posts.models import Like, Post, PostImage
from users.models import User
from notifications.models import NotificationObject
from users.services.feed_service import invalidate_home_feed_context
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def create_post_for_user(form, user, files, group_id=None):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"create_post_for_user called. files: {files}, group_id: {group_id}")
    logger.info(f"files keys: {list(files.keys()) if files else 'None'}")
    
    with transaction.atomic():
        post = form.save(commit=False)

        post.author = user
        post.course = user.course
        post.year = user.year

        # Group handling from POST data
        if group_id:
            post.group = get_object_or_404(Group, id=group_id)
            logger.info(f"Group set from group_id: {group_id}")
        else:
            post.group = None
            logger.info("No group selected, post will be global")
        
        # Unit override
        if post.unit:
            post.course = post.unit.course

        # Check if any media is being uploaded and set gradient to 'none'
        has_media = False
        if files:
            if 'images' in files and files.getlist('images'):
                has_media = True
            if 'video' in files and files.get('video'):
                has_media = True
            if 'docs' in files and files.get('docs'):
                has_media = True
            if 'audio' in files and files.get('audio'):
                has_media = True
        
        if has_media:
            post.gradient_class = 'none'
            logger.info(f"Media detected, setting gradient_class to 'none'")

        post.save()
        logger.info(f"Post saved with ID: {post.id}, gradient_class: {post.gradient_class}, group: {post.group}")

        # Handle multiple image uploads
        if files and 'images' in files:
            images = files.getlist('images')
            logger.info(f"Processing {len(images)} images")
            for idx, image_file in enumerate(images[:15]):  # Max 15 images
                logger.info(f"Creating PostImage {idx}: {image_file.name}")
                PostImage.objects.create(
                    post=post,
                    image=image_file,
                    order=idx
                )
            logger.info(f"Finished creating PostImage objects. Total: {post.images.count()}")
        else:
            logger.info("No images found in files")

        # Handle audio upload
        if files and 'audio' in files:
            audio_file = files.get('audio')
            logger.info(f"Audio file found: {audio_file.name if audio_file else 'None'}")
            if audio_file and hasattr(audio_file, 'name') and audio_file.name:
                try:
                    post.audio = audio_file
                    post.save()
                    logger.info(f"Audio saved successfully: {post.audio}")
                except Exception as e:
                    # Log error but don't fail the entire post creation
                    logger.error(f"Error saving audio file: {e}")
                    pass

        # Handle video upload
        if files and 'video' in files:
            video_file = files.get('video')
            logger.info(f"Video file found: {video_file.name if video_file else 'None'}")
            if video_file and hasattr(video_file, 'name') and video_file.name:
                try:
                    post.video = video_file
                    post.save()
                    logger.info(f"Video saved successfully: {post.video}")
                except Exception as e:
                    # Log error but don't fail the entire post creation
                    logger.error(f"Error saving video file: {e}")
                    pass

        # Handle docs upload - integrate with document repo (aligned with document repo pipeline)
        if files and 'docs' in files:
            docs_file = files.get('docs')
            logger.info(f"Docs file found: {docs_file.name if docs_file else 'None'}")
            if docs_file and hasattr(docs_file, 'name') and docs_file.name:
                try:
                    # Create document in document repo for proper processing
                    # This follows the same pattern as documents/views.py upload_document
                    from documents.models import Document, DocumentFile, DocumentVersion, Category
                    from documents.tasks.processing import process_document
                    
                    # Get or create default category for post uploads
                    default_category, _ = Category.objects.get_or_create(
                        code='other',
                        defaults={'name': 'Other', 'description': 'Documents shared via posts'}
                    )
                    
                    # Generate title from filename (same as document repo)
                    title = docs_file.name.replace('.pdf', '').replace('.docx', '').replace('.pptx', '')
                    description = f"Shared via post by {user.username}"
                    
                    # Check if document with same title already exists for this user (same as document repo)
                    existing_doc = Document.objects.filter(
                        title=title,
                        uploaded_by=user
                    ).first()
                    
                    if existing_doc:
                        logger.info(f"Document with title '{title}' already exists, linking to existing document")
                        # Link to existing document instead of creating duplicate
                        post.shared_document = existing_doc
                        post.docs = docs_file  # Keep the file reference for backward compatibility
                        post.save()
                        
                        # Trigger processing for existing document if needed
                        if existing_doc.status == 'draft' or existing_doc.status == 'processing':
                            logger.info(f"Triggering processing for existing document {existing_doc.id}")
                            task = process_document.delay(existing_doc.id)
                            logger.info(f"Celery task triggered with ID: {task.id} for existing document {existing_doc.id}")
                    else:
                        # Create document record (aligned with document repo pipeline)
                        document = Document.objects.create(
                            title=title,
                            description=description,
                            uploaded_by=user,
                            status='processing',  # Start as processing, Celery will update to ready
                            visibility='public',
                            category=default_category
                        )
                        
                        # Create document version (same as document repo)
                        document_version = DocumentVersion.objects.create(
                            document=document,
                            version_number=1,
                            is_latest=True,
                            created_by=user
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
                            uploaded_by=user,
                            processing_status='pending',
                            checksum=None  # Will be generated by background processing
                        )
                        
                        # Link post to document
                        post.shared_document = document
                        post.docs = docs_file  # Keep the file reference for backward compatibility
                        post.save()
                        
                        # Trigger Celery background processing (same as document repo)
                        logger.info(f"About to trigger Celery task for document {document.id}")
                        task = process_document.delay(document.id)
                        logger.info(f"Celery task triggered with ID: {task.id} for document {document.id}")
                        
                        logger.info(f"Document created with ID: {document.id} and linked to post {post.id}")
                    
                except Exception as e:
                    # Log error but don't fail the entire post creation
                    logger.error(f"Error creating document from post upload: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Fallback to old behavior if document creation fails
                    try:
                        post.docs = docs_file
                        post.save()
                        logger.info(f"Fallback: Docs saved directly to post: {post.docs}")
                    except Exception as fallback_error:
                        logger.error(f"Error in fallback doc save: {fallback_error}")
                        pass

    logger.info(f"Final post state - images: {post.images.count()}, video: {post.video.name if post.video else 'None'}, docs: {post.docs.name if post.docs else 'None'}, audio: {post.audio.name if post.audio else 'None'}, gradient_class: {post.gradient_class}, group: {post.group}")
    logger.info(f"get_intel_file returns: {post.get_intel_file.url if post.get_intel_file else 'None'}")
    
    # Invalidate feeds (outside transaction)
    invalidate_home_feed_context(user.id)

    # Notifications (outside transaction)
    if post.group:
        recipients = User.objects.filter(
            group_memberships__group=post.group,
            group_memberships__status=MembershipStatus.APPROVED
        ).exclude(id=user.id)
        msg_text = f"posted in the {post.group.name} squad."
    else:
        recipients = User.objects.filter(
            course=user.course,
            year=user.year
        ).exclude(id=user.id)
        msg_text = "posted a new update in the global feed."

    Notifications.objects.bulk_create([
        Notifications(
            recipient=recipient,
            sender=user,
            post=post,
            notification_type=Notifications.ALERTE,
            msg=msg_text,
        )
        for recipient in recipients
    ])
    
    return post
   

@transaction.atomic


def toggle_post_like_for_user(post, user):
    like_qs = Like.objects.filter(user=user, post=post)

    if like_qs.exists():
        like_qs.delete()
        is_liked = False
    else:
        Like.objects.create(user=user, post=post)
        is_liked = True

    invalidate_home_feed_context(user.id)

    if post.author_id != user.id:
        invalidate_home_feed_context(post.author_id)
    
    # Broadcast like update via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "feed_updates",
        {
            'type': 'post_like_update',
            'post_id': post.id,
            'like_count': post.likes.count(),
            'is_liked': is_liked,
            'user_id': user.id
        }
    )

    return {
        "post": post,
        "is_liked": is_liked,
        "like_count": post.likes.count()
    }