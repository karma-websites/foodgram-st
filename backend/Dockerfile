# Use a slim Python image as the base
FROM python:3.12-slim

# чтобы не создавать файлы __pycache__
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

COPY requirements.txt .

# обновляем pip, а потом ставим зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 4. Теперь копируем всё приложение
COPY . /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 5. Создаём пользователя и выдаём права
RUN useradd -m django \
    && chown -R django:django /app /entrypoint.sh

USER django

# 6. Добавляем entrypoint
ENTRYPOINT ["/entrypoint.sh"]


EXPOSE 8000
CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000"]