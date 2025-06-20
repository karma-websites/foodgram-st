from rest_framework import serializers

from .models import Recipe, Ingredient, RecipeIngredient
from utils.fields import Base64ImageField
from users.serializers import UserShortSerializer

class IngredientAmountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)


class IngredientSerializer(serializers.ModelSerializer):

    name = serializers.CharField(source="title")

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']

class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id               = serializers.ReadOnlyField(source='ingredient.id')
    name             = serializers.ReadOnlyField(source='ingredient.title')
    measurement_unit = serializers.ReadOnlyField(
                           source='ingredient.measurement_unit')
    amount           = serializers.IntegerField()

    class Meta:
        model  = RecipeIngredient        #  <-- важный момент
        fields = ('id', 'name',
                  'measurement_unit', 'amount')

class RecipeMinified(serializers.ModelSerializer):

    name = serializers.CharField(source="title")

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")   # только 4 поля
        read_only_fields = fields

class RecipeReadSerializer(serializers.ModelSerializer):

    author = UserShortSerializer(read_only=True)

    name = serializers.CharField(source="title")
    text = serializers.CharField(source="description")

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    ingredients = IngredientInRecipeSerializer(source='recipe_ingredients', many=True, read_only=True)

    class Meta:
        model = Recipe
        depth = 1 # автоматически разворачивать вложенные объекты
        fields = (
            'id', 'author', 'ingredients', 'is_favorited', 
            'is_in_shopping_cart',  'name', 'image', 'text', 'cooking_time'
        )

    
    # ---------- helpers ----------
    def _exists_for_user(self, user, manager):
        """Возвращает True/False, никогда None."""
        if not user or not user.is_authenticated:
            return False
        return manager.filter(user=user).exists()

    def get_is_favorited(self, obj) -> bool:
        user = self.context["request"].user
        # obj.favorited_by — related_name модели Favorite
        return self._exists_for_user(user, obj.favorited_by)

    def get_is_in_shopping_cart(self, obj) -> bool:
        user = self.context["request"].user
        # obj.in_shopping_carts — related_name модели ShoppingCart
        return self._exists_for_user(user, obj.in_shopping_carts)

class IngredientAmountSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),   # ← проверит существование
    )
    amount = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=0.01,
    )

class RecipeWriteSerializer(serializers.ModelSerializer):

    image = Base64ImageField(required=True)
    name = serializers.CharField(required=True, source="title", max_length=256)
    text = serializers.CharField(required=True, source="description")

    ingredients = serializers.ListSerializer(
        required=True,
        child=IngredientAmountSerializer(),
        write_only=True
    )

    class Meta:
        model  = Recipe
        fields = [
            "name", "text", "cooking_time",
            "image", "ingredients"
        ]

    def to_representation(self, instance):
        """
        После создания/обновления вернуть объект так,
        как будто это RecipeReadSerializer.
        """
        from .serializers import RecipeReadSerializer   # локальный импорт, чтобы избежать циклов
        return RecipeReadSerializer(instance, context=self.context).data

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError("Время приготовления должно быть не меньше 1 минуты.")
        return value
    

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один ингредиент.")

        seen = set()
        for item in value:
            ing = item["id"]             # здесь уже сам объект Ingredient
            if ing in seen:
                raise serializers.ValidationError("Ингредиенты не должны повторяться.")
            seen.add(ing)
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        user = self.context["request"].user
        recipe = Recipe.objects.create(author=user, **validated_data)

        bulk = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item["id"],   # это уже экземпляр Ingredient
                amount=item["amount"]
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(bulk)
        return recipe

    
    def validate(self, attrs):
        """
        При PATCH поле `ingredients` обязательно — 
        тест ожидает 400, если его нет.
        """
        request = self.context["request"]
        # PATCH (или PUT c partial=True)
        if request.method in ("PATCH",) and "ingredients" not in self.initial_data:
            raise serializers.ValidationError({
                "ingredients": ["Это поле обязательно при обновлении рецепта."]
            })
        return attrs
    

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)

        # Обновляем простые поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            bulk = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient=item["id"],
                    amount=item["amount"],
                )
                for item in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(bulk)

        return instance
