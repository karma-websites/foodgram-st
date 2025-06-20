from recipes.models import RecipeIngredient, Recipe
from django.db.models import Sum, F
from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10             # дефолтное количество
    page_size_query_param = 'limit'  # параметр в query для указания limit
    max_page_size = 100        # максимум по limit
    page_query_param = 'page'  # параметр для номера страницы (дефолт)



def generate_ingredient_list(user):
    recipes_qs = Recipe.objects.filter(in_shopping_carts__user=user)

    if not recipes_qs.exists():
        return None, "Ваша корзина пуста."

    ingredients = (
        RecipeIngredient.objects
        .filter(recipe__in=recipes_qs)
        .values(
            name=F("ingredient__title"),
            unit=F("ingredient__measurement_unit")
        )
        .annotate(total=Sum("amount"))
        .order_by("name")
    )

    lines = [
        f"{item['name']} ({item['unit']}) — {item['total']}"
        for item in ingredients
    ]
    content = "\n".join(lines) + "\n"
    return content, None