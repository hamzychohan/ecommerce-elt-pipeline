FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app
ENV HOME=/home/appuser
ENV DUCKDB_PATH=/app/warehouse/ecommerce.duckdb

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_app.txt requirements_dbt.txt requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements_app.txt -r requirements_dbt.txt

COPY . .
RUN chmod +x docker-entrypoint.sh
RUN useradd --create-home appuser && chown -R appuser:appuser ${APP_HOME}

USER appuser
WORKDIR ${APP_HOME}

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
