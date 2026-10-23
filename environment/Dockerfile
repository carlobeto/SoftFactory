FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias si fueran necesarias
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY workspace/ /app/

CMD ["python3", "main.py", "--help"]
