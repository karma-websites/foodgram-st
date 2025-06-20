# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django import forms
from django.contrib.auth import get_user_model

from utils.fields import Base64ImageField as DRFBase64ImageField  # ваш DRF field

User = get_user_model()


# Адаптер для формы, чтобы админ принимал base64 или файл
class Base64OrFileImageFormField(forms.ImageField):
    def to_python(self, data):
        if hasattr(data, "read"):  # файл
            return super().to_python(data)

        if isinstance(data, str):
            drf_field = DRFBase64ImageField()
            file_obj = drf_field.to_internal_value(data)
            return super().to_python(file_obj)

        return super().to_python(data)


class CustomUserChangeForm(forms.ModelForm):
    avatar = Base64OrFileImageFormField(required=False)

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm

    list_display = (*UserAdmin.list_display, "avatar_thumb")

    fieldsets = UserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("avatar",)}),
    )

    @admin.display(description="Аватар")
    def avatar_thumb(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="32" height="32" style="object-fit:cover; border-radius:50%;" />',
                obj.avatar.url,
            )
        return "—"
