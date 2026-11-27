from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from .models import Application, Category, Job, Profile


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=["job_seeker", "employer"],
        default="job_seeker",
        required=False,
    )

    def validate_username(self, value):
        cleaned_value = str(value).strip()
        if not cleaned_value:
            raise serializers.ValidationError("Username cannot be empty.")
        if User.objects.filter(username__iexact=cleaned_value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return cleaned_value

    def validate_email(self, value):
        cleaned_value = str(value).strip().lower()
        if not cleaned_value:
            raise serializers.ValidationError("Email cannot be empty.")
        if User.objects.filter(email__iexact=cleaned_value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return cleaned_value

    def validate(self, data):
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        try:
            validate_password(data.get("password"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        role = validated_data.pop("role", "job_seeker")

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
            )
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.save(update_fields=["role"])

        return user


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:
        model = Profile
        fields = ["username", "email", "role", "phone", "bio", "skills", "resume"]


class JobSerializer(serializers.ModelSerializer):
    employer_username = serializers.CharField(source="employer.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company",
            "salary",
            "location",
            "description",
            "slug",
            "category",
            "category_name",
            "employer",
            "employer_username",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "employer", "created_at"]

    def validate_salary(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Salary cannot be negative.")
        return value

    def validate_title(self, value):
        cleaned_value = str(value).strip()
        if not cleaned_value:
            raise serializers.ValidationError("Title cannot be empty.")
        return cleaned_value


class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    company = serializers.CharField(source="job.company", read_only=True)
    applicant_username = serializers.CharField(source="applicant.username", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "job",
            "job_title",
            "company",
            "applicant",
            "applicant_username",
            "status",
            "applied_at",
        ]
        read_only_fields = ["id", "job", "applicant", "status", "applied_at"]