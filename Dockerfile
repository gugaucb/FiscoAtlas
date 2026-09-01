FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY . .
