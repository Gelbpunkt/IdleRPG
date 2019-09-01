FROM python:3.8.0b3-alpine3.10

WORKDIR /idlerpg
COPY requirements.txt /idlerpg/

RUN apk add --no-cache musl-dev zlib-dev jpeg-dev freetype-dev linux-headers git gcc make libtool automake m4 autoconf && \
    pip install git+https://github.com/cython/cython && \
    pip install -r requirements.txt

CMD python3.8 launcher.py
COPY . /idlerpg
