FROM python:3.8.0b4-alpine3.10

WORKDIR /idlerpg
COPY requirements.txt /idlerpg/

RUN apk add --no-cache --virtual .build-deps git gcc  musl-dev linux-headers make automake libtool m4 autoconf && \
    pip install --no-cache-dir git+https://github.com/cython/cython && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

CMD python3.8 launcher.py
COPY . /idlerpg
