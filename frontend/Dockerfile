# Build the SPA, then serve it from nginx running as an unprivileged user.
FROM node:24.21.0-alpine3.24 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Listens on 8080 and runs as uid 101: https://github.com/nginx/docker-nginx-unprivileged
FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24
# Replaces the main config, because worker_processes is only valid there, not in a conf.d include.
COPY nginx.conf /etc/nginx/nginx.conf
# The entrypoint fills this in at start, into /tmp, the one folder the read-only container can write:
# the DNS server from /etc/resolv.conf, and API_HOST. https://github.com/nginx/docker-nginx/tree/master/entrypoint
COPY nginx-upstream.conf.template /etc/nginx/templates/upstream.conf.template
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 NGINX_ENVSUBST_OUTPUT_DIR=/tmp API_HOST=api
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
