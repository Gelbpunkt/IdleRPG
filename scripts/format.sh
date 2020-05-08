#!/bin/bash
isort .
black .
flake8
