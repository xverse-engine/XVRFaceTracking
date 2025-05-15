from fastapi import APIRouter, Request, HTTPException
import os, shutil 
import time
import httpx
import json
import base64
from datetime import datetime, timedelta
from app.internal.common import streamDeviceManager
import traceback
import asyncio
from typing import List
from loguru import logger


allow_mock = os.getenv("DO_MOCK") #  babble / xverse
if allow_mock == None:
    allow_mock = "0"

router = APIRouter()

########## POST
@router.post('/facecap', tags=["Face Capture"])
async def login_device(userID: str, request: Request):
    try:
        body = await request.body()  # 获取原始请求体
        body = json.loads(body)
        streamDeviceManager.addDevice({
            'userID': userID,
            'stream': body['stream'],
            'mac_address': body['mac_address'],
            'time': time.time()
        })
    except Exception as e:
        msg = ''.join(traceback.TracebackException.from_exception(e).format())
        return {'status_code': 0, 'msg': msg}


@router.post('/facecap_mock', tags=["Face Capture Mock"])
async def login_device(stream: str):
    if allow_mock == "0":
        raise HTTPException(status_code=403, detail="Face Capture Mock is not enabled.")
    
    import random
    import uuid
    def generate_random_mac():
        mac = [format(random.randint(0, 255), '02x') for _ in range(6)]
        return ':'.join(mac)
    try:     
        streamDeviceManager.addDevice({
            'userID': str(uuid.uuid4()),
            'stream': stream,
            'mac_address': generate_random_mac(),
            'time': time.time()
        })
    except Exception as e:
        msg = ''.join(traceback.TracebackException.from_exception(e).format())
        return {'status_code': 0, 'msg': msg}


@router.get('/runtime', tags=["Face Capture"])
async def get_runtime_info():
    return streamDeviceManager.runtimeInfo()


@router.post('/streamurl', tags=["Face Capture"])
async def get_stream_info(userKey: str):
    result = ""
    if userKey not in streamDeviceManager.devices:
        return result
    return streamDeviceManager.devices[userKey].stream


@router.post('/faceexp', tags=["Face Capture"])
async def get_exp_info(userKeys: List[str]):
    # 根据users，获取指定mac_address的设备采集的exp
    result = {}
    for key in userKeys:
        # logger.info("key = {}".format(key) )
        if key not in streamDeviceManager.devices:
            continue
        exp_queue = streamDeviceManager.devices[key].task.get_exp_queue()
        # logger.info("exp_queue = {}".format(exp_queue.qsize()) )
        if exp_queue.qsize() > 0:
            data = []
            while not exp_queue.empty():
                (camera_mac_address, cam_info) = exp_queue.get(block=True, timeout=0.01)
                data.append( list(cam_info.output) )
            # TODO: 单人还好，多人的情况如何处理？ 可能需要主动发出消息到所有相同房间. 
            result[key] = data

    return result