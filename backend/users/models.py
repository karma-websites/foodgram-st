from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from app import settings

# Create your models here.

def user_avatar_path(instance: "User", filename: str) -> str:

    return f'users/avatars/{instance.pk}/{filename}'

class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra):
        if not email:
            raise ValueError("E-mail обязателен")
        if not username:
            raise ValueError("Username обязателен")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, username, password, **extra)


class Subscription(models.Model):
    """User -> Author (self-referencing)"""
    follower  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="following_relations",
        on_delete=models.CASCADE
    )
    author    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="follower_relations",
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "author")
        ordering        = ["-created_at"]

    def __str__(self):
        return f"{self.follower} → {self.author}"


class User(AbstractBaseUser, PermissionsMixin):
    avatar = models.ImageField(
        upload_to=user_avatar_path,
        blank=True,                          # поле необязательно
        default='users/avatars/default.png'  # можно задать картинку-заглушку
    )

    email       = models.EmailField(max_length=150, unique=True)
    username    = models.CharField(max_length=255,  unique=True)
    first_name  = models.CharField(max_length=150)
    last_name   = models.CharField(max_length=150) 
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # «подписки, за кем я слежу»
    following = models.ManyToManyField(
        "self",
        symmetrical=False,
        through="Subscription",
        related_name="followers",
    )

    USERNAME_FIELD  = "email"          # ← ЛОГИНИМСЯ ПО E-MAIL!
    REQUIRED_FIELDS = ["username"]     # ← Но username обязателен

    objects = UserManager()

    def __str__(self):
        return self.email