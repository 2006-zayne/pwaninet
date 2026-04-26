from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Post, Comment, Report, Like
from .serializers import (
    PostSerializer, PostCreateSerializer, PostUpdateSerializer,
    CommentSerializer, CommentCreateSerializer, ReportCreateSerializer,
    ReportSerializer
)
from .permissions import CanDeletePost, CanEditPost, IsPostAuthorOrReadOnly
from groups.permissions import IsApprovedMember
from courses.models import Unit
from users.models import User
from posts.forms import PostForm
from posts.services.comment_service import build_comments_context, handle_add_comment_request, toggle_comment_like_for_user
from posts.services.feed_service import build_home_feed_context
from posts.services.post_service import toggle_post_like_for_user, create_post_for_user
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

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

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


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments.
    """
    permission_classes = [IsAuthenticated]
    queryset = Comment.objects.select_related('author', 'post').all()
    serializer_class = CommentSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing reports (admin only).
    """
    permission_classes = [IsAuthenticated]
    queryset = Report.objects.select_related('reporter', 'post').all()
    serializer_class = ReportSerializer

    def get_queryset(self):
        # Only allow admins to see reports
        user = self.request.user
        from groups.models import Membership, MembershipRole, MembershipStatus
        
        # Get all groups where user is admin
        admin_groups = Membership.objects.filter(
            user=user,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        ).values_list('group_id', flat=True)
        
        # Filter reports for posts in those groups
        return self.queryset.filter(post__group_id__in=admin_groups)


# ============================================================================
# DJANGO WEB VIEWS
# ============================================================================

@login_required
def home_view(request):
    cursor = request.GET.get('cursor')
    context = build_home_feed_context(request.user, cursor=cursor)
    
    # Add explore groups - groups user is not a member of
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
    group_id = request.GET.get('group_id')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            create_post_for_user(form, request.user, request.FILES, group_id=group_id)
            messages.success(request, 'Post created successfully.')
            return redirect('posts:home')
    else:
        form = PostForm(user=request.user)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_detail_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    show_all = request.GET.get('show_all') == '1'
    context = build_comments_context(post, request.user, show_all_comments=show_all)
    context['is_liked'] = post.is_liked_by(request.user)
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    
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

    # Get likes for the post
    post_likes = post.likes.select_related('user').all()
    liked_users = [like.user for like in post_likes]

    # Get users that the current user follows
    following_ids = set(request.user.following.all().values_list('id', flat=True))

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
    }

    return render(request, 'posts/image_fullscreen.html', context)
