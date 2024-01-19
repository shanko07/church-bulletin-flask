FROM python:latest
LABEL authors="shanko"

RUN mkdir church-bulletin-flask
WORKDIR ./church-bulletin-flask

COPY chbul chbul

RUN pip install flask waitress click

RUN flask --app chbul init-db
RUN python -c 'import secrets; print("SECRET_KEY = \"" + f"{secrets.token_hex()}" + "\"")' > instance/config.py

EXPOSE 8080/tcp

CMD waitress-serve --call 'chbul:create_app'