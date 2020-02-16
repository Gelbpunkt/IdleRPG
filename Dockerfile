FROM python:3.9.0a3-alpine3.10

WORKDIR /idlerpg
COPY requirements.txt .

RUN sed -i "s:v3.10:edge:g" /etc/apk/repositories && \
    apk update && apk upgrade && \
    apk add --no-cache curl git && \
    curl -sL https://raw.githubusercontent.com/Gelbpunkt/alpine-python-wheels/3.9/index-order | while read p; do pip install "https://github.com/Gelbpunkt/alpine-python-wheels/raw/3.9/wheels/$p"; done && \
    apk del curl && \
    sed -i "s:v3.10.4:v3.11.3:g" /etc/os-release /etc/alpine-release && \
    sed -i "s:v3.10:v3.11:g" /etc/os-release

COPY . .

# Fix git URL in Dockerhub
RUN git remote set-url origin https://git.travitia.xyz/Kenvyra/IdleRPG.git

CMD python launcher.py
