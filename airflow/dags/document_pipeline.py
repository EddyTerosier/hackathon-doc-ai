from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def ocr():
    print("OCR")

def classify():
    print("classification")

def extract():
    print("extraction")

def validate():
    print("validation")

def store():
    print("mongo")

with DAG(
    "document_pipeline",
    start_date=datetime(2024,1,1),
    schedule=None,
    catchup=False
) as dag:

    t1 = PythonOperator(task_id="ocr", python_callable=ocr)
    t2 = PythonOperator(task_id="classify", python_callable=classify)
    t3 = PythonOperator(task_id="extract", python_callable=extract)
    t4 = PythonOperator(task_id="validate", python_callable=validate)
    t5 = PythonOperator(task_id="store", python_callable=store)

    t1 >> t2 >> t3 >> t4 >> t5


""" from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

from tasks.ocr_task import run_ocr
from tasks.classify_task import run_classification
from tasks.extract_task import run_extraction
from tasks.validate_task import run_validation
from tasks.store_mongo import store_results

with DAG(
    dag_id="document_pipeline",
    start_date=datetime(2024,1,1),
    schedule_interval=None,
    catchup=False
) as dag:

    ocr_task = PythonOperator(
        task_id="ocr_task",
        python_callable=run_ocr
    )

    classification_task = PythonOperator(
        task_id="classification_task",
        python_callable=run_classification
    )

    extraction_task = PythonOperator(
        task_id="extraction_task",
        python_callable=run_extraction
    )

    validation_task = PythonOperator(
        task_id="validation_task",
        python_callable=run_validation
    )

    store_mongo = PythonOperator(
        task_id="store_mongo",
        python_callable=store_results
    )

    ocr_task >> classification_task >> extraction_task >> validation_task >> store_mongo """