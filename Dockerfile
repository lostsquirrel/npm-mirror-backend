FROM registry.lisong.pub:5000/lisong/npm-mirror-backend-base:3.2.0

ADD . /app/
VOLUME /data

CMD python3 /app/main.py