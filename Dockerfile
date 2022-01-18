FROM docker.io/gelbpunkt/python:3.11

ARG IS_CUSTOM=false

LABEL maintainer="adrian@travitia.xyz" \
    description="docker image to run latest IdleRPG"

CMD ["python", "-OO", "/idlerpg/launcher.py"]

RUN mkdir /idlerpg && \
    adduser -h /idlerpg -s /bin/false -D -H idle && \
    chown -R idle:idle /idlerpg && \
    apk add --no-cache libgcc

USER idle
WORKDIR /idlerpg/

COPY --chown=idle:idle requirements.txt /idlerpg/
COPY --chown=idle:idle requirements-custom.txt /idlerpg/

RUN if [ "$IS_CUSTOM" == 'true' ]; then \
        pip install \
            --no-cache-dir \
            -i https://packages.travitia.xyz/root/idle/+simple/ \
            --no-warn-script-location \
            --pre \
            -r requirements-custom.txt; \
    else \
        pip install \
            --no-cache-dir \
            -i https://packages.travitia.xyz/root/idle/+simple/ \
            --no-warn-script-location \
            --pre \
            -r requirements.txt; \
    fi

COPY --chown=idle:idle . /idlerpg/
