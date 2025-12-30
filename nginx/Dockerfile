FROM nginx


COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
## Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

CMD ["nginx", "-g", "daemon off;"]
