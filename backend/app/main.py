import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import faceCapture
from fastapi.staticfiles import StaticFiles
import os
import sys
import time
from loguru import logger
import logging
from app.internal.common import LOCAL_DOMAIN, streamDeviceManager
from apscheduler.schedulers.background import BackgroundScheduler

import os
allow_mock = os.getenv("DO_MOCK") #  babble / xverse
if allow_mock == None:
    allow_mock = "0"

check_time = os.getenv("CHECK_TIME")
if check_time == None:
    check_time = 2
else:
    check_time = float(check_time)

logger.info('Check time = {}, do mock = {}'.format(check_time, allow_mock) )

## TODO: 这个在实际设备中需要开启。用于定时同步确认设备在线. 在mock实验中，需要关闭
# DevicePingPong = True

############## init log ##############
LOG_DIR = os.path.join( os.path.dirname(__file__), "log")
os.makedirs(LOG_DIR, exist_ok=True)
logger.remove()
logger.add(sys.stderr, colorize=True, format="{time} {level} {message}", filter="stderr", level="ERROR")
logger.add(sys.stdout, colorize=True, format="{time} {level} {message}", filter="stdout", level="INFO")
logger.add( os.path.join(LOG_DIR, "{time:YYYY-MM-DD}.log"), enqueue=True, encoding='utf-8', rotation='00:00')

# # 自定义 Handler 将标准 logging 日志转发到 Loguru
# class InterceptHandler(logging.Handler):
#     def emit(self, record):
#         try:
#             level = logger.level(record.levelname).name
#         except ValueError:
#             level = record.levelno
        
#         # 定位日志来源
#         frame, depth = logging.currentframe(), 6
#         while frame.f_code.co_filename == logging.__file__:
#             frame = frame.f_back
#             depth += 1
        
#         logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# # 配置日志拦截
# logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# uvicorn_logger = logging.getLogger("uvicorn")
# uvicorn_logger.setLevel(logging.WARNING)
# fastapi_logger = logging.getLogger("fastapi")
# fastapi_logger.setLevel(logging.WARNING)
# logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
#######################################

app = FastAPI()

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "https://localhost",
        "http://localhost:8888",
        LOCAL_DOMAIN,
        ':'.join( LOCAL_DOMAIN.split(":")[:2] ),
        ':'.join( LOCAL_DOMAIN.split(":")[:2] ) + ":81"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(faceCapture.router)

# app.mount("/shared_data", StaticFiles(directory="/shared_data"), name="static")
os.makedirs('/app/app/log', exist_ok=True)
app.mount("/log", StaticFiles(directory="/app/app/log"), name="static")


####################
if allow_mock != "1":
    scheduler = BackgroundScheduler(job_defaults={'max_instances': 1})
    # 定时检查设备连接是否还在
    scheduler.add_job( streamDeviceManager.removeDisconnectDevice, 'interval', seconds=check_time, args=[check_time], max_instances=1)
    scheduler.start()

 # at last, the bottom of the file/module
if __name__ == "__main__": 
    uvicorn.run(app, host="0.0.0.0", port=8889)
