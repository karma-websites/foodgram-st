from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework.response import Response

from utils.pagination import CustomPage
from utils.fields import Base64ImageField
from .models import User, Subscription
from .serializers import (
    UserSerializer, UserCreateSerializer,
    SubscriptionSerializer, PasswordChangeSerializer
)


def make_paginated_response(viewset, qs, serializer_cls):
    """Унифицированная страница-ответ."""
    page = viewset.paginate_queryset(qs)
    ser  = serializer_cls(page, many=True, context={"request": viewset.request})
    return viewset.get_paginated_response(ser.data)



def handle_subscribe(request, author, model, err_exist, err_absent):
    """
    Общая логика POST / DELETE для подписок / корзины / избранного
    (здесь нужна только для подписок).
    """
    follower = request.user 

    # ---------- PSOT ----------
    if request.method == "POST":
        if model.objects.filter(follower=follower, author=author).exists():
            return Response({"errors": err_exist}, status=400)

        sub = model.objects.create(follower=follower, author=author)  # ← sub

        serializer = SubscriptionSerializer(
            sub,                                   # передаём подписку
            context={"request": request},
        )
        return Response(serializer.data, status=201)

    # ---------- DELETE ----------
    qs = model.objects.filter(follower=follower, author=author)
    if not qs.exists():
        return Response({"errors": err_absent}, status=400)

    qs.delete()
    return Response(status=204)


# ──────────────────────────── permissions ------------------------------------
class IsAuthorOrReadOnly(BasePermission):
    """SAFE методы — всем; модификация — только автору."""
    def has_permission(self, rq, v):
        return rq.method in SAFE_METHODS or rq.user.is_authenticated

    def has_object_permission(self, rq, v, obj):
        return rq.method in SAFE_METHODS or obj.author == rq.user



class UserViewSet(viewsets.ModelViewSet):
    """ /api/users """

    queryset           = User.objects.all().order_by("date_joined")
    serializer_class   = UserSerializer
    pagination_class   = CustomPage


    # --- сериализаторы -------------------------------------------------------
    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        else: 
            return UserSerializer


    # --- права доступа -------------------------------------------------------
    def get_permissions(self):
        # список пользователей и регистрация — публично
        if self.action in ("list", "create", "retrieve"):
            return [AllowAny()]
        # всё остальное → нужна авторизация
        return [IsAuthenticated()]


    # --- actions      --------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        return Response(self.get_serializer(request.user).data)
    

    @action(
        detail=False,
        methods=["post"],
        url_path="set_password",
        permission_classes=[IsAuthenticated],
    )
    def set_password(self, request):
        """
        POST /api/users/set_password/
        {
            "current_password": "oldPass123",
            "new_password":     "New_Pass987"
        }
        """
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        return Response(status=204)


    # /api/users/me/avatar/
    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[IsAuthenticated],
        parser_classes=[JSONParser],  # файл ИЛИ base64-json
    )
    def my_avatar(self, request):
        user = request.user

        class AvatarSerializer(serializers.Serializer):
            avatar = Base64ImageField(required=True)

        # -------- PUT: добавить или заменить аватар --------
        if request.method == "PUT":
            ser = AvatarSerializer(data=request.data, context={"request": request})
            ser.is_valid(raise_exception=True)

            user.avatar = ser.validated_data["avatar"]   # always exists
            user.save(update_fields=["avatar"])
            return Response({"avatar": user.avatar.url}, status=200)


        # -------- DELETE: убрать аватар (сбросить) --------
        user.avatar.delete(save=False)
        user.avatar = ""         
        user.save(update_fields=["avatar"])
        return Response(status=204)


    # /api/users/{id}/subscribe
    @action(
            detail=True, methods=["post", "delete"], url_path="subscribe",
            permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()           # пользователь, на которого подписываемся

        if author == request.user:
            return Response({"errors": "Нельзя подписаться на себя"}, status=400)
        return handle_subscribe(
            request, author, Subscription,
            err_exist="Уже подписаны", err_absent="Подписка не найдена"
        )
        

    # --- /users/subscriptions/ ---
    @action(
        detail=False, methods=["get"], url_path="subscriptions",
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        qs = Subscription.objects.filter(follower=request.user).select_related("author")
        return make_paginated_response(self, qs, SubscriptionSerializer)