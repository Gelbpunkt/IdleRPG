FROM docker.io/gelbpunkt/python:gcc10

RUN adduser -S idle && \
    apk upgrade --no-cache && \
    apk add --no-cache git libgcc

USER idle
WORKDIR /idlerpg

COPY requirements.txt /idlerpg/

RUN pip install --no-cache-dir -i https://packages.travitia.xyz/root/idle/+simple/ --no-warn-script-location --pre --use-feature=2020-resolver -r requirements.txt

COPY . /idlerpg/

RUN git remote set-url origin https://git.travitia.xyz/Kenvyra/IdleRPG.git

CMD python launcher.py
