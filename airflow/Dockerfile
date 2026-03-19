FROM apache/airflow:3.1.8-python3.12

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data/raw /data/clean /data/curated \
    && chmod -R 777 /data

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY dags/ /opt/airflow/dags/
USER root
COPY start-airflow.sh /start-airflow.sh
RUN sed -i 's/\r$//' /start-airflow.sh
RUN chmod +x /start-airflow.sh
USER airflow

