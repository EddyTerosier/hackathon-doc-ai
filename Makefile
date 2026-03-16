PYTHON=python

dataset-generate:
	$(PYTHON) dataset/generate_base_dataset.py

dataset-clean:
	$(PYTHON) dataset/clean_generated_pdfs.py

dataset-reset: dataset-clean dataset-generate