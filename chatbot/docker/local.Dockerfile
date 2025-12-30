#FROM python:3.10 
FROM ubuntu:24.04
WORKDIR /app

COPY chatbot ./
COPY .env ./.env

RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

ENV ENV=DEV

EXPOSE 3000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--workers", "1"]