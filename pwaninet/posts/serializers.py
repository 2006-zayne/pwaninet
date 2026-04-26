from rest_framework import serializers
from .models import Post, Comment, Report, Like, Repost, HiddenPost, AuthorPreference, SharedPost
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
    repost_count = serializers.ReadOnlyField(source='repost_count')
    is_reposted = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'group', 'course', 'unit', 'content',
            'image', 'video', 'docs', 'gradient_class',
            'created_at', 'updated_at', 'like_count', 'is_liked',
            'repost_count', 'is_reposted'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

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


class RepostSerializer(serializers.ModelSerializer):
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
        
        repost = Repost.objects.create(reposter=request.user, **validated_data)
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

    class Meta:
        model = SharedPost
        fields = ['id', 'original_post', 'sharer', 'shared_to', 'message', 'created_at', 'is_viewed']
        read_only_fields = ['sharer', 'created_at', 'is_viewed']


class SharedPostCreateSerializer(serializers.ModelSerializer):
    """Serializer for sharing posts"""
    class Meta:
        model = SharedPost
        fields = ['original_post', 'shared_to', 'message']

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

    def create(self, validated_data):
        request = self.context['request']
        original_post = validated_data['original_post']
        shared_to = validated_data['shared_to']
        
        # Check if already shared
        if SharedPost.objects.filter(
            original_post=original_post,
            sharer=request.user,
            shared_to=shared_to
        ).exists():
            raise serializers.ValidationError("You have already shared this post to this user.")
        
        shared_post = SharedPost.objects.create(sharer=request.user, **validated_data)
        return shared_post
