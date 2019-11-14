FROM python:3.8.0-alpine3.10

WORKDIR /idlerpg
COPY requirements.txt /idlerpg/

RUN apk add --no-cache curl git && \
    curl -sL https://raw.githubusercontent.com/Gelbpunkt/alpine-python-3.8-wheels/master/index-order | while read p; do pip install "https://github.com/Gelbpunkt/alpine-python-3.8-wheels/raw/master/wheels/$p"; done && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del curl

COPY . /idlerpg

# fix git remote url from ssh to https
RUN git remote set-url origin https://git.travitia.xyz/kenvyra/IdleRPG.git

CMD python launcher.py
