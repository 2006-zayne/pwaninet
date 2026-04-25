from rest_framework import serializers
from .models import Post, Comment, Report, Like
from groups.serializers import GroupSerializer, UserMinimalSerializer
from courses.models import Course, Unit


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'name']


class PostSerializer(serializers.ModelSerializer):
    author = UserMinimalSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    unit = UnitSerializer(read_only=True)
    like_count = serializers.ReadOnlyField(source='like_count')
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'group', 'course', 'unit', 'content',
            'image', 'video', 'docs', 'gradient_class',
            'created_at', 'updated_at', 'like_count', 'is_liked'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
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
    """Serializer for creating posts"""
    class Meta:
        model = Post
        fields = [
            'group', 'course', 'unit', 'content',
            'image', 'video', 'docs', 'gradient_class'
        ]

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
                    "You must be an approved member to post in this group."
                )
        return value


class PostUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating posts"""
    class Meta:
        model = Post
        fields = ['content', 'image', 'video', 'docs', 'gradient_class']


class CommentSerializer(serializers.ModelSerializer):
    author = UserMinimalSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'created_at', 'like_count', 'is_liked']
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
        fields = ['post', 'reason']

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
