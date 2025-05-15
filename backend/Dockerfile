FROM tiangolo/uvicorn-gunicorn:python3.11-slim

WORKDIR /app/

ENV DEBIAN_FRONTEND=noninteractive  

ENV PYTHONPATH=/app

RUN pip config set global.index-url https://mirrors.tencent.com/pypi/simple
RUN pip config set install.trusted-host mirrors.tencent.com

RUN pip3 install "fastapi[standard]" 
RUN pip3 install aiohttp
RUN pip3 install httpx
RUN pip3 install httpx[http2]
RUN pip3 install python-dotenv
# RUN pip3 install --upgrade protobuf
# RUN pip3 install PyJWT
# RUN pip3 install sqlmodel
RUN pip3 install APScheduler
RUN pip3 install python-osc
RUN pip3 install onnxruntime-gpu
RUN pip3 install opencv-python-headless
RUN pip3 install loguru
RUN pip3 install scipy
# RUN pip3 install mediapipe

EXPOSE 8889

# babble / xverse
ENV ALG_TYPE="xverse" 
# 禁止用mock
ENV DO_MOCK="0"

ENV CHECK_TIME=2

COPY ./app/infer /app/app/infer
COPY ./app/internal /app/app/internal
COPY ./app/Models /app/app/Models
COPY ./app/routers /app/app/routers
COPY ./app/*.py /app/app

COPY ./prestart.sh /app/


# docker build -t test-vr-face:base .

# docker run --rm -it --gpus all -p 8889:8889 -v "D:\\face\\XVRFaceCap\\log":/app/app/log  test-vr-face:base

# docker run --rm -it --gpus all -p 8889:8889 -v "D:\\face\\XVRFaceCap\\log":/app/app/log -v "D:\\face\\XVRFaceCap\\faceTracking\\VRFaceTrackingApp\\backend\\app":/app/app  test-vr-face:base /bin/bash

