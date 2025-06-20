from rest_framework import serializers

from .fields import Base64ImageField

class ImageMixin(serializers.Serializer):
    """Поле `avatar` для чтения/записи base64-картинки."""
    avatar = Base64ImageField(required=False, allow_null=True)

