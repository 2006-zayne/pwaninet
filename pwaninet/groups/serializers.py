from rest_framework import serializers
from .models import Group, Membership, MembershipRole, MembershipStatus, JoinPolicy
from users.models import User
from courses.models import Course, Year


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representations"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'second_name', 'profile_pic']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name']


class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = ['id', 'year']


class GroupSerializer(serializers.ModelSerializer):
    created_by = UserMinimalSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    year = YearSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'group_pic', 'is_official', 'join_policy',
            'course', 'year', 'created_at', 'created_by', 'member_count'
        ]
        read_only_fields = ['created_by', 'created_at']

    def get_member_count(self, obj):
        return obj.memberships.filter(status=MembershipStatus.APPROVED).count()


class GroupCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating groups"""
    class Meta:
        model = Group
        fields = [
            'name', 'description', 'group_pic', 'is_official', 'join_policy',
            'course', 'year'
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        group = Group.objects.create(created_by=user, **validated_data)
        
        # Creator automatically becomes admin
        Membership.objects.create(
            user=user,
            group=group,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )
        return group


class MembershipSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Membership
        fields = [
            'id', 'user', 'group', 'role', 'role_display',
            'status', 'status_display', 'joined_at'
        ]
        read_only_fields = ['joined_at']


class MembershipCreateSerializer(serializers.Serializer):
    """Serializer for joining a group"""
    def validate(self, attrs):
        user = self.context['request'].user
        group_id = self.context['group_id']
        
        # Check if user already has a membership
        if Membership.objects.filter(user=user, group_id=group_id).exists():
            raise serializers.ValidationError("You already have a membership request for this group.")
        
        # Check official group restrictions
        try:
            group = Group.objects.get(pk=group_id)
            if group.is_official and group.course and group.year:
                if user.course != group.course or user.year != group.year:
                    raise serializers.ValidationError(
                        "You can only join official groups that match your course and year."
                    )
        except Group.DoesNotExist:
            raise serializers.ValidationError("Group not found.")
        
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        group_id = self.context['group_id']
        
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            raise serializers.ValidationError("Group not found.")
        
        # Determine status based on join policy
        if group.join_policy == JoinPolicy.OPEN:
            status = MembershipStatus.APPROVED
        elif group.join_policy == JoinPolicy.APPROVAL:
            status = MembershipStatus.PENDING
        elif group.join_policy == JoinPolicy.INVITE_ONLY:
            raise serializers.ValidationError("This group is invite-only.")
        else:
            status = MembershipStatus.PENDING
        
        membership = Membership.objects.create(
            user=user,
            group_id=group_id,
            role=MembershipRole.MEMBER,
            status=status
        )
        return membership


class MembershipActionSerializer(serializers.Serializer):
    """Serializer for approving/rejecting membership requests"""
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        try:
            User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        return value


class RoleAssignmentSerializer(serializers.Serializer):
    """Serializer for assigning roles to members"""
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=MembershipRole.choices)

    def validate_user_id(self, value):
        try:
            User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        return value

    def validate(self, attrs):
        group_id = self.context['group_id']
        user_id = attrs['user_id']
        role = attrs['role']
        
        # Check if membership exists
        try:
            membership = Membership.objects.get(
                user_id=user_id,
                group_id=group_id,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            raise serializers.ValidationError("User is not an approved member of this group.")
        
        # Enforce max 5 admins constraint
        if role == MembershipRole.ADMIN:
            current_admin_count = Membership.objects.filter(
                group_id=group_id,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            ).count()
            if current_admin_count >= 5:
                raise serializers.ValidationError(
                    "Maximum of 5 admins allowed per group."
                )
        
        attrs['membership'] = membership
        return attrs
