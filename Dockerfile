FROM python:3.8-slim-buster

RUN apt-get update
RUN apt-get -y install vim iproute2 curl
RUN rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

WORKDIR /app

RUN pip install -r requirements.txt

COPY src \
     entrypoint.sh \
     ./

CMD [ "/bin/bash", "/app/entrypoint.sh"]

