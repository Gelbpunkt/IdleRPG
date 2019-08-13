#!/bin/bash
isort -rc .
black .
flake8
