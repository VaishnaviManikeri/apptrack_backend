import uuid

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        candidate = User(username=attrs["email"], email=attrs["email"])
        validate_password(attrs["password"], user=candidate)
        return attrs

    def create(self, validated_data):
        name = validated_data["name"].strip()
        return User.objects.create_user(
            username=uuid.uuid4().hex,
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=name,
        )


class EmailTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from rest_framework_simplejwt.tokens import RefreshToken

        email = attrs["email"].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user = None

        authenticated_user = (
            authenticate(
                request=self.context.get("request"),
                username=user.get_username(),
                password=attrs["password"],
            )
            if user is not None
            else None
        )
        if authenticated_user is None:
            raise serializers.ValidationError(
                {"detail": "Email or password is incorrect."}
            )

        refresh = RefreshToken.for_user(authenticated_user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": authenticated_user.pk,
                "email": authenticated_user.email,
                "name": authenticated_user.first_name or authenticated_user.email,
                "joinedAt": authenticated_user.date_joined.isoformat(),
            },
        }


class ApplicationSerializer(serializers.Serializer):
    STATUSES = (
        "Interested",
        "Applied",
        "Assessment",
        "Interview",
        "Offer",
        "Rejected",
        "Withdrawn",
    )
    SOURCES = (
        "Company website",
        "LinkedIn",
        "Naukri",
        "Direct email",
        "Referral",
        "Other",
    )

    company = serializers.CharField(max_length=200)
    position = serializers.CharField(max_length=200)
    email = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    date = serializers.DateField(input_formats=["%Y-%m-%d"])
    status = serializers.ChoiceField(choices=STATUSES, default="Interested")
    source = serializers.ChoiceField(choices=SOURCES, default="Company website")
    followUp = serializers.DateField(
        input_formats=["%Y-%m-%d"], required=False, allow_null=True
    )
    jobUrl = serializers.URLField(max_length=2000, required=False, allow_blank=True)
    resume = serializers.CharField(max_length=200, required=False, allow_blank=True)
    salary = serializers.CharField(max_length=200, required=False, allow_blank=True)
    companyUrl = serializers.URLField(
        max_length=2000, required=False, allow_blank=True
    )
    recruiterName = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    recruiterLinkedin = serializers.URLField(
        max_length=2000, required=False, allow_blank=True
    )
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    color = serializers.CharField(max_length=30, required=False, allow_blank=True)
    mark = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def validate(self, attrs):
        for field in ("date", "followUp"):
            if field in attrs and attrs[field] is not None:
                attrs[field] = attrs[field].isoformat()
        return attrs
