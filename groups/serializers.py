from rest_framework import serializers
from .models import (
    Group, Membership, MembershipRole, MembershipStatus, JoinPolicy,
    Announcement, AnnouncementPriority, AnnouncementAttachment,
    GroupMessage, GroupMessageAttachment, GroupMessageReaction
)
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


class AnnouncementAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for announcement attachments"""
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    document_preview = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementAttachment
        fields = ['id', 'attachment_type', 'file', 'file_url', 'file_name', 'file_extension', 'thumbnail', 'thumbnail_url', 'document', 'document_preview', 'uploaded_at']
        read_only_fields = ['uploaded_at']

    def get_file_url(self, obj):
        if obj.attachment_type == 'document' and obj.document and obj.document.latest_version:
            return obj.document.latest_version.files.first().file.url if obj.document.latest_version.files.exists() else None
        return obj.file.url if obj.file else None

    def get_file_name(self, obj):
        if obj.attachment_type == 'document' and obj.document:
            return obj.document.title
        return obj.file.name.split('/')[-1] if obj.file else None

    def get_file_extension(self, obj):
        if obj.attachment_type == 'document' and obj.document and obj.document.latest_version:
            return obj.document.latest_version.files.first().extension if obj.document.latest_version.files.exists() else None
        if obj.file and obj.file.name:
            return obj.file.name.split('.')[-1].lower() if '.' in obj.file.name else None
        return None

    def get_thumbnail_url(self, obj):
        if obj.attachment_type == 'document' and obj.document and obj.document.latest_version:
            first_file = obj.document.latest_version.files.first()
            if first_file and first_file.thumbnail_path:
                return f"/media/{first_file.thumbnail_path}"
        return obj.thumbnail.url if obj.thumbnail else None

    def get_document_preview(self, obj):
        if obj.attachment_type == 'document' and obj.document:
            return {
                'id': obj.document.id,
                'title': obj.document.title,
                'category': obj.document.category.name if obj.document.category else None,
                'preview_path': obj.document.latest_version.files.first().preview_path if obj.document.latest_version and obj.document.latest_version.files.exists() else None,
            }
        return None


class AnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for announcement display"""
    author = UserMinimalSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    author_role = serializers.SerializerMethodField()
    attachments = AnnouncementAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'group', 'author', 'title', 'content', 'priority',
            'priority_display', 'is_pinned', 'attachments',
            'created_at', 'updated_at', 'author_role'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_author_role(self, obj):
        """Get the author's role in the group at time of announcement creation"""
        try:
            membership = Membership.objects.get(
                user=obj.author,
                group=obj.group,
                status=MembershipStatus.APPROVED
            )
            return membership.get_role_display()
        except Membership.DoesNotExist:
            return None


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating announcements"""
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'priority', 'is_pinned', 'attachments']

    def create(self, validated_data):
        user = self.context['request'].user
        group_id = self.context['group_id']
        
        # Extract attachments from validated data
        attachments_files = validated_data.pop('attachments', [])
        
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            raise serializers.ValidationError("Group not found.")
        
        announcement = Announcement.objects.create(
            group=group,
            author=user,
            **validated_data
        )
        
        # Create attachment objects
        for attachment_file in attachments_files:
            # Determine file type
            file_name = attachment_file.name.lower()
            if file_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                # Image attachment - create with file and generate thumbnail
                attachment = AnnouncementAttachment.objects.create(
                    announcement=announcement,
                    attachment_type='image',
                    file=attachment_file
                )
                from .tasks import generate_attachment_thumbnail
                generate_attachment_thumbnail.delay(attachment.id)
            else:
                # Document attachment - create in document repository
                from documents.models import Document, DocumentVersion, DocumentFile, Category
                from documents.tasks import process_document_file
                
                # Get or create default category (will be updated later)
                category, _ = Category.objects.get_or_create(
                    code='other',
                    defaults={'name': 'Other'}
                )
                
                # Create document
                document = Document.objects.create(
                    title=attachment_file.name,
                    description=f"Attached to announcement: {announcement.title}",
                    category=category,
                    uploaded_by=user,
                    visibility='private',  # Will be updated later
                    status='processing'
                )
                
                # Create version
                version = DocumentVersion.objects.create(
                    document=document,
                    version_number=1,
                    created_by=user,
                    is_latest=True
                )
                
                # Create file
                document_file = DocumentFile.objects.create(
                    document_version=version,
                    file=attachment_file,
                    original_filename=attachment_file.name,
                    storage_path=attachment_file.name,
                    mime_type=attachment_file.content_type,
                    extension=attachment_file.name.split('.')[-1].lower(),
                    size_bytes=attachment_file.size,
                    storage_provider='local',
                    uploaded_by=user
                )
                
                # Create attachment linking to document
                attachment = AnnouncementAttachment.objects.create(
                    announcement=announcement,
                    attachment_type='document',
                    document=document
                )
                
                # Trigger document processing
                # process_document_file.delay(document_file.id)
        
        return announcement


class AnnouncementUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating announcements"""
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'priority', 'is_pinned', 'attachments']

    def update(self, instance, validated_data):
        # Extract attachments from request data (not validated_data since it's write-only)
        attachments_files = self.context.get('request').FILES.getlist('attachments')
        
        # Update announcement fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        
        # Handle attachments - if new attachments are provided, replace existing ones
        if attachments_files:
            # Delete existing attachments
            instance.attachments.all().delete()
            
            # Create new attachment objects
            for attachment_file in attachments_files:
                # Determine file type
                file_name = attachment_file.name.lower()
                if file_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    # Image attachment - create with file and generate thumbnail
                    attachment = AnnouncementAttachment.objects.create(
                        announcement=instance,
                        attachment_type='image',
                        file=attachment_file
                    )
                    from .tasks import generate_attachment_thumbnail
                    generate_attachment_thumbnail.delay(attachment.id)
                else:
                    # Document attachment - create in document repository
                    from documents.models import Document, DocumentVersion, DocumentFile, Category
                    from documents.tasks import process_document_file
                    
                    # Get or create default category (will be updated later)
                    category, _ = Category.objects.get_or_create(
                        code='other',
                        defaults={'name': 'Other'}
                    )
                    
                    # Create document
                    document = Document.objects.create(
                        title=attachment_file.name,
                        description=f"Attached to announcement: {instance.title}",
                        category=category,
                        uploaded_by=self.context.get('request').user,
                        visibility='private',  # Will be updated later
                        status='processing'
                    )
                    
                    # Create version
                    version = DocumentVersion.objects.create(
                        document=document,
                        version_number=1,
                        created_by=self.context.get('request').user,
                        is_latest=True
                    )
                    
                    # Create file
                    document_file = DocumentFile.objects.create(
                        document_version=version,
                        file=attachment_file,
                        original_filename=attachment_file.name,
                        storage_path=attachment_file.name,
                        mime_type=attachment_file.content_type,
                        extension=attachment_file.name.split('.')[-1].lower(),
                        size_bytes=attachment_file.size,
                        storage_provider='local',
                        uploaded_by=self.context.get('request').user
                    )
                    
                    # Create attachment linking to document
                    attachment = AnnouncementAttachment.objects.create(
                        announcement=instance,
                        attachment_type='document',
                        document=document
                    )
                    
                    # Trigger document processing
                    # process_document_file.delay(document_file.id)

        return instance


class GroupMessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for group message attachments"""
    class Meta:
        model = GroupMessageAttachment
        fields = ['id', 'attachment_type', 'file', 'thumbnail', 'caption', 'order', 'created_at']
        read_only_fields = ['created_at']


class GroupMessageReactionSerializer(serializers.ModelSerializer):
    """Serializer for group message reactions"""
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = GroupMessageReaction
        fields = ['id', 'user', 'emoji', 'created_at']
        read_only_fields = ['created_at']


class GroupMessageSerializer(serializers.ModelSerializer):
    """Serializer for group messages"""
    sender = UserMinimalSerializer(read_only=True)
    attachments = GroupMessageAttachmentSerializer(many=True, read_only=True)
    reactions = GroupMessageReactionSerializer(many=True, read_only=True)
    reply_to = serializers.SerializerMethodField()

    class Meta:
        model = GroupMessage
        fields = [
            'id', 'group', 'sender', 'content', 'message_type',
            'reply_to', 'created_at', 'updated_at', 'status',
            'attachments', 'reactions'
        ]
        read_only_fields = ['created_at', 'updated_at', 'status']

    def get_reply_to(self, obj):
        if obj.reply_to:
            return GroupMessageSerializer(obj.reply_to).data
        return None


class GroupMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating group messages"""
    class Meta:
        model = GroupMessage
        fields = ['content', 'message_type', 'reply_to']

    def create(self, validated_data):
        group_id = self.context['group_id']
        user = self.context['request'].user

        # Validate user is a member of the group
        from .models import Membership, MembershipStatus
        if not Membership.objects.filter(
            user=user,
            group_id=group_id,
            status=MembershipStatus.APPROVED
        ).exists():
            raise serializers.ValidationError("You must be a member of this group to send messages.")

        message = GroupMessage.objects.create(
            group_id=group_id,
            sender=user,
            **validated_data
        )
        return message
