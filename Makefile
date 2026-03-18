PYTHON=python

dataset-generate:
	$(PYTHON) dataset/generate_base_dataset.py

dataset-clean:
	$(PYTHON) dataset/clean_generated_pdfs.py

dataset-reset: dataset-clean dataset-generate

dataset-images-generate:
	$(PYTHON) dataset/generate_base_images.py

dataset-images-clean:
	$(PYTHON) dataset/clean_generated_images.py

dataset-images-reset: dataset-images-clean dataset-images-generate

test:
	$(PYTHON) -m pytest

test-fast:
	$(PYTHON) -m pytest --no-header -q --override-ini="addopts="

pipeline-up:
    docker-compose up airflow mongo mongo-express -d

pipeline-test:
    cd scripts && AIRFLOW_PASSWORD=$$(docker exec hackathon-airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated | python3 -c "import sys,json; print(list(json.load(sys.stdin).values())[0])") python test_pipeline.py
