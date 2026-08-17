from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from celery.result import AsyncResult

from .models import Post, Comment, Report, Like, Repost, HiddenPost, AuthorPreference, SharedPost, PostImage, PostImageLike, PostImageComment
from .serializers import (
    PostSerializer, PostCreateSerializer, PostUpdateSerializer,
    CommentSerializer, CommentCreateSerializer, ReportCreateSerializer,
    ReportSerializer, RepostSerializer, RepostCreateSerializer,
    HiddenPostSerializer, HiddenPostCreateSerializer,
    AuthorPreferenceSerializer, AuthorPreferenceCreateSerializer,
    SharedPostSerializer, SharedPostCreateSerializer
)
from .permissions import CanDeletePost, CanEditPost, IsPostAuthorOrReadOnly
from groups.permissions import IsApprovedMember
from courses.models import Unit
from users.models import User
from posts.forms import PostForm
from posts.services.comment_service import build_comments_context, handle_add_comment_request, toggle_comment_like_for_user, add_comment_to_image
from posts.services.feed_service import build_home_feed_context
from posts.services.post_service import toggle_post_like_for_user, create_post_for_user
from posts.services.repost_service import create_repost, delete_repost, get_post_reposts
from posts.services.hide_service import hide_post, unhide_post, is_post_hidden
from posts.services.author_preference_service import set_author_preference, get_author_preference, get_all_preferences
from posts.services.share_service import share_post, get_shared_posts, mark_share_as_viewed, get_user_received_shares
from notifications.services.notification_service import get_cached_unread_count


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing posts.
    """
    permission_classes = [IsAuthenticated]
    queryset = Post.objects.select_related('author', 'group', 'course', 'unit').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return PostCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PostUpdateSerializer
        return PostSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), CanDeletePost()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), CanEditPost()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        logger.info('[PostViewSet.create] Starting post creation')
        logger.info('[PostViewSet.create] Request data: %s', request.data)
        logger.info('[PostViewSet.create] Request files: %s', request.FILES)
        logger.info('[PostViewSet.create] Custom gradient fields: custom_gradient_text=%s, custom_gradient_color1=%s, custom_gradient_color2=%s, custom_gradient_text_color=%s',
                    request.data.get('custom_gradient_text'),
                    request.data.get('custom_gradient_color1'),
                    request.data.get('custom_gradient_color2'),
                    request.data.get('custom_gradient_text_color'))

        try:
            response = super().create(request, *args, **kwargs)
            logger.info('[PostViewSet.create] Post created successfully')
            logger.info('[PostViewSet.create] Response data: %s', response.data)
            # Mark this as a new post in session for back button logic
            request.session['is_new_post'] = True
            post_id = response.data.get('id') or response.data.get('pk')
            if post_id:
                request.session['new_post_id'] = post_id
                logger.info('[PostViewSet.create] Session flags set for new post ID: %s', post_id)
            else:
                logger.warning('[PostViewSet.create] No post ID found in response data')
            return response
        except Exception as e:
            logger.error('[PostViewSet.create] Error during post creation: %s', str(e))
            logger.error('[PostViewSet.create] Error type: %s', type(e).__name__)
            import traceback
            logger.error('[PostViewSet.create] Traceback: %s', traceback.format_exc())
            raise

    @action(detail=True, methods=['post'], url_path='report')
    def report(self, request, pk=None):
        """
        POST /posts/{id}/report/
        Report a post.
        """
        post = self.get_object()
        
        # Check if user already reported this post
        if Report.objects.filter(reporter=request.user, post=post).exists():
            return Response(
                {'detail': 'You have already reported this post.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ReportCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post)
        
        return Response(
            ReportSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        """
        POST /posts/{id}/like/
        Like a post.
        """
        post = self.get_object()
        
        # Check if user is approved member of the group
        if post.group:
            from groups.models import Membership, MembershipStatus
            try:
                Membership.objects.get(
                    user=request.user,
                    group=post.group,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                return Response(
                    {'detail': 'You must be an approved member to like posts in this group.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if created:
            return Response(
                {'detail': 'Post liked.'},
                status=status.HTTP_201_CREATED
            )
        else:
            like.delete()
            return Response(
                {'detail': 'Post unliked.'},
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=['post'], url_path='images/(?P<image_id>[^/.]+)/like')
    def image_like(self, request, pk=None, image_id=None):
        """
        POST /posts/{id}/images/{image_id}/like/
        Like or unlike a specific post image.
        """
        post = self.get_object()
        
        try:
            post_image = post.images.get(id=image_id)
        except PostImage.DoesNotExist:
            return Response(
                {'detail': 'Image not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is approved member of the group
        if post.group:
            from groups.models import Membership, MembershipStatus
            try:
                Membership.objects.get(
                    user=request.user,
                    group=post.group,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                return Response(
                    {'detail': 'You must be an approved member to like images in this group.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        like, created = PostImageLike.objects.get_or_create(
            user=request.user,
            post_image=post_image
        )
        
        likes_count = post_image.likes.count()
        
        if created:
            return Response(
                {'detail': 'Image liked.', 'likes_count': likes_count},
                status=status.HTTP_201_CREATED
            )
        else:
            like.delete()
            return Response(
                {'detail': 'Image unliked.', 'likes_count': likes_count},
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=['get', 'post'], url_path='images/(?P<image_id>[^/.]+)/comments')
    def image_comments(self, request, pk=None, image_id=None):
        """
        GET /posts/{id}/images/{image_id}/comments/
        List all comments for a specific post image.
        
        POST /posts/{id}/images/{image_id}/comments/
        Create a new comment for a specific post image.
        """
        post = self.get_object()
        
        try:
            post_image = post.images.get(id=image_id)
        except PostImage.DoesNotExist:
            return Response(
                {'detail': 'Image not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if request.method == 'GET':
            comments = post_image.comments.select_related('author').all()
            
            # Format comments for response
            comments_data = []
            for comment in comments:
                comments_data.append({
                    'id': comment.id,
                    'content': comment.content,
                    'author': {
                        'id': comment.author.id,
                        'username': comment.author.username,
                        'profile_pic': comment.author.profile_pic.url if comment.author.profile_pic else None
                    },
                    'created_at': comment.created_at.strftime('%B %d, %Y at %I:%M %p')
                })
            
            return Response({
                'comments': comments_data,
                'total_count': len(comments_data)
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            content = request.data.get('content', '').strip()
            
            if not content:
                return Response(
                    {'detail': 'Comment content is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user is approved member of the group
            if post.group:
                from groups.models import Membership, MembershipStatus
                try:
                    Membership.objects.get(
                        user=request.user,
                        group=post.group,
                        status=MembershipStatus.APPROVED
                    )
                except Membership.DoesNotExist:
                    return Response(
                        {'detail': 'You must be an approved member to comment on images in this group.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Use the service function to add comment (mirrors post comment functionality)
            comment = add_comment_to_image(post_image, request.user, content)
            
            if not comment:
                return Response(
                    {'detail': 'Failed to add comment.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'id': comment.id,
                'content': comment.content,
                'author': {
                    'id': comment.author.id,
                    'username': comment.author.username,
                    'full_name': comment.author.get_full_name(),
                    'profile_pic': comment.author.profile_pic.url if comment.author.profile_pic else None
                },
                'created_at': comment.created_at.strftime('%B %d, %Y at %I:%M %p')
            }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='comments')
    def comments(self, request, pk=None):
        """
        GET /posts/{id}/comments/
        List all comments for a post.
        """
        post = self.get_object()
        comments = post.comments.all()
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='repost')
    def repost(self, request, pk=None):
        """
        POST /posts/{id}/repost/
        Repost a post by creating a new post that references the original.
        """
        original_post = self.get_object()
        content = request.data.get('content', '')

        # Create a new post as a repost
        repost = Post.objects.create(
            author=request.user,
            content=content,
            group=original_post.group,
            course=original_post.course,
            unit=original_post.unit,
            video=original_post.video,
            docs=original_post.docs,
            gradient_class=original_post.gradient_class,
            repost_of=original_post
        )

        # Copy images from original post
        for image in original_post.images.all():
            from posts.models import PostImage
            PostImage.objects.create(post=repost, image=image.image)

        return Response(
            PostSerializer(repost, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='repost')
    def delete_repost(self, request, pk=None):
        """
        DELETE /posts/{id}/repost/
        Delete a repost (delete the reposted post).
        """
        post = self.get_object()

        # Only allow deleting if this is a repost and the user is the reposter
        if not post.repost_of:
            return Response(
                {'detail': 'This is not a repost.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if post.author != request.user:
            return Response(
                {'detail': 'You can only delete your own reposts.'},
                status=status.HTTP_403_FORBIDDEN
            )

        post.delete()
        return Response(
            {'detail': 'Repost deleted.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], url_path='reposts')
    def reposts(self, request, pk=None):
        """
        GET /posts/{id}/reposts/
        List all reposts of a post.
        """
        post = self.get_object()
        reposts = get_post_reposts(post)
        serializer = RepostSerializer(reposts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='hide')
    def hide(self, request, pk=None):
        """
        POST /posts/{id}/hide/
        Hide a post from feed.
        """
        post = self.get_object()
        try:
            hidden_post = hide_post(request.user, post)
            return Response(
                {'detail': 'Post hidden successfully.'},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'], url_path='hide')
    def unhide(self, request, pk=None):
        """
        DELETE /posts/{id}/hide/
        Unhide a post.
        """
        post = self.get_object()
        unhidden = unhide_post(request.user, post)
        if unhidden:
            return Response(
                {'detail': 'Post unhidden.'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'detail': 'Post was not hidden.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='share')
    def share(self, request, pk=None):
        """
        POST /posts/{id}/share/
        Share a post to multiple users or groups.
        Accepts either direct IDs (shared_to, shared_to_group) or lookups (shared_to_usernames, shared_to_group_ids).
        For bulk sharing, use comma-separated values in shared_to_usernames or shared_to_group_ids.
        """
        post = self.get_object()
        share_data = request.data.copy()
        message = share_data.get('message', '')
        
        # Handle bulk user sharing
        if 'shared_to_usernames' in share_data:
            usernames_str = share_data['shared_to_usernames']
            usernames = [u.strip() for u in str(usernames_str).split(',') if u.strip()]
            
            shared_posts = []
            errors = []
            
            for username in usernames:
                try:
                    user = User.objects.get(username=username)
                    shared_post = share_post(request.user, post, shared_to_user=user, message=message)
                    shared_posts.append(shared_post)
                except User.DoesNotExist:
                    errors.append(f'User {username} not found')
                except Exception as e:
                    errors.append(f'Error sharing to {username}: {str(e)}')
            
            if shared_posts:
                return Response({
                    'detail': f'Shared to {len(shared_posts)} user(s) successfully.',
                    'shared_posts': SharedPostSerializer(shared_posts, many=True, context={'request': request}).data,
                    'errors': errors if errors else None
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'detail': 'No successful shares.', 'errors': errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Handle bulk group sharing
        elif 'shared_to_group_ids' in share_data:
            group_ids_str = share_data['shared_to_group_ids']
            group_ids = [g.strip() for g in str(group_ids_str).split(',') if g.strip()]
            
            shared_posts = []
            errors = []
            
            from groups.models import Group
            for group_id in group_ids:
                try:
                    group = Group.objects.get(id=group_id)
                    shared_post = share_post(request.user, post, shared_to_group=group, message=message)
                    shared_posts.append(shared_post)
                except Group.DoesNotExist:
                    errors.append(f'Group {group_id} not found')
                except Exception as e:
                    errors.append(f'Error sharing to group {group_id}: {str(e)}')
            
            if shared_posts:
                return Response({
                    'detail': f'Shared to {len(shared_posts)} group(s) successfully.',
                    'shared_posts': SharedPostSerializer(shared_posts, many=True, context={'request': request}).data,
                    'errors': errors if errors else None
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'detail': 'No successful shares.', 'errors': errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Handle single user/group sharing (backward compatibility)
        else:
            # If username is provided, look up the user ID
            if 'shared_to_username' in share_data and not share_data.get('shared_to'):
                try:
                    user = User.objects.get(username=share_data['shared_to_username'])
                    share_data['shared_to'] = user.id
                    del share_data['shared_to_username']
                except User.DoesNotExist:
                    return Response(
                        {'detail': 'User not found.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # If group_id is provided, look up the group
            if 'shared_to_group_id' in share_data and not share_data.get('shared_to_group'):
                from groups.models import Group
                try:
                    group = Group.objects.get(id=share_data['shared_to_group_id'])
                    share_data['shared_to_group'] = group.id
                    del share_data['shared_to_group_id']
                except Group.DoesNotExist:
                    return Response(
                        {'detail': 'Group not found.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            serializer = SharedPostCreateSerializer(
                data=share_data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(original_post=post)
            
            return Response(
                SharedPostSerializer(serializer.instance, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def get_queryset(self):
        # Only filter for top-level comments on list actions
        if self.action == 'list':
            return Comment.objects.select_related('author', 'post').filter(parent_comment__isnull=True)
        # For detail actions (retrieve, update, delete, custom actions), include all comments
        return Comment.objects.select_related('author', 'post')

    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        
        # Broadcast new comment via WebSocket for real-time updates
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        # Broadcast to post author's feed
        if comment.post.author.id != self.request.user.id:
            async_to_sync(channel_layer.group_send)(
                f"feed_{comment.post.author.id}",
                {
                    'type': 'feed_update',
                    'post': {
                        'id': comment.post.id,
                        'comment': {
                            'id': comment.id,
                            'content': comment.content,
                            'author': {
                                'id': comment.author.id,
                                'username': comment.author.username,
                                'profile_pic': comment.author.profile_pic.url if comment.author.profile_pic else None
                            },
                            'created_at': comment.created_at.isoformat()
                        }
                    }
                }
            )

    @action(detail=True, methods=['post'], url_path='reply')
    def reply(self, request, pk=None):
        """
        POST /comments/{id}/reply/
        Create a reply to a comment.
        """
        parent_comment = self.get_object()
        content = request.data.get('content', '').strip()
        
        if not content:
            return Response(
                {'detail': 'Reply content cannot be empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user can comment on the post (group membership check)
        if parent_comment.post.group:
            from groups.models import Membership, MembershipStatus
            try:
                Membership.objects.get(
                    user=request.user,
                    group=parent_comment.post.group,
                    status=MembershipStatus.APPROVED
                )
            except Membership.DoesNotExist:
                return Response(
                    {'detail': 'You must be an approved member to comment on posts in this group.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Create the reply using the service
        from posts.services.comment_service import add_comment_to_post
        reply = add_comment_to_post(
            parent_comment.post,
            request.user,
            content,
            parent_comment=parent_comment
        )
        
        serializer = CommentSerializer(reply, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        """
        POST /comments/{id}/like/
        Toggle like on a comment.
        """
        comment = self.get_object()
        from posts.services.comment_service import toggle_comment_like_for_user
        result = toggle_comment_like_for_user(comment, request.user)
        
        if result['comment'].is_liked_by(request.user):
            return Response(
                {'detail': 'Comment liked.', 'likes_count': comment.likes.count()},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'detail': 'Comment unliked.', 'likes_count': comment.likes.count()},
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=['get'], url_path='replies')
    def replies(self, request, pk=None):
        """
        GET /comments/{id}/replies/
        List direct replies to a comment.
        """
        parent_comment = self.get_object()
        replies = parent_comment.replies.select_related('author').order_by('created_at')
        
        # Pagination
        page = self.paginate_queryset(replies)
        if page is not None:
            serializer = CommentSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = CommentSerializer(replies, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reports.
    """
    permission_classes = [IsAuthenticated]
    queryset = Report.objects.select_related('reporter', 'post').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ReportCreateSerializer
        return ReportSerializer

    def get_queryset(self):
        # Only allow admins to see reports
        user = self.request.user
        from groups.models import Membership, MembershipRole, MembershipStatus

        # Get all groups where user is admin or moderator
        admin_groups = Membership.objects.filter(
            user=user,
            role__in=[MembershipRole.ADMIN, MembershipRole.MODERATOR],
            status=MembershipStatus.APPROVED
        ).values_list('group_id', flat=True)

        # Filter reports for posts in those groups
        return self.queryset.filter(post__group_id__in=admin_groups)

    def perform_create(self, serializer):
        # Save the report
        report = serializer.save(reporter=self.request.user)

        # Send notification to group admins/moderators
        if report.post.group:
            from groups.models import Membership, MembershipRole, MembershipStatus
            from notifications.events import publish_event, EventTypes, EventSources, EventActions

            # Get all admins and moderators of the group
            officials = Membership.objects.filter(
                group=report.post.group,
                role__in=[MembershipRole.ADMIN, MembershipRole.MODERATOR],
                status=MembershipStatus.APPROVED
            ).exclude(user=report.reporter)

            # Emit event for each official - the rules engine will create notifications
            for membership in officials:
                publish_event(
                    event_type=EventTypes.POSTS_POST_REPORTED.value,
                    source=EventSources.POSTS.value,
                    action=EventActions.REPORTED.value,
                    actor=report.reporter,
                    target_type='Post',
                    target_id=str(report.post.id),
                    context_type='GROUP',
                    context_id=str(report.post.group.id),
                    audience=str(membership.user.id),
                    metadata={
                        'report_reason': report.reason,
                        'reporter_username': report.reporter.username,
                        'post_content': report.post.content[:100] if report.post.content else '',
                        'resource_type': 'POST',
                    }
                )


class AuthorPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing author preferences.
    """
    permission_classes = [IsAuthenticated]
    queryset = AuthorPreference.objects.select_related('user', 'author').all()
    serializer_class = AuthorPreferenceSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return AuthorPreferenceCreateSerializer
        return AuthorPreferenceSerializer

    def get_queryset(self):
        # Only show current user's preferences
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SharedPostViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing shared posts.
    """
    permission_classes = [IsAuthenticated]
    queryset = SharedPost.objects.select_related('original_post', 'sharer', 'shared_to').all()
    serializer_class = SharedPostSerializer

    def get_queryset(self):
        # Only show posts shared to current user
        return self.queryset.filter(shared_to=self.request.user)

    @action(detail=True, methods=['post'], url_path='view')
    def mark_viewed(self, request, pk=None):
        """
        POST /shared-posts/{id}/view/
        Mark a shared post as viewed.
        """
        shared_post = self.get_object()
        marked = mark_share_as_viewed(shared_post.id)
        if marked:
            return Response(
                {'detail': 'Shared post marked as viewed.'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'detail': 'Shared post not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# DJANGO WEB VIEWS
# ============================================================================

@login_required
def home_view(request):
    cursor = request.GET.get('cursor')
    context = build_home_feed_context(request.user, cursor=cursor)
    
    # Only add explore_groups on initial page load (no cursor, not HTMX pagination)
    is_initial_load = cursor is None and not request.headers.get('HX-Request')
    if is_initial_load:
        from groups.models import Group, Membership, MembershipStatus
        user_group_ids = set(Group.objects.filter(
            memberships__user=request.user,
            memberships__status=MembershipStatus.APPROVED
        ).values_list('id', flat=True))
        explore_groups = Group.objects.exclude(id__in=user_group_ids).order_by('-created_at')[:8]
        context['explore_groups'] = explore_groups
    
    # If HTMX requests the home feed (e.g. when clearing search), return the inner content
    if request.headers.get('HX-Request') and not request.GET.get('q'):
        return render(request, 'posts/partials/home_content.html', context)

    # For HTMX infinite scroll: render only the posts partial
    if request.headers.get('HX-Request'):
        return render(request, 'posts/partials/post_list.html', context)

    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    return render(request, 'posts/home.html', context)


@login_required
def create_post_view(request):
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user's groups for the dropdown
    from groups.models import Group, Membership, MembershipStatus
    user_groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__status=MembershipStatus.APPROVED
    ).distinct()
    
    if request.method == 'POST':
        logger.info(f"POST request received. FILES keys: {list(request.FILES.keys())}")
        logger.info(f"POST data keys: {list(request.POST.keys())}")
        
        form = PostForm(request.POST, request.FILES, user=request.user)
        logger.info(f"Form is valid: {form.is_valid()}")
        if not form.is_valid():
            logger.error(f"Form errors: {form.errors}")
        
        if form.is_valid():
            logger.info(f"Calling create_post_for_user with FILES: {request.FILES}")
            # Get group from POST data (hidden input)
            group_id = request.POST.get('group')
            post = create_post_for_user(form, request.user, request.FILES, group_id=group_id)
            logger.info(f"Post created with ID: {post.id}")
            logger.info(f"Post group: {post.group}")
            logger.info(f"Post images count: {post.images.count()}")
            logger.info(f"Post video: {post.video}")
            logger.info(f"Post docs: {post.docs}")
            logger.info(f"Post audio: {post.audio}")
            messages.success(request, 'Post created successfully.')
            # Mark this as a new post in session for back button logic
            request.session['is_new_post'] = True
            request.session['new_post_id'] = post.id
            return redirect('posts:post_details', post_id=post.id)
    else:
        form = PostForm(user=request.user)
    return render(request, 'posts/create_post.html', {'form': form, 'user_groups': user_groups})


@login_required
def storage_manager_view(request):
    """View for the storage manager page"""
    return render(request, 'posts/storage/storage_manager.html')


@login_required
def offline_media_viewer_view(request):
    """View for the offline media viewer page"""
    return render(request, 'posts/offline_media_viewer.html')


@login_required
def post_detail_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    show_all = request.GET.get('show_all') == '1'
    context = build_comments_context(post, request.user, show_all_comments=show_all)
    context['is_liked'] = post.is_liked_by(request.user)
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    
    # Track previous page for back button logic
    is_new_post = request.session.pop('is_new_post', False)
    new_post_id = request.session.pop('new_post_id', None)
    
    # If not a new post, save the referring URL for back button
    if not is_new_post and request.META.get('HTTP_REFERER'):
        # Only save if it's not already the post detail page
        referer = request.META.get('HTTP_REFERER')
        if str(post_id) not in referer:
            request.session['previous_page'] = referer
    
    context['is_new_post'] = is_new_post
    context['previous_page'] = request.session.get('previous_page', reverse('posts:home'))
    
    # For HTMX requests to show all comments, return only the comments section
    if request.headers.get('HX-Request') and show_all:
        return render(request, 'posts/partials/comments_section.html', context)
    
    return render(request, 'posts/post_detail.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        handle_add_comment_request(request, post)
    return redirect('posts:post_details', post_id=post_id)


@login_required
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    result = toggle_comment_like_for_user(comment, request.user)
    liked_comment_ids = result.get('liked_comment_ids', set())
    return render(request, 'posts/partials/comment_item.html', {
        'comment': comment,
        'liked_comment_ids': liked_comment_ids,
    })


@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    result = toggle_post_like_for_user(post, request.user)
    return render(request, 'posts/partials/like_button.html', {
        'post': result['post'],
        'is_liked': result['is_liked'],
        'like_count': result['like_count'],
    })


@login_required
def post_likers_list(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    likers = User.objects.filter(like__post=post) if hasattr(User, "like_set") else User.objects.filter(id__in=post.likes.values_list("user_id", flat=True))
    return render(request, 'posts/partials/likers_modal_content.html', {'likers': likers})


@login_required
def unit_posts_view(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)
    posts = Post.objects.filter(unit=unit).select_related('author', 'unit').order_by('-created_at')
    liked_post_ids = set(Like.objects.filter(user=request.user, post__in=posts).values_list('post_id', flat=True))
    return render(request, 'courses/unit_detail.html', {
        'unit': unit,
        'posts': posts,
        'liked_post_ids': liked_post_ids,
        'unread_notifications_count': get_cached_unread_count(request.user),
    })


@login_required
def search_view(request):
    from posts.queries.search_queries import search_users, search_groups, get_user_groups, get_following_ids
    query = request.GET.get('q', '')

    users = search_users(query, request.user)
    groups = search_groups(query)
    user_groups = get_user_groups(request.user)
    following_ids = list(get_following_ids(request.user))

    context = {
        'query': query,
        'users': users,
        'groups': groups,
        'user_groups': user_groups,
        'following_ids': following_ids,
        'unread_notifications_count': get_cached_unread_count(request.user),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'posts/partials/search_results_inner.html', context)

    return render(request, 'posts/search_results.html', context)


@login_required
def view_image_fullscreen(request, post_id, image_index):
    post = get_object_or_404(Post, id=post_id)
    all_images = list(post.images.all())
    
    # Handle both index and ID (for backward compatibility with existing links)
    if image_index < len(all_images):
        current_index = image_index
        post_image = all_images[current_index]
    else:
        # If image_index is actually an ID (from old links), find by ID
        post_image = get_object_or_404(post.images, id=image_index)
        current_index = all_images.index(post_image)

    # Get likes for the individual image
    from .models import PostImageLike
    image_likes = post_image.likes.select_related('user').all()
    liked_users = [like.user for like in image_likes]

    # Check if current user liked the image
    is_liked = post_image.likes.filter(user=request.user).exists()

    # Get users that the current user follows
    from users.models import Follow
    following_ids = set(Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True))

    # Separate likes into followed users and others
    followed_likers = [user for user in liked_users if user.id in following_ids]
    other_likers = [user for user in liked_users if user.id not in following_ids]

    context = {
        'post': post,
        'post_image': post_image,
        'all_images': all_images,
        'current_index': current_index,
        'has_prev': current_index > 0,
        'has_next': current_index < len(all_images) - 1,
        'prev_index': current_index - 1 if current_index > 0 else None,
        'next_index': current_index + 1 if current_index < len(all_images) - 1 else None,
        'followed_likers': followed_likers,
        'other_likers_count': len(other_likers),
        'total_likes': len(liked_users),
        'is_liked': is_liked,
        'current_user_profile_pic': request.user.profile_pic.url if request.user.profile_pic else None,
    }

    return render(request, 'posts/image_fullscreen.html', context)


@login_required
def share_post_view(request, post_id):
    """Django view to handle post sharing to multiple users or groups"""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        share_type = request.POST.get('share_type')  # 'user' or 'group'
        message = request.POST.get('message', '')
        
        # Debug: Log the POST data
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Share request - share_type: {share_type}, POST data: {dict(request.POST)}")
        
        try:
            if share_type == 'user':
                # Handle multiple users (comma-separated)
                usernames_str = request.POST.get('shared_to_usernames', '')
                logger.info(f"Usernames string: {usernames_str}")
                usernames = [u.strip() for u in usernames_str.split(',') if u.strip()]
                logger.info(f"Parsed usernames: {usernames}")
                
                shared_count = 0
                for username in usernames:
                    try:
                        shared_to_user = User.objects.get(username=username)
                        share_post(request.user, post, shared_to_user=shared_to_user, message=message)
                        shared_count += 1
                    except User.DoesNotExist:
                        continue  # Skip invalid usernames
                
                if shared_count > 0:
                    if request.headers.get('HX-Request'):
                        return HttpResponse(
                            f'<div class="alert alert-success">Post shared to {shared_count} user(s) successfully.</div>'
                        )
                    messages.success(request, f'Post shared to {shared_count} user(s) successfully.')
                else:
                    if request.headers.get('HX-Request'):
                        return HttpResponse(
                            '<div class="alert alert-danger">No valid users found.</div>'
                        )
                    messages.error(request, 'No valid users found.')
                    
            elif share_type == 'group':
                # Handle multiple groups (comma-separated)
                group_ids_str = request.POST.get('shared_to_group_ids', '')
                group_ids = [int(g.strip()) for g in group_ids_str.split(',') if g.strip()]
                
                shared_count = 0
                errors = []
                from groups.models import Group
                for group_id in group_ids:
                    try:
                        shared_to_group = Group.objects.get(id=group_id)
                        share_post(request.user, post, shared_to_group=shared_to_group, message=message)
                        shared_count += 1
                    except (Group.DoesNotExist, ValueError) as e:
                        errors.append(str(e))
                        continue  # Skip invalid group IDs
                    except ValidationError as e:
                        errors.append(str(e))
                        continue  # Skip groups that can't be shared to
                
                if shared_count > 0:
                    if request.headers.get('HX-Request'):
                        return HttpResponse(
                            f'<div class="alert alert-success">Post shared to {shared_count} group(s) successfully.</div>'
                        )
                    messages.success(request, f'Post shared to {shared_count} group(s) successfully.')
                else:
                    error_msg = errors[0] if errors else 'No valid groups found.'
                    if request.headers.get('HX-Request'):
                        return HttpResponse(
                            f'<div class="alert alert-danger">{error_msg}</div>'
                        )
                    messages.error(request, error_msg)
            else:
                if request.headers.get('HX-Request'):
                    return HttpResponse(
                        f'<div class="alert alert-danger">Invalid share type: {share_type}</div>'
                    )
                messages.error(request, 'Invalid share type.')
        except Exception as e:
            import traceback
            logger.error(f"Share error: {str(e)}\n{traceback.format_exc()}")
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    f'<div class="alert alert-danger">Error: {str(e)}</div>'
                )
            messages.error(request, str(e))
    
    # Only redirect if not an HTMX request
    if not request.headers.get('HX-Request'):
        return redirect('posts:post_details', post_id=post_id)
    return HttpResponse('')


@login_required
def shared_posts_view(request):
    """View to show all posts shared to the user (direct shares and group shares)"""
    shared_posts = get_user_received_shares(request.user)
    
    context = {
        'shared_posts': shared_posts,
        'unread_notifications_count': get_cached_unread_count(request.user),
    }
    
    return render(request, 'posts/shared_posts.html', context)


@login_required
def search_following_users(request):
    """HTMX search endpoint for users the current user is following"""
    query = request.GET.get('user_search', '') or request.GET.get('q', '')
    
    from users.models import Follow
    following_ids = Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True)
    
    users = User.objects.filter(
        id__in=following_ids
    ).filter(
        username__icontains=query
    )[:10]
    
    return render(request, 'posts/partials/share_user_results.html', {'users': users})


@login_required
def search_user_groups(request):
    """HTMX search endpoint for groups the current user is a member of"""
    query = request.GET.get('group_search', '') or request.GET.get('q', '')
    
    from groups.models import Membership, MembershipStatus
    group_ids = Membership.objects.filter(
        user=request.user,
        status=MembershipStatus.APPROVED
    ).values_list('group_id', flat=True)
    
    from groups.models import Group
    groups = Group.objects.filter(id__in=group_ids)
    
    if query:
        groups = groups.filter(name__icontains=query)
    
    return render(request, 'posts/partials/share_group_results.html', {'groups': groups})


@login_required
def task_status_view(request, task_id):
    """API endpoint to check Celery task status for progress tracking"""
    from .tasks import create_post_with_media
    
    task = AsyncResult(task_id, app=create_post_with_media)
    
    response_data = {
        'state': task.state,
        'meta': task.info if task.state != 'FAILURE' else {'status': str(task.info)}
    }
    
    return JsonResponse(response_data)
