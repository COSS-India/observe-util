FROM python:3.10 as base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/src

RUN apt-get update && apt-get install -y libsndfile1 libsndfile1-dev ffmpeg

WORKDIR /src
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "torchaudio==2.4.1"

# Install Dhruva Observability Plugin from Test PyPI
# RUN pip install -i https://test.pypi.org/simple/ dhruva-observability==1.0.9
# NOTE: Using local dhruva_observability package instead (copied via COPY . /src)

COPY . /src
RUN chmod -R 777 /src