FROM nginx:alpine

# Copy index.html
COPY index.html /usr/share/nginx/html/index.html.template

# Default value for BACKEND_URL
ENV BACKEND_URL=http://localhost:8080

# Use envsubst to replace BACKEND_URL in index.html and then start nginx
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]
