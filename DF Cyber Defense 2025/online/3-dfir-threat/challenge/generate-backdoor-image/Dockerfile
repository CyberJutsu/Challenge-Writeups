FROM node:18-alpine
WORKDIR /app
COPY app.js .
COPY flag .
COPY entrypoint.sh .
RUN rm -rf ./flag && echo "Try to read me"
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
