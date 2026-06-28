from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer
from .models import User, Follow, DeviceAccount, CollaborationStatus, Pinch
from courses.models import Course, Year


class CourseSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'name', 'school_name']


class YearSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Year
        fields = ['id', 'level', 'course', 'course_id']


class UserSerializer(serializers.ModelSerializer):
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    course = CourseSerializer(read_only=True)
    year = YearSerializer(read_only=True)
    profile_pic_url = serializers.SerializerMethodField()
    cover_photo_url = serializers.SerializerMethodField()
    profile_completion_percentage = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='course.school.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'second_name', 'last_name',
            'global_role', 'profile_pic', 'cover_photo', 'bio', 'course', 'year',
            'follower_count', 'following_count', 'is_following',
            'profile_pic_url', 'cover_photo_url',
            'notify_on_like', 'notify_on_follow', 'notify_on_invite',
            'notify_on_group_request', 'notify_on_group_approved',
            'email_notifications', 'is_profile_complete',
            'headline', 'interests', 'collaboration_status', 'skills', 'projects',
            'github_url', 'linkedin_url', 'portfolio_url', 'twitter_url',
            'profile_completion_percentage', 'school_name',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['date_joined', 'last_login', 'is_profile_complete', 'profile_completion_percentage', 'school_name']

    def get_follower_count(self, obj):
        return obj.follower_relationships.count()

    def get_following_count(self, obj):
        return obj.following_relationships.count()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                follower=request.user, followed=obj
            ).exists()
        return False

    def get_profile_pic_url(self, obj):
        if obj.profile_pic:
            return obj.profile_pic.url
        return '/static/img/default_profile.jpg'

    def get_cover_photo_url(self, obj):
        if obj.cover_photo:
            return obj.cover_photo.url
        return None

    def get_profile_completion_percentage(self, obj):
        return obj.profile_completion_percentage


class UserPublicSerializer(serializers.ModelSerializer):
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    course = CourseSerializer(read_only=True)
    year = YearSerializer(read_only=True)
    profile_pic_url = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='course.school.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'second_name', 'last_name',
            'global_role', 'profile_pic', 'bio', 'course', 'year',
            'follower_count', 'following_count', 'is_following',
            'profile_pic_url', 'is_profile_complete',
            'headline', 'interests', 'collaboration_status', 'skills', 'projects',
            'github_url', 'linkedin_url', 'portfolio_url', 'twitter_url',
            'school_name'
        ]

    def get_follower_count(self, obj):
        return obj.follower_relationships.count()

    def get_following_count(self, obj):
        return obj.following_relationships.count()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                follower=request.user, followed=obj
            ).exists()
        return False

    def get_profile_pic_url(self, obj):
        if obj.profile_pic:
            return obj.profile_pic.url
        return '/static/img/default_profile.jpg'


class FollowSerializer(serializers.ModelSerializer):
    follower = UserPublicSerializer(read_only=True)
    followed = UserPublicSerializer(read_only=True)
    followed_username = serializers.CharField(write_only=True)

    class Meta:
        model = Follow
        fields = ['id', 'follower', 'followed', 'followed_username', 'created_at']
        read_only_fields = ['follower', 'created_at']

    def validate_followed_username(self, value):
        try:
            user = User.objects.get(username=value)
            if user == self.context['request'].user:
                raise serializers.ValidationError("You cannot follow yourself.")
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

    def create(self, validated_data):
        followed = validated_data.pop('followed_username')
        followed_user = User.objects.get(username=followed)
        follower = self.context['request'].user
        
        follow, created = Follow.objects.get_or_create(
            follower=follower,
            followed=followed_user
        )
        
        if not created:
            # If already following, unfollow
            follow.delete()
            return None
        
        return follow


class PinchSerializer(serializers.ModelSerializer):
    pinch_user = UserPublicSerializer(read_only=True)
    pinched_user = UserPublicSerializer(read_only=True)
    pinched_username = serializers.CharField(write_only=True)

    class Meta:
        model = Pinch
        fields = ['id', 'pinch_user', 'pinched_user', 'pinched_username', 'created_at']
        read_only_fields = ['pinch_user', 'created_at']

    def validate_pinched_username(self, value):
        try:
            user = User.objects.get(username=value)
            if user == self.context['request'].user:
                raise serializers.ValidationError("You cannot pinch yourself.")
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

    def create(self, validated_data):
        pinched = validated_data.pop('pinched_username')
        pinched_user = User.objects.get(username=pinched)
        pinch_user = self.context['request'].user
        
        # Check if can pinch
        can_pinch, error_msg = Pinch.can_pinch(pinch_user, pinched_user)
        if not can_pinch:
            raise serializers.ValidationError(error_msg)
        
        pinch = Pinch.objects.create(
            pinch_user=pinch_user,
            pinched_user=pinched_user
        )
        
        return pinch


class DeviceAccountSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = DeviceAccount
        fields = ['id', 'user', 'device_id', 'last_used', 'session_key']
        read_only_fields = ['user', 'last_used']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'second_name', 'last_name', 'bio',
            'profile_pic', 'cover_photo',
            'headline', 'interests', 'collaboration_status', 'skills', 'projects',
            'github_url', 'linkedin_url', 'portfolio_url', 'twitter_url',
            'notify_on_like', 'notify_on_follow', 'notify_on_invite',
            'notify_on_group_request', 'notify_on_group_approved',
            'email_notifications'
        ]
        read_only_fields = ['course', 'year']

    def validate_skills(self, value):
        """Ensure skills is a valid list"""
        if value is None:
            return []
        if isinstance(value, str):
            # If user sent a JSON string, try to parse it
            try:
                import json
                value = json.loads(value)
            except json.JSONDecodeError:
                # If not valid JSON, treat as comma-separated string
                value = [skill.strip() for skill in value.split(',') if skill.strip()]
        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a list of strings")
        return value

    def validate_projects(self, value):
        """Ensure projects is a valid list of dicts"""
        if value is None:
            return []
        if isinstance(value, str):
            # If user sent a JSON string, try to parse it
            try:
                import json
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    "Projects must be a valid JSON array of objects with title, description, and link"
                )
        if not isinstance(value, list):
            raise serializers.ValidationError("Projects must be a list of project objects")
        # Validate each project has required fields
        for project in value:
            if not isinstance(project, dict):
                raise serializers.ValidationError("Each project must be an object")
            if 'title' not in project or 'description' not in project:
                raise serializers.ValidationError("Each project must have title and description")
        return value

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class NotificationPreferencesSerializer(serializers.Serializer):
    notify_on_like = serializers.BooleanField(required=False)
    notify_on_follow = serializers.BooleanField(required=False)
    notify_on_invite = serializers.BooleanField(required=False)
    notify_on_group_request = serializers.BooleanField(required=False)
    notify_on_group_approved = serializers.BooleanField(required=False)
    email_notifications = serializers.BooleanField(required=False)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
