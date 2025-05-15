
import queue
from queue import Queue, Empty
from app.internal.osc import VRChatOSC
from app.infer.babble_processor import BabbleProcessor
from app.internal.camera import Camera
from app.internal.config import BabbleConfig
from threading import Event, Thread
import signal
import sys


VRCHAT_OSC = True

class DeviceTask:

    def get_exp_queue(self):
        '''
        获取表情系数队列
        '''
        return self.osc_queue

    def __init__(self, streamUrl, userID, mac_address):

        config: BabbleConfig = BabbleConfig.load()
        # config.save()

        self.cancellation_event = Event()

        self.cancellation_event.clear()

        # Spawn worker threads: osc\camera\processor
        # 记录表情系数推理结果（ (camera_address, camera_info) ）
        self.osc_queue: queue.Queue[tuple[bool, int, int]] = queue.Queue(maxsize=10)

        if VRCHAT_OSC:
            self.osc = VRChatOSC(self.cancellation_event, self.osc_queue, config)
            self.osc_thread = Thread(target=self.osc.run)
            self.osc_thread.start()

        ########## for camera
        self.capture_event = Event()
        self.capture_queue = Queue(maxsize=2)
        self.camera = Camera(
            camConfig = config.cam,
            settings=config.settings,
            capture_source=streamUrl,
            cancellation_event=self.cancellation_event,
            capture_event=self.capture_event,
            camera_output_outgoing=self.capture_queue,
        )

        ########## for img2exp
        self.babble_cnn = BabbleProcessor(
            camConfig = config.cam,
            settings = config.settings,
            cancellation_event=self.cancellation_event,
            capture_event=self.capture_event,
            capture_queue_incoming=self.capture_queue,
            osc_queue=self.osc_queue,
            mac_address = mac_address,
        )

        self.camera_thread = Thread(target=self.camera.run)
        self.camera_thread.start()
        self.babble_cnn_thread = Thread(target=self.babble_cnn.run)
        self.babble_cnn_thread.start()
    
    def started(self):
        print('>>>> start')
        return not self.cancellation_event.is_set()
    
    def stopped(self):
        print('>>>> stopped')
        return self.cancellation_event.is_set()
    
    def stop(self):
        print('>>>> stop')
        # If we're not running yet, bail
        if self.cancellation_event.is_set():
            return
        self.cancellation_event.set()

        if VRCHAT_OSC:
            self.osc_thread.join()

        self.camera_thread.join()
        self.babble_cnn_thread.join()