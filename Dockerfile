FROM python:3.11-alpine

RUN pip install "poetry==1.7.1"

WORKDIR /app
COPY poetry.lock pyproject.toml /app/

RUN poetry config virtualenvs.create false \
  && poetry install --only main --no-interaction --no-ansi

COPY tgsteg /app/tgsteg
ENV PYTHONPATH=.
ENTRYPOINT [ "python", "tgsteg/bot.py" ]
