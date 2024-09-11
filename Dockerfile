FROM python:3.10-slim

# Install dependencies
RUN mkdir /app
WORKDIR /app


COPY chat_app /app/chat_app

ENV VIRTUAL_ENV=/usr/local
RUN python3 -m pip install pip --upgrade
RUN python3 -m pip install uv

COPY requirements.txt /app
COPY run.py /app
COPY gunicorn.sh /app

RUN uv pip install --system -r requirements.txt

EXPOSE 80

RUN ["chmod", "+x", "./gunicorn.sh"]

ENTRYPOINT ["./gunicorn.sh"]
