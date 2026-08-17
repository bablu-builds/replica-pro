FROM python:3.11-slim

WORKDIR /app

# Copy only requirements first for caching
COPY replica-pro/pyproject.toml replica-pro/setup.py /app/replica-pro/
COPY replica-pro/src/ /app/replica-pro/src/
COPY replica-pro/README.md /app/replica-pro/

RUN pip install --no-cache-dir -e /app/replica-pro/[dev]

EXPOSE 8000

CMD ["rmao", "serve", "--host", "0.0.0.0", "--port", "8000"]
