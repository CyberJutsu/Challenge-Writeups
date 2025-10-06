FROM node:18-alpine
WORKDIR /app
RUN npm install -g typescript ts-node nodemon
EXPOSE 3000
CMD ["tail", "-f", "/dev/null"]
