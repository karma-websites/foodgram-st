# <any_app>/management/commands/import_ingredients.py
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Импорт ингредиентов из CSV: «название,ед.изм.»"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=Path,
            help="Путь к CSV-файлу с ингредиентами",
        )
        parser.add_argument(
            "--delimiter",
            default=",",
            help="Символ-разделитель (по умолчанию запятая)",
        )

    def handle(self, csv_path: Path, delimiter: str, *args, **options):
        if not csv_path.exists():
            raise CommandError(f"Файл {csv_path} не найден")

        created, skipped = 0, 0
        rows = []

        with csv_path.open(encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=delimiter)
            # пропускаем заголовок, если есть
            peek = next(reader)
            if peek[0].lower().strip() in {"title", "название"}:
                pass  # уже считали заголовок
            else:
                rows.append(peek)

            rows.extend(reader)

        objs = []
        for title, unit, *_ in rows:
            title = title.strip()
            unit = unit.strip()

            if Ingredient.objects.filter(title__iexact=title).exists():
                skipped += 1
                continue

            objs.append(Ingredient(title=title, measurement_unit=unit))

        with transaction.atomic():
            Ingredient.objects.bulk_create(objs)
            created = len(objs)

        self.stdout.write(
            self.style.SUCCESS(
                f"Импорт завершён: добавлено {created}, пропущено {skipped}"
            )
        )
