FROM docker.io/gelbpunkt/python:3.11

LABEL maintainer="adrian@travitia.xyz" \
      description="docker image to run latest IdleRPG"

CMD ["python", "-OO", "/idlerpg/launcher.py"]

RUN mkdir /idlerpg && \
    adduser -h /idlerpg -s /bin/false -D -H idle && \
    chown -R idle:idle /idlerpg && \
    apk upgrade --no-cache && \
    apk add --no-cache git libgcc

USER idle
WORKDIR /idlerpg/

COPY --chown=idle:idle requirements.txt /idlerpg/

RUN pip install --no-cache-dir -i https://packages.travitia.xyz/root/idle/+simple/ --no-warn-script-location --pre -r requirements.txt

COPY --chown=idle:idle . /idlerpg/
