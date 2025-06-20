# utils/fields.py
import base64
import binascii
import imghdr
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    """
    Принимает как обычный «file upload», так и строку base64
    формата data:<mimetype>;base64,<код>. Декодирует и отдаёт
    Django-файлу ContentFile, годный для ImageField/Storage.
    """

    # Допустимые типы изображений (imghdr.what возвращает эти строки)
    ALLOWED_TYPES = {"jpeg", "png", "gif", "bmp", "tiff", "webp"}

    def to_internal_value(self, data):
        # 1️⃣  Если это уже файл (мультимимедийная форма), работаем «как обычно»
        if isinstance(data, (bytes, bytearray)):
            raise serializers.ValidationError("Ожидалась строка base64 или файл, а получены байты.")
        if hasattr(data, "read"):
            # например, <InMemoryUploadedFile>
            return super().to_internal_value(data)

        # 2️⃣  Если пришла строка — проверяем префикс и вырезаем «data:image/...;base64,»
        if isinstance(data, str):
            if "base64," in data:
                header, data = data.split("base64,", 1)
            if not data:
                raise serializers.ValidationError("Пустая строка base64.")

            # 3️⃣  Пробуем декодировать
            try:
                decoded_file = base64.b64decode(data, validate=True)
            except (TypeError, ValueError, binascii.Error):
                raise serializers.ValidationError("Невалидное изображение — не удалось декодировать base64.")

            # 4️⃣  Определяем формат (imghdr смотрит по сигнатуре байтов)
            file_format = imghdr.what(None, decoded_file)
            if file_format == "jpg":
                file_format = "jpeg"
            if file_format not in self.ALLOWED_TYPES:
                raise serializers.ValidationError(f"Неподдерживаемый тип изображения: {file_format}")

            # 5️⃣  Генерируем уникальное имя
            file_name = f"{uuid.uuid4().hex[:16]}.{file_format}"

            # 6️⃣  Оборачиваем в ContentFile — Django сможет сохранить
            data = ContentFile(decoded_file, name=file_name)

            # 7️⃣  Передаём «вверх» в стандартный ImageField для финальной валидации
            return super().to_internal_value(data)

        raise serializers.ValidationError("Неверный тип данных — ожидается файл либо строка base64.")