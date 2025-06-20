from django.db.models import QuerySet
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.validators import UnicodeUsernameValidator
from djoser.serializers import UserCreateSerializer as BaseCreate

from utils.mixins import ImageMixin
from .models import User, Subscription


# ────────────────────────────── mixins ───────────────────────────────
class SubscriptionMixin(serializers.Serializer):
    """Добавляет поле `is_subscribed` и общую реализацию."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    def _is_following(self, user, obj) -> bool:
        return (
            user.is_authenticated
            and user != obj
            and Subscription.objects.filter(follower=user, author=obj).exists()
        )

    def get_is_subscribed(self, obj) -> bool:      # noqa: D401
        request = self.context.get("request")
        if not request:  # для вызова вне представления
            return False
        return self._is_following(request.user, obj)


# ────────────────────────────── serializers ─────────────────────────
class UserSerializer(ImageMixin, SubscriptionMixin, serializers.ModelSerializer):
    """Базовый сериализатор с общими полями и логикой подписки."""

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "avatar",
            "first_name", "last_name", "is_subscribed"
        )
        read_only_fields = ("id", "is_subscribed")  # актуально для read-only сериализаторов


class UserShortSerializer(UserSerializer):
    """Упрощённый сериализатор для рецептов, подписок."""
    
    class Meta(UserSerializer.Meta):
        read_only_fields = UserSerializer.Meta.fields  # полностью read-only


class UserCreateSerializer(BaseCreate):
    """Сериализатор создания пользователя (наследует от djoser)."""
    username = serializers.CharField(
        max_length=150,
        required=True,
        validators=[
            UnicodeUsernameValidator(),
            UniqueValidator(User.objects.all())
        ]
    )
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(User.objects.all())]
    )

    class Meta(BaseCreate.Meta):
        model = User
        fields = (
            "id", "email", "username",
            "first_name", "last_name", "password",
        )
        extra_kwargs = {"password": {"write_only": True}}


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, trim_whitespace=False)
    new_password     = serializers.CharField(required=True, trim_whitespace=False)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Текущий пароль неверен.")
        return value

    def validate_new_password(self, value):
        user = self.context["request"].user
        # при желании — минимальная длина, спец-символы и т.д.
        # if len(value) < 8:
        #     raise serializers.ValidationError("Пароль должен быть не короче 8 символов.")
        if user.check_password(value):
            raise serializers.ValidationError("Новый пароль не должен совпадать с текущим.")
        return value





class SubscriptionSerializer(serializers.ModelSerializer):
    """`Subscription` + агрегированные рецепты автора."""

    author = UserShortSerializer(read_only=True)
    recipes_count = serializers.IntegerField(
        source="author.recipes.count", read_only=True
    )
    recipes = serializers.SerializerMethodField()
    

    class Meta:
        model  = Subscription
        fields = ("id", "author", "recipes_count", "recipes")

    # ─────────── вспом. методы ───────────
    def _limited_recipes(self, qs: QuerySet) -> QuerySet:
        """
        Возвращает QS c учётом query-param ?recipes_limit=N.
        """
        limit = self.context.get("request").query_params.get("recipes_limit")
        return qs[: int(limit)] if (limit and limit.isdigit()) else qs

    def get_recipes(self, obj) -> list[dict]:
        from recipes.serializers import RecipeMinified

        qs = self._limited_recipes(obj.author.recipes.order_by("-id"))
        return RecipeMinified(qs, many=True, context=self.context).data

    # ─────────── плоское представление ───────────
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(data.pop("author"))        # «расплющиваем» поля автора
        return data