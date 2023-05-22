FROM python:3.10.9

WORKDIR /root/uniearn/api

RUN apt-get update && \
    apt-get install -y cron

COPY poetry.lock pyproject.toml ./

RUN pip install --upgrade pip && pip install poetry

RUN poetry install

CMD ["poetry", "run", "-q", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
