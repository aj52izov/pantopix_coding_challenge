
FROM python:3.10
WORKDIR /app

COPY local ./
COPY chatbot ./chatbot


EXPOSE 80

CMD ["python", "-m", "http.server", "80"]
