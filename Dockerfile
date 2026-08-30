FROM python:3.11-slim-bookworm

WORKDIR /app
COPY app/ /app/app/

CMD ["python", "-u", "app/main.py"]