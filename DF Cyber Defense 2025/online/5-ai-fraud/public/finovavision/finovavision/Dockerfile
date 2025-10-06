FROM python:3.12-slim

WORKDIR /app

COPY src/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY data/ /data/
COPY src/ ./

EXPOSE 10001

CMD ["flask", "run", "--host=0.0.0.0", "--port=10001"]
