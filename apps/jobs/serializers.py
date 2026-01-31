from rest_framework import serializers
from apps.accounts.models import User
from .models import Category, Tag, Job
from cloudinary.uploader import upload  # For manual Cloudinary upload from URL

# Category Serializer
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '_all__'


# Tag Serializer
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


# Organization Serializer
class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'organization_name', 'email', 'website']


# Job Seeker Serializer (for jobSeekers_who_apply)
class JobSeekerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']  # Fields relevant to job seekers


# Job Serializer (updated)
class JobSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    category_title = serializers.StringRelatedField(source='category', read_only=True)
    tags = TagSerializer(many=True, read_only=True)  # Read-only for output (full details)
    tags_ids = serializers.PrimaryKeyRelatedField(  # New: Writable field for input (IDs)
        queryset=Tag.objects.all(), many=True, source='tags', write_only=True
    )
    organization = OrganizationSerializer(read_only=True)  # Read-only for output
    jobSeekers_who_apply = JobSeekerSerializer(many=True, read_only=True)  # New field

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'organization', 'category', 'category_id', 'category_title',
            'tags', 'tags_ids', 'slug',  # Note: tags_ids for input
            'description', 'location', 'banner', 'salary', 'is_active', 'jobSeekers_who_apply',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'jobSeekers_who_apply', 'created_at', 'updated_at']

    def validate(self, data):
        """
        Custom validation to ensure required fields are provided and valid.
        """
        if not data.get('title'):
            raise serializers.ValidationError({"title": "Title is required."})
        if not data.get('description'):
            raise serializers.ValidationError({"description": "Description is required."})
        if not data.get('location'):
            raise serializers.ValidationError({"location": "Location is required."})
        if not data.get('category'):
            raise serializers.ValidationError({"category_id": "Category is required."})
        # No need to validate organization_id anymore - it will be auto-set
        return data

    def create(self, validated_data):
        """
        Handle creation of a Job instance with related fields.
        Auto-set organization to request.user.
        """
        # Pop tags_ids (list of Tag instances from PrimaryKeyRelatedField)
        tags = validated_data.pop('tags', [])  # Now this will have instances if tags_ids provided
        # Auto-set organization from context (authenticated user)
        request = self.context.get('request')
        if request and request.user:
            validated_data['organization'] = request.user
        else:
            raise serializers.ValidationError({"organization": "Authenticated organization user required."})

        job = Job.objects.create(**validated_data)
        if tags:
            job.tags.set(tags)
        return job

    def update(self, instance, validated_data):
        """
        Handle updating of a Job instance with related fields.
        """
        tags = validated_data.pop('tags', None)  # tags here means instances from tags_ids
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if tags is not None:
            instance.tags.set(tags)
        instance.save()
        return instance  # Fixed: was 'return job' (undefined)


# Application Serializer
class ApplicationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    message = serializers.CharField(max_length=1000)
    resume = serializers.FileField(required=False, allow_null=True)

    def validate_resume(self, value):
        """
        Validate the uploaded resume file.
        """
        if value:
            max_size = 5 * 1024 * 1024  # 5MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError("Resume file size must be less than 5MB.")
            allowed_types = ['application/pdf', 'application/msword', 
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Resume must be a PDF, DOC, or DOCX file.")
        return value

    def validate(self, data):
        """
        Custom validation for the entire serializer.
        """
        if not data.get('message') and not data.get('resume'):
            raise serializers.ValidationError(
                {"non_field_errors": "Either a message or a resume must be provided."}
            )
        return data