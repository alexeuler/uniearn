FROM python:3.10.9

WORKDIR /root/uniearn/api

RUN apt-get update && \
    apt-get install -y cron

COPY poetry.lock pyproject.toml ./

RUN pip install --upgrade pip && pip install poetry

RUN poetry install

CMD ["/root/uniearn/start_cron.sh"]
