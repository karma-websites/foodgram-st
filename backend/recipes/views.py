# stdlib
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from django.shortcuts import HttpResponse

# 3rd-party
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission, SAFE_METHODS
from django_filters.rest_framework import DjangoFilterBackend

# local
from .models import Recipe, Ingredient, ShoppingCart, Favorite
from .filters import IngredientFilter
from recipes.serializers import RecipeReadSerializer, RecipeMinified, RecipeWriteSerializer, IngredientSerializer
from utils.helpers import generate_ingredient_list
from utils.pagination import CustomPage


def _handle_add_remove(request, model, recipe, error_exists, error_missing):
    user = request.user

    if request.method == "POST":
        try:
            with transaction.atomic():
                obj, created = model.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                return Response({"errors": error_exists}, status=400)
        except IntegrityError:
            return Response({"errors": "Ошибка при добавлении."}, status=409)
        return Response(RecipeMinified(recipe, context={"request": request}).data, status=201)

    deleted, _ = model.objects.filter(user=user, recipe=recipe).delete()
    if deleted:
        return Response(status=204)
    return Response({"errors": error_missing}, status=400)


class IsAuthorOrReadOnly(BasePermission):
    """
    Разрешаем:
      • любые SAFE-методы (GET, HEAD, OPTIONS) — всем;
      • POST — только аутентифицированным;
      • PATCH / DELETE — только автору объекта.
    """

    def has_permission(self, request, view):
        # чтение — всегда, запись — только если пользователь залогинен
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # чтение любой объект; изменения — только свой
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user


class RecipeViewSet(viewsets.ModelViewSet):
    # serializer_class  = RecipeReadSerializer
    pagination_class  = CustomPage
    http_method_names = ["get", "post", "patch", "delete"]

    # 1️⃣  Читаем-/пишем разные сериализаторы
    def get_serializer_class(self):
        # действие create → POST /api/recipes/
        if self.action in ("create", "update", "partial_update"):
            return RecipeWriteSerializer
        # всё остальное (list, retrieve, …) — «читающий»
        return RecipeReadSerializer


    def get_permissions(self):
        # безопасные действия + кастомный get_link — доступны всем
        if self.action in ("list", "retrieve", "get_link"):
            return [AllowAny()]
        
        elif self.action in ("shopping_cart", "favorite"):
            return [IsAuthenticated()]

        # все остальные (POST/PATCH/DELETE) — только автору/аутентифицированному
        return [IsAuthorOrReadOnly()]


    def get_queryset(self):
        qs     = Recipe.objects.all()
        user   = self.request.user
        params = self.request.query_params

        author_id     = params.get("author")
        is_favorited  = params.get("is_favorited") in ("1", "true", "True")
        is_in_cart    = params.get("is_in_shopping_cart") in ("1", "true", "True")

        # автор
        if author_id:
            qs = qs.filter(author_id=author_id)

        # избранное
        if is_favorited:
            return qs.filter(favorited_by__user=user).distinct().order_by("-created_at") \
                     if user.is_authenticated else Recipe.objects.none()

        # корзина
        if is_in_cart:
            return qs.filter(in_shopping_carts__user=user).distinct().order_by("-created_at") \
                     if user.is_authenticated else Recipe.objects.none()

        return qs.distinct().order_by("-created_at")


    @action(detail=True, methods=['get'], url_path='get-link', permission_classes=[AllowAny])
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        link = f"https://example.com/recipes/{recipe.pk}/"
        return Response({"short-link": link})


    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="favorite",
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        """Добавить / удалить рецепт из избранного текущего пользователя."""
        recipe = self.get_object()
        return _handle_add_remove(
            request, Favorite, recipe,
            error_exists="Уже в избранном.",
            error_missing="Этого рецепта нет в избранном."
        )

    
    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="shopping_cart",
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        """POST  — добавить в корзину
           DELETE — убрать из корзины"""
        recipe = self.get_object()
        return _handle_add_remove(
            request, ShoppingCart, recipe,
            error_exists="Уже в корзине.",
            error_missing="Этого рецепта нет в корзине."
        )
    
    @action(
        detail=False,                       # ⬅️ весь список, а не конкретный рецепт
        methods=["get"],
        url_path="download_shopping_cart",
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """
        Скачивает TXT-файл со сводным перечнем ингредиентов
        из всех рецептов, находящихся в корзине пользователя.
        """
        content, error = generate_ingredient_list(request.user)
        if error:
            return Response({"errors": error}, status=400)

        filename = f"shopping_list_{slugify(request.user.username)}.txt"
        response = HttpResponse(content, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]

    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter