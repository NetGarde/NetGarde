FROM python:3.12-alpine

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY log_config.py consumer.py api_client.py http_api.py recent_alerts.py baseline_view.py .
COPY rules/ rules/
COPY pipeline/ pipeline/

CMD ["python", "consumer.py"]
