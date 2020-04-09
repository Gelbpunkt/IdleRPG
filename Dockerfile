FROM gelbpunkt/python:latest

WORKDIR /idlerpg

RUN apk add --no-cache curl git util-linux jpeg-dev zlib-dev && \
    curl -sL "https://raw.githubusercontent.com/Gelbpunkt/alpine-python-wheels/3.9-$(uname -m)/index-order" | while read p; do pip install --no-deps "https://github.com/Gelbpunkt/alpine-python-wheels/raw/3.9-$(uname -m)/wheels/$p"; done && \
    curl -L "https://github.com/Gelbpunkt/alpine-stockfish/raw/$(uname -m)/stockfish" -o stockfish && \
    chmod +x stockfish && \
    curl -L "https://github.com/Gelbpunkt/alpine-stockfish/raw/$(uname -m)/Vajolet" -o Vajolet && \
    chmod +x Vajolet && \
    apk del curl && \
    apk add cairo-dev --repository http://dl-cdn.alpinelinux.org/alpine/v3.11/main

COPY . .

# Fix git URL in Dockerhub
RUN git remote set-url origin https://git.travitia.xyz/Kenvyra/IdleRPG.git

CMD python launcher.py
