from django.contrib import admin
from django.db.models import Count
from rest_framework import filters

from .models import Recipe, Ingredient, RecipeIngredient, Favorite


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display  = ("id", "title", "author_name", "favorites_total")
    list_select_related = ("author",)                # чтобы не было N+1
    search_fields = (
        "title",
        "author__username",
        "author__first_name",
        "author__last_name",
        "author__email",
    )
    readonly_fields = ("favorites_total",)           # на detail-странице
    fields = (
        "title",
        "author",
        "description",
        "cooking_time",
        "image",
        "favorites_total",                           # выводим счётчик
    )

    # ──────────────────────────────────────────────────────────
    # оптимизируем запрос: сразу считаем число избранных
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_fav_count=Count("favorited_by"))

    # имя автора (колонка)
    @admin.display(description="Автор", ordering="author__username")
    def author_name(self, obj):
        return obj.author.username

    # сколько раз добавлен в избранное
    @admin.display(description="В избранном", ordering="_fav_count")
    def favorites_total(self, obj):
        return obj._fav_count


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    search_fields = ("title", )
    list_display  = ("title", "measurement_unit", )
    filter_backends  = [filters.SearchFilter]    # ← подменили фильтр
    search_fields    = ["title"]             # icontains по умолчанию



admin.site.register(RecipeIngredient)