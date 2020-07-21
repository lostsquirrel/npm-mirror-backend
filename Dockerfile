FROM registry.lisong.pub:5000/lisong/npm-mirror-backend-base:3.1.0

ADD main.py clean.py /app/
VOLUME /data

CMD python3 /app/main.py