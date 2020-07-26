FROM docker.io/gelbpunkt/python:3.10

ARG beta

RUN adduser -S idle && \
    apk upgrade --no-cache && \
    apk add --no-cache git libgcc

WORKDIR /idlerpg

COPY . .

RUN git remote set-url origin https://git.travitia.xyz/Kenvyra/IdleRPG.git && \
    chown -R idle:nogroup .

USER idle

RUN pip install --no-cache-dir -i https://packages.travitia.xyz/root/idle/+simple/ --no-warn-script-location --pre -r requirements.txt

CMD python launcher.py
