FROM python:3.10.9

WORKDIR /root/uniearn/data

RUN apt-get update && \
    apt-get install rsyslog -y && \
    apt-get install -y cron

COPY poetry.lock pyproject.toml ./

RUN pip install --upgrade pip && pip install poetry

RUN poetry install

CMD ["/root/uniearn/data/start_cron.sh"]
