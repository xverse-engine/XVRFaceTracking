'''
所有公共的类、对象都放在这边
'''

import concurrent.futures
from typing import List
import asyncio
import threading
import time
import os
import json
import signal
import sys
import uuid
from enum import Enum
from app.internal.deviceTask import DeviceTask
from loguru import logger

ENV_URL = os.getenv('ENV_URL')
LOCAL_DOMAIN = os.getenv('LOCAL_DOMAIN')
LLM_URL = os.getenv('LLM_URL')

LOCAL_DOMAIN = LOCAL_DOMAIN if LOCAL_DOMAIN else "http://localhost"

class DeviceItem:
    def __init__(self):
        self.userID = ""
        self.stream = ""
        self.mac_address = ""
        self.lastVisitTime = 0

        self.task = None

    def isActive(self, time, threshold):

        # logger.info(' time = {}, lastVisitTime = {}'.format(time, self.lastVisitTime) )

        if time - self.lastVisitTime > threshold:
            '''
            触发task kill
            '''
            if self.task is not None:
                # 开一个新线程做stop任务。stop任务因为camera里面read()会卡线程，导致这边如果不开新线程，就会卡住主线程的后台任务
                stop_thread = threading.Thread(target=self.stop)
                stop_thread.start()
            return False
        else:
            return True
    
    def start(self,):
        '''
        DeviceTask中开启多个新线程，用于采集、推理、传输
        '''
        self.task = DeviceTask( 
            streamUrl = self.stream, userID=self.userID, mac_address=self.mac_address)

        ## 通过下面的函数，可以获取当前task的表情系数队列. 
        # self.task.get_exp_queue()

    def stop(self):
        logger.info('>>> DeviceItem stop')
        # Directly invoke the stop method in a separate thread
        if self.task is not None:
            stop_thread = threading.Thread(target=self.task.stop)
            stop_thread.start()
            self.task = None
            stop_thread.join()
            logger.info("> quit task <")

class StreamDeviceManager:
    def __init__(self):
        self.devices: dict[str, DeviceItem] = {}

    def getAllDeviceKey(self,):
        return list(self.devices.keys())
    
    def runtimeInfo(self,):
        taskInfo = {}
        itemInfo = {
            'cap_fps': 0,
            'source': "",
            'infer_fps': 0,
        }
        for key,value in self.devices.items():
            tmpInfo = itemInfo.copy()
            tmpInfo['cap_fps'] = value.task.camera.fps
            tmpInfo['source'] = value.stream
            tmpInfo['infer_fps'] = value.task.babble_cnn.fps
            taskInfo[key] = tmpInfo
        return taskInfo
    
    def removeDisconnectDevice(self, threshold = 1):
        '''
        超过1秒没有反应的全部删除
        '''
        # self.devices = {key: value for key, value in self.devices.items() if value.isActive(time.time(), threshold ) }
        inactive_devices = []  # 用于记录返回 False 的设备
        new_devices = {}       # 用于存储返回 True 的设备
        for key, value in self.devices.items():
            if value.isActive(time.time(), threshold):
                new_devices[key] = value  # 保留活跃设备
            else:
                inactive_devices.append(value)  # 记录不活跃设备
        self.devices = new_devices  # 更新 self.devices 为新的活跃设备字典
    
        if len(inactive_devices) > 0:
            for item in inactive_devices:
                logger.info("Delete mac:{}, userID:{}, stream:{}".format(item.mac_address, item.userID, item.stream ) )
            

    def removeAll(self, ):
        self.removeDisconnectDevice(-1)        

    def addDevice(self, device):
        '''
        device: dict
        userId
        '''
        if device['mac_address'] in self.getAllDeviceKey():
            # 检查是否已经有记录
            self.devices[device['mac_address']].lastVisitTime = device['time']
            # logger.info('device:{} exists. jump'.format(device['mac_address']) )
            return False
        
        item = DeviceItem()
        item.userID = device['userID']
        item.stream = device['stream']
        item.mac_address = device['mac_address']
        item.lastVisitTime = device['time']
        item.start()
        self.devices[device['mac_address']] = item

        logger.info("=========  Add Device =======")
        logger.info(device)
        
        return True

streamDeviceManager = StreamDeviceManager()

# 定义信号处理函数
def signal_handler(sig, frame):
    logger.warning('You pressed Ctrl+C!')
    streamDeviceManager.removeAll()
    # sys.exit(0)
# 设置信号处理函数
signal.signal(signal.SIGINT, signal_handler)
