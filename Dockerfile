FROM docker.io/gelbpunkt/python:latest

LABEL maintainer="adrian@travitia.xyz" \
      description="docker image to run latest IdleRPG"

CMD ["python", "/idlerpg/launcher.py"]

RUN adduser -h /idlerpg -s /bin/false -D -H idle && \
    apk upgrade --no-cache && \
    apk add --no-cache git libgcc

USER idle
WORKDIR /idlerpg/

COPY --chown=idle:idle requirements.txt /idlerpg/

RUN pip install --no-cache-dir -i https://packages.travitia.xyz/root/idle/+simple/ --no-warn-script-location --pre --use-feature=2020-resolver -r requirements.txt

COPY --chown=idle:idle . /idlerpg/
