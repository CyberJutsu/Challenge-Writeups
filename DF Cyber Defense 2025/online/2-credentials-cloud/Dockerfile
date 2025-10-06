FROM ubuntu:24.04

ENV NODE_ENV=production \
    PORT=8080 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates tzdata bash file strace curl \
       init-system-helpers adduser passwd util-linux procps psmisc \
       nodejs npm nginx supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=root:root package.json package-lock.json ./
RUN npm install --omit=dev

# copy only runtime application code
RUN mkdir -p /app/src/static
COPY --chown=root:root src/server.js ./src/server.js
COPY --chown=root:root src/jwt.js ./src/jwt.js
COPY --chown=root:root lib ./lib
COPY --chown=root:root assets/app.js ./src/static/app.js

# Copy runtime configuration and entrypoint
COPY --chown=root:root nginx/default.conf /etc/nginx/nginx.conf
COPY --chown=root:root docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN find /app -type d -exec chmod 0755 {} \; \
    && find /app -name .git -prune -o -type f -exec chmod 0644 {} \;

EXPOSE 80 8080

# Create supervisor configuration for running both nginx and node
RUN mkdir -p /etc/supervisor/conf.d
RUN echo '[supervisord]\n\
nodaemon=true\n\
user=root\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
\n\
[program:app]\n\
command=/usr/local/bin/docker-entrypoint.sh\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0' > /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
