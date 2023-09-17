FROM python:3.11-slim-buster

WORKDIR /app

RUN apt-get update \
    && apt-get install -y jq curl \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .
# run gunicorn
CMD [ "python3", "-u", "app.py"]
# CMD gunicorn --bind 0.0.0.0:8899 main:app -k uvicorn.workers.UvicornWorker