FROM gelbpunkt/python:latest

WORKDIR /idlerpg
ARG beta

RUN if [ -z "$beta" ]; then \
        echo "INFO: Building release version!"; \
    else \
        echo "INFO: Building beta version!"; \
    fi && \
    sleep 3 && \
    set -ex && \
    adduser -S idle && \
    apk add --no-cache --virtual .fetch-deps curl && \
    if [[ "$(uname -m)" = "x86_64" && "$beta" ]]; then \
        BRANCH="3.9-x86_64-beta"; \
    elif [ "$(uname -m)" = "x86_64" ]; then \
        BRANCH="3.9-x86_64"; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        BRANCH="3.9-aarch64"; \
    else \
        echo "Unsupport architecture" && exit 1; \
    fi && \
    curl -sL "https://raw.githubusercontent.com/Gelbpunkt/alpine-python-wheels/$BRANCH/index-order" \
    | while read p; do \
        pip install --no-deps --no-cache-dir "https://github.com/Gelbpunkt/alpine-python-wheels/raw/$BRANCH/wheels/$p"; \
    done && \
    apk del .fetch-deps --no-network && \
    apk add --no-cache git util-linux

USER idle

COPY . .

# Fix git URL in Dockerhub
RUN git remote set-url origin https://git.travitia.xyz/Kenvyra/IdleRPG.git

CMD python launcher.py
