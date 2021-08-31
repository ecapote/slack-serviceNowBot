FROM python:3.7.4-alpine
MAINTAINER Erick Capote "erick.capote@ntt.com"
RUN apk update && apk upgrade
RUN apk add --no-cache gcc \
                       libcurl \
                       python3-dev \
                       gpgme-dev \
                       libc-dev \
    && rm -rf /var/cache/apk/*
#RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py
#RUN pip install setuptools==30.1.0
RUN pip install requests slackclient
RUN mkdir /app
WORKDIR /app
COPY ./py_ServiceNow_BOT_ver3.py /app
COPY ./slack_bot_config.ini /app
COPY ./__init__.py /app

CMD ["python","/app/py_ServiceNow_BOT_ver3.py"]
