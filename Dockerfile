# Dockerfile для продакшена
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python пакеты
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Собираем статику
RUN python manage.py collectstatic --noinput

# Открываем порт
EXPOSE 8000

# Команда запуска
CMD ["gunicorn", "soju_seoul.wsgi:application", "--bind", "0.0.0.0:8000"]
