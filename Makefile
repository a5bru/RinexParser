VIRTUALENV_DIR=env

clean-pyc:
	find . -name '*.pyc' -exec rm -v --force {} \;
	find . -name '*.pyo' -exec rm -v --force {} \;

clean-build:
	rm --force --recursive build/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info

clean-venv:
	( \
		rm -rf $(VIRTUALENV_DIR); \
	)

isort:
	sh -c "isort --skip-glob=.tox --recursive . "

lint:
	flake8 --exclude=.tox

prepare:
	virtualenv --python=python3 ${VIRTUALENV_DIR}

install:
	pip install -r requirements.txt

init: prepare
	install

test: clean-pyc
	nosetests tests

.PHONY: init test
