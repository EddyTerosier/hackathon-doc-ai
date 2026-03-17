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