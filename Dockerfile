FROM gelbpunkt/python:latest

WORKDIR /idlerpg

RUN apk add --no-cache curl git util-linux && \
    curl -sL "https://raw.githubusercontent.com/Gelbpunkt/alpine-python-wheels/3.9-$(uname -m)/index-order" | while read p; do pip install --no-deps "https://github.com/Gelbpunkt/alpine-python-wheels/raw/3.9-$(uname -m)/wheels/$p"; done && \
    apk del curl

COPY . .

# Fix git URL in Dockerhub
RUN git remote set-url origin https://git.travitia.xyz/Kenvyra/IdleRPG.git

CMD python launcher.py
