#!/bin/sh
set -e

# Убедимся, что каталог БД и статики существует и доступен

echo "▶ Запускаю миграции…"
python manage.py migrate         --noinput

echo "▶ Собираю статику…"
python manage.py collectstatic --noinput --clear

echo "Создаём суперпользователя (если ещё нет)…"

python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
import os

User = get_user_model()

username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
email    = os.getenv("DJANGO_SUPERUSER_EMAIL",    "admin@example.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "1234")

if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
    print(f"  › Пользователь «{username}» уже существует — пропускаем.")
else:
    User.objects.create_superuser(
        username=username, 
        email=email, 
        password=password
    )
    print(f"  ✔ Суперпользователь «{username}» создан.")
PY

python manage.py import_ingredients ./data/ingredients.csv
python manage.py create_recipes ./data/recipes.json

exec "$@"