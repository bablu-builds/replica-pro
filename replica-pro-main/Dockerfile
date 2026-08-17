FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY replica-pro/ /app/replica-pro/

WORKDIR /app/replica-pro
RUN pip install --no-cache-dir -e '.[dev]'

EXPOSE 8000
CMD ["rmao", "serve", "--host", "0.0.0.0", "--port", "8000"]