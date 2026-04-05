VENV := venv
PYTHON := $(VENV)/bin/python3.12
PIP := $(VENV)/bin/pip

.PHONY: venv install run migrate seed test shell

venv:
	python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	source

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) manage.py runserver

migrate:
	$(PYTHON) manage.py makemigrations
	$(PYTHON) manage.py migrate

seed:
	$(PYTHON) manage.py seed_data

test:
	$(PYTHON) manage.py test

shell:
	$(PYTHON) manage.py shell
