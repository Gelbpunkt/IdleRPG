FROM python:3.8.1-alpine3.11

WORKDIR /idlerpg
COPY requirements.txt .

RUN apk add --no-cache curl git && \
    curl -sL https://raw.githubusercontent.com/Gelbpunkt/alpine-python-3.8-wheels/master/index-order | while read p; do pip install "https://github.com/Gelbpunkt/alpine-python-3.8-wheels/raw/master/wheels/$p"; done && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del curl

COPY . .

CMD python launcher.py
