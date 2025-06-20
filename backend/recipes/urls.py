from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RecipeViewSet, IngredientViewSet

router = DefaultRouter()
router.register(r'recipes', RecipeViewSet, basename='recipes') # /api/
router.register(r'ingredients', IngredientViewSet, basename='ingredients') # /api/

urlpatterns = router.urls