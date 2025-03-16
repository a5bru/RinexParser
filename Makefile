VIRTUALENV_DIR=env

cleanPYco:
	find . -name '*.pyc' -exec rm --force {} \;
	find . -name '*.pyo' -exec rm --force {} \;

cleanBuild:
	rm --force --recursive build/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info

cleanVenv:
	rm -rf $(VIRTUALENV_DIR)

cleanAll: cleanBuild cleanVenv cleanPYco


isort:
	sh -c "isort --skip-glob=.tox --recursive . "

lint:
	flake8 --exclude=.tox

buildEgg:
	pipenv run python setup.py bdist_wheel

prepareVenv:
	virtualenv --python=python3 ${VIRTUALENV_DIR}

setupVenv:
	pip install -r requirements.txt

test: cleanPYco
	nosetests tests

.PHONY: init test
