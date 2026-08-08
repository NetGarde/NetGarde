FROM python:3.12-alpine

WORKDIR /app
# libsnappy needed so kafka-python can decode producer batches (e.g. rpk default).
RUN apk add --no-cache snappy
COPY requirements.txt .
RUN apk add --no-cache --virtual .build-deps gcc musl-dev snappy-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps
COPY log_config.py consumer.py api_client.py http_api.py recent_alerts.py baseline_view.py .
COPY rules/ rules/
COPY pipeline/ pipeline/
COPY ai_activity/ ai_activity/

CMD ["python", "consumer.py"]
