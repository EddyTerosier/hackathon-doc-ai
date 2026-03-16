import sys
sys.path.append("/opt/airflow")

from backend.extraction.classifier import extract


def run_extraction(**context):
    ti = context["ti"]

    text = ti.xcom_pull(task_ids="ocr_task")

    result = extract(text)

    return result.to_dict()
