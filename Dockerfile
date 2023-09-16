FROM python:3.11-slim-buster

WORKDIR /app

RUN apt-get update \
    && pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .
CMD [ "python3", "-u", "app.py"]