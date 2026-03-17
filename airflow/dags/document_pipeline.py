from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

from tasks.ocr_task import run_ocr
from tasks.classify_extract_task import run_classify_and_extract
from tasks.store_mongo import store_results
from tasks.validate_task import run_validation
from tasks.update_status_task import update_status
from tasks.callbacks import on_task_failure

with DAG(
    dag_id="document_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "on_failure_callback": on_task_failure,
    }
) as dag:

    t1 = PythonOperator(task_id="ocr_task",              python_callable=run_ocr)
    t2 = PythonOperator(task_id="classify_extract_task", python_callable=run_classify_and_extract)
    t3 = PythonOperator(task_id="store_db_task",         python_callable=store_results)
    t4 = PythonOperator(task_id="validation_task",       python_callable=run_validation)
    t5 = PythonOperator(task_id="update_status_task",    python_callable=update_status)

    t1 >> t2 >> t3 >> t4 >> t5
