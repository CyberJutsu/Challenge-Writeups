FROM maven:3.8.3-openjdk-17-slim AS build

WORKDIR /src
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY src ./src
RUN mvn -q -DskipTests package

FROM openjdk:17-jdk
ARG FLAG

WORKDIR /app
COPY --from=build /src/target/app.jar /app/app.jar
RUN echo "$FLAG" > /$(openssl rand -hex 9)-flag.txt

# RUN chown -R www-data:www-data /app
# USER www-data
USER 1000:1000

ENTRYPOINT ["java","-jar","/app/app.jar"]


