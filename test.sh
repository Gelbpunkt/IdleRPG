isort -rc .
black .
flake8 --extend-ignore E501,E203,E731 | grep -v "F821 undefined name '_'" # ignore the i18n builtins mod
