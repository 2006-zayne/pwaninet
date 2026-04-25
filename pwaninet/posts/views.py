from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Post, Comment, Report, Like
from .serializers import (
    PostSerializer, PostCreateSerializer, PostUpdateSerializer,
    CommentSerializer, CommentCreateSerializer, ReportCreateSerializer,
    ReportSerializer
)
from .permissions import CanDeletePost, CanEditPost, IsPostAuthorOrReadOnly
from groups.permissions import IsApprovedMember


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
