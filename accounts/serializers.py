from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils.text import slugify

from .models import RegistrationOTP

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    otp = serializers.CharField(write_only=True, max_length=6)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name',
                  'phone', 'password', 'password_confirm', 'otp')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})

        otp = attrs.pop('otp', None)
        email = attrs.get('email')
        if not otp:
            raise serializers.ValidationError({'otp': 'OTP is required.'})

        reg_otp = RegistrationOTP.objects.filter(
            email__iexact=email,
            token=otp,
            is_used=False,
        ).first()

        if not reg_otp or reg_otp.is_expired():
            raise serializers.ValidationError({'otp': 'Invalid or expired OTP.'})

        self._registration_otp = reg_otp
        return attrs

    def create(self, validated_data):
        if validated_data.get('email') and not validated_data.get('username'):
            validated_data['username'] = validated_data['email']
        user = User.objects.create_user(**validated_data)
        reg_otp = getattr(self, '_registration_otp', None)
        if reg_otp:
            reg_otp.is_used = True
            reg_otp.save(update_fields=['is_used'])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name',
                  'phone', 'role', 'public_booking_slug', 'date_joined')
        read_only_fields = ('id', 'role', 'public_booking_slug', 'date_joined')


class ProfileSerializer(serializers.ModelSerializer):
    public_booking_slug = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name',
                  'phone', 'role', 'public_booking_slug', 'date_joined')
        read_only_fields = ('id', 'role', 'date_joined')

    def validate_public_booking_slug(self, value):
        request = self.context.get('request')
        user = request.user if request else None

        if value is None or value == '':
            return None

        if not user or not user.is_admin_user:
            raise serializers.ValidationError('Only admins can set a public booking link.')

        slug = slugify(value)
        if not slug:
            raise serializers.ValidationError('Please enter a valid slug (letters/numbers/hyphens).')

        qs = User.objects.filter(public_booking_slug__iexact=slug)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This booking link is already in use.')

        return slug


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admins to manage other users/admins."""
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name',
                  'phone', 'role', 'public_booking_slug', 'password', 'date_joined')
        read_only_fields = ('id', 'public_booking_slug', 'date_joined')

    def validate_email(self, value):
        existing = User.objects.filter(email__iexact=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if validated_data.get('email') and not validated_data.get('username'):
            validated_data['username'] = validated_data['email']
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if validated_data.get('email') and not validated_data.get('username'):
            validated_data['username'] = validated_data['email']
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account is associated with this email address.")
        return value


class ConfirmPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)
    password_confirm = serializers.CharField(min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs


class RequestRegistrationOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value
