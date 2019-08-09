FROM python:3.8.0b3-alpine3.10
COPY . /idlerpg
WORKDIR /idlerpg
RUN apk upgrade
RUN apk add musl-dev
RUN apk add zlib-dev
RUN apk add jpeg-dev
RUN apk add linux-headers
RUN apk add git
RUN apk add gcc
RUN apk add make
RUN pip install -r requirements.txt
CMD python3.8 launcher.py
