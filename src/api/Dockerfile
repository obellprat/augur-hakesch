# pull official base image
FROM python:3.13-trixie

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

#RUN apt-get update && apt-get install -y gcc
#RUN apt-get install -y build-essential python3-dev libcairo2-dev libpango1.0-dev libgdal-dev

# install dependencies
RUN pip install --upgrade pip
RUN apt-get update && \
apt-get upgrade -y && \
apt-get install -y git build-essential python3-dev libcairo2-dev libpango1.0-dev libgdal-dev libjemalloc2
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .


ENV TZ="Europe/Zurich"

RUN prisma generate
