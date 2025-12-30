#FROM python:3.10 
FROM archiva.tng.de:9099/de.tng/topic_modeling_base_env:3.10_latest
WORKDIR /app

COPY prod ./
COPY chatbot ./chatbot


EXPOSE 80

CMD ["python", "-m", "http.server", "80"]

