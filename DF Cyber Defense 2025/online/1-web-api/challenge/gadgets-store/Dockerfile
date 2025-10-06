FROM maven:3.8.5-openjdk-17-slim AS builder

WORKDIR /app

COPY src ./src
COPY pom.xml ./pom.xml

RUN mvn clean package

FROM tomcat:10.1.18-jdk17

RUN rm -rf /usr/local/tomcat/webapps/* && \
    chown -R www-data:www-data /usr/local/tomcat/

COPY --from=builder /app/target/*.war /usr/local/tomcat/webapps/ROOT.war

ENV JPDA_ADDRESS=*:8000
ENV JPDA_TRANSPORT=dt_socket

USER www-data:www-data

CMD ["catalina.sh", "jpda", "run"]