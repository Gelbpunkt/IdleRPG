FROM python:3.8.0rc1-alpine3.10

WORKDIR /idlerpg
COPY requirements.txt /idlerpg/

RUN apk add --no-cache --virtual .deps curl git && \
    curl -sL https://raw.githubusercontent.com/Gelbpunkt/alpine-python-3.8-wheels/master/index-order | while read p; do pip install "https://github.com/Gelbpunkt/alpine-python-3.8-wheels/raw/master/wheels/$p"; done && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .deps

CMD python3.8 launcher.py
COPY . /idlerpg
