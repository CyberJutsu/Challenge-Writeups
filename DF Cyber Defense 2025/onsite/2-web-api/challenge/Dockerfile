FROM node:22-alpine

WORKDIR /app

RUN apk add --no-cache openssl curl

COPY package*.json pnpm-lock.yaml ./

RUN npm install -g pnpm

RUN pnpm install

COPY . .

RUN pnpm db:generate

EXPOSE 25001 

CMD [ "pnpm", "run", "start" ]
