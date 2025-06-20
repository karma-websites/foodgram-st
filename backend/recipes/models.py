from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

from users.models import User

# from rest_framework import serializers

class Ingredient(models.Model):
    title = models.CharField(max_length=150)

    class Unit(models.TextChoices):
        GRAM      = "g",  "г"
        KILOGRAM  = "kg", "кг"
        MILLILITR = "ml", "мл"
        LITR      = "l",  "л"
        PIECE     = "pcs","шт"

    measurement_unit = models.CharField(
        max_length=50,
        help_text="грамм, шт., мл и т.д.",
        choices=Unit.choices,
    )

    class Meta:
        ordering = ("title",)
        verbose_name = "ингредиент"
        verbose_name_plural = "ингредиенты"

        unique_together = ("title", "measurement_unit") 

    def __str__(self):
        return f"{self.title} ({self.measurement_unit})"





def recipe_image_path(instance: "Recipe", filename: str) -> str:
    # /media/users/<username>//<original_filename>
    return f'users/recipes/{instance.author.id}/{filename}'

class Recipe(models.Model):
    author  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
        null=False,
        blank=False
    )
    title           = models.CharField(max_length=256, null=False, blank=False)
    description     = models.TextField(blank=True, null=False)
    cooking_time    = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Время приготовления в минутах",
        null=False, 
        blank=False
    )
    ingredients     = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
        null=False,
        blank=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    image = models.ImageField(
        upload_to=recipe_image_path,
        blank=False,
        null=False,
        default='users/recipes/default.png'
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "рецепт"
        verbose_name_plural = "рецепты"

    def __str__(self):
        return self.title


class Favorite(models.Model):
    user    = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='favorites')
    recipe  = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='favorited_by')

    class Meta:
        unique_together = ('user', 'recipe')


class ShoppingCart(models.Model):
    user    = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='shopping_carts')
    recipe  = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='in_shopping_carts')

    class Meta:
        unique_together = ('user', 'recipe')


class RecipeIngredient(models.Model):
    """Связь рецепт — ингредиент с количеством."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients"
    )

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="ingredient_recipes"
    )

    amount = models.DecimalField(
        max_digits=7, decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Сколько именно (в указанных единицах)"
    )

    class Meta:
        unique_together = ("recipe", "ingredient")
        verbose_name = "ингредиент в рецепте"
        verbose_name_plural = "ингредиенты в рецепте"

    def __str__(self):
        return f"{self.ingredient} — {self.amount}"