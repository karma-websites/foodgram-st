import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from recipes.models import Ingredient, Recipe, RecipeIngredient


class Command(BaseCommand):
    """
    Пример:
        python manage.py create_default_recipes                 # берёт default_recipes.json
        python manage.py create_default_recipes data/my.json    # свой JSON
        python manage.py create_default_recipes --reset         # удалить старые
    """

    help = "Создаёт набор стандартных рецептов из JSON-файла."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            nargs="?",
            default=None,
            help="Путь к JSON-файлу с рецептами (по умолчанию default_recipes.json рядом с командой)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить созданные ранее стандартные рецепты перед загрузкой.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Загружаем JSON --------------------------------------------------
        json_file = self._resolve_json_path(options["json_path"])
        self.stdout.write(f"Читаю данные из: {json_file}")

        try:
            with json_file.open(encoding="utf-8") as fp:
                recipes_data = json.load(fp)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Невалидный JSON: {exc}") from exc

        if not isinstance(recipes_data, list):
            raise CommandError("Корень JSON должен быть списком рецептов.")

        # 2. Автор bot --------------------------------------------------------
        User = get_user_model()
        author, _ = User.objects.get_or_create(
            username="recipes_bot",
            defaults=dict(
                first_name="Recipes",
                last_name="Bot",
                email="recipes_bot@example.com",
                password="_Pa$SW0RD!",
                is_staff=False,
                is_active=True,
            ),
        )

        # 3. Создаём ----------------------------------------------------------
        created, skipped = 0, 0
        for data in recipes_data:
            recipe, is_created = Recipe.objects.get_or_create(
                author=author,
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "cooking_time": data["cooking_time"],
                    "image": data["image"],
                },
            )
            if not is_created:
                skipped += 1
                continue

            # ингредиенты
            bulk = []
            for ing in data["ingredients"]:
                ingredient, _ = Ingredient.objects.get_or_create(
                    title=ing["name"],          # поправь, если у тебя поле `name`
                    measurement_unit=ing["measurement_unit"],
                )
                bulk.append(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=ing["amount"],
                    )
                )
            RecipeIngredient.objects.bulk_create(bulk)

            created += 1
            self.stdout.write(f"✓ {recipe.title}")

        # 5. Итог -------------------------------------------------------------
        self.stdout.write(
            self.style.SUCCESS(f"Готово! Создано: {created}, пропущено: {skipped}")
        )

    # --------------------------------------------------------------------- #
    # Вспомогательные методы                                                #
    # --------------------------------------------------------------------- #
    def _resolve_json_path(self, cli_path: str | None) -> Path:
        """
        Возвращает Path к JSON-файлу.
        Если путь не указан, берёт default_recipes.json рядом с этим файлом.
        """
        if cli_path:
            path = Path(cli_path).expanduser().resolve()
        else:
            path = Path(__file__).with_name("default_recipes.json")

        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")

        if path.suffix.lower() != ".json":
            raise CommandError("Файл должен быть с расширением .json")

        return path
