FROM registry.lisong.pub:28500/lisong/npm-mirror-backend-base:3.3.0

ADD . /app/
VOLUME /data

CMD python3 /app/main.py