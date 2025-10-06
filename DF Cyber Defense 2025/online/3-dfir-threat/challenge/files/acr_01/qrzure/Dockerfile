FROM node:18-alpine
WORKDIR /app
COPY --chown=node:node package*.json ./
RUN npm ci --only=production && npm cache clean --force
COPY --chown=node:node app.js ./
COPY --chown=node:node src/ ./src/
COPY --chown=node:node views/ ./views/
COPY --chown=node:node public/ ./public/
ENV NODE_ENV=production PORT=3000
EXPOSE 3000
USER node
CMD ["node","app.js"]