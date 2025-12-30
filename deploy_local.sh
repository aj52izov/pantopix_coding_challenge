#!/bin/bash
# Configuration

# NGINX
NGINX_IMAGE_TAG="pantopix_rag_chatbot_nginx:latest" # Name of your Docker image
NGINX_DOCKER_FILE="./nginx/Dockerfile"          # Path to your Dockerfile
NGINX_CONTEXT="./nginx"          # Path to your Dockerfile

# frontend
FRONTEND_IMAGE_TAG="pantopix_rag_chatbot_frontend:latest"
FRONTEND_DOCKER_FILE="./frontend/docker/local.Dockerfile"
FRONTEND_CONTEXT="./frontend"

# rag_chatbot
IMAGE_TAG="pantopix_rag_chatbot_backend:latest"
STACK_NAME="pantopix_rag_chatbot"            # Name of your Docker stack
DOCKER_FILE="./chatbot/docker/local.Dockerfile" # Path to your Dockerfile
COMPOSE_FILE="./chatbot/docker/local_docker-compose.yml" # Path to your Docker Compose file
STACK_NAME_APP="pantopix_rag_chatbot-backend-1"            # Name of your Docker stack
CONTEXT=.

## get the argument that check if the user want to delete the docker image or not
DELETE_IMGS=$1

# Unset Docker environment variables
unset DOCKER_HOST
unset DOCKER_TLS_VERIFY

# delete the images if DELETE_IMGS
if [ "$DELETE_IMGS" == "true" ];
then
    echo "deleting local images"
    docker rmi $IMAGE_TAG --force
    docker rmi $FRONTEND_IMAGE_TAG --force
    docker rmi $NGINX_IMAGE_TAG --force
fi

# NGINX
echo "Building rag_chatbot_nginx Docker image..."
docker build -t $NGINX_IMAGE_TAG -f $NGINX_DOCKER_FILE $NGINX_CONTEXT

# frontend
echo "Building rag_chatbot_frontend Docker image..."
docker build -t $FRONTEND_IMAGE_TAG -f $FRONTEND_DOCKER_FILE $FRONTEND_CONTEXT

# APP
echo "Building rag_chatbot_faq_nginx-nginx Docker image..."
docker build -t $IMAGE_TAG -f $DOCKER_FILE $CONTEXT

# delete the stack if it exists
echo "Removing existing deployemnt"
docker compose -f $COMPOSE_FILE down 
sleep 10

# Deploy the stack to Docker Swarm
echo "Deploying the compose "
docker compose -f $COMPOSE_FILE -p $STACK_NAME up -d

# Check the logs of the rag_chatbot service
echo "log check"
docker container logs $STACK_NAME_APP --follow