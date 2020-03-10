FROM gelbpunkt/python:latest

WORKDIR /idlerpg
COPY requirements.txt .

RUN apk add --no-cache curl git util-linux && \
    curl -sL https://raw.githubusercontent.com/Gelbpunkt/alpine-python-wheels/3.9/index-order | while read p; do pip install "https://github.com/Gelbpunkt/alpine-python-wheels/raw/3.9/wheels/$p"; done && \
    apk del curl

COPY . .

# Fix git URL in Dockerhub
RUN git remote set-url origin https://git.travitia.xyz/Kenvyra/IdleRPG.git

CMD python launcher.py
