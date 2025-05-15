import cv2
# from cv2.typing import *
import numpy as np
import queue
# import serial.tools.list_ports
import threading
import time
from app.internal.config import BabbleCameraConfig, BabbleSettingsConfig
from enum import Enum
import sys

MAX_RESOLUTION: int = 600


class CameraState(Enum):
    CONNECTING: int = 0
    CONNECTED: int = 1
    DISCONNECTED: int = 2


class Camera:
    def __init__(
        self,
        camConfig: BabbleCameraConfig,
        settings: BabbleSettingsConfig,
        capture_source: str,
        cancellation_event: "threading.Event",
        capture_event: "threading.Event",
        # camera_status_outgoing: "queue.Queue[CameraState]",
        camera_output_outgoing: "queue.Queue(maxsize=2)",
    ):
        self.camera_status = CameraState.CONNECTING
        self.camConfig = camConfig
        self.settings = settings
        # self.camera_status_outgoing = camera_status_outgoing
        self.camera_output_outgoing = camera_output_outgoing
        self.capture_event = capture_event
        self.cancellation_event = cancellation_event
        self.current_capture_source = None
        self.cv2_camera: "cv2.VideoCapture" = None

        self.last_frame_time = time.time()
        self.fps = 0
        self.bps = 0
        self.buffer = b""
        self.FRAME_SIZE = [0, 0]

        self.error_message = f'info.enterCaptureOne'



        self.current_capture_source = capture_source

        if self.camConfig.use_ffmpeg:
            self.cv2_camera = cv2.VideoCapture(
                self.current_capture_source, cv2.CAP_FFMPEG
            )
        else:
            self.cv2_camera = cv2.VideoCapture(
                self.current_capture_source
            )

        if not self.settings.gui_cam_resolution_x == 0:
            self.cv2_camera.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                self.settings.gui_cam_resolution_x,
            )
        if not self.settings.gui_cam_resolution_y == 0:
            self.cv2_camera.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                self.settings.gui_cam_resolution_y,
            )
        if not self.settings.gui_cam_framerate == 0:
            self.cv2_camera.set(
                cv2.CAP_PROP_FPS, self.settings.gui_cam_framerate
            )


    def set_output_queue(self, camera_output_outgoing: "queue.Queue"):
        self.camera_output_outgoing = camera_output_outgoing

    def run(self):
        while True:
            if self.cancellation_event.is_set():
                print(
                    f"info.exitCaptureThread"
                )
                return 
            # Assuming we can access our capture source, wait for another thread to request a capture.
            # Cycle every so often to see if our cancellation token has fired. This basically uses a
            # python event as a context-less, resettable one-shot channel.
            ## 等待推理线程消耗，如果0.02秒内，推理线程没有设置capture_event，那么说明，推理线程还在跑历史数据，不要采集新的了。
            # 推理线程中，会判断待处理的数据是否充足，如果不充足（消耗很快），就会设置capture_event，然后进入后续的采集逻辑
            if not self.capture_event.wait(timeout=0.02):
                continue
            
            if self.cv2_camera is not None: # and self.cv2_camera.isOpened():
                self.get_cv2_camera_picture()
            

    def get_cv2_camera_picture(self,):
        try:
            ret, image = self.cv2_camera.read()
            if not ret:
                self.camera_status = CameraState.DISCONNECTED
                self.cv2_camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                raise RuntimeError("opencv read frame error")
            
            # 顺时针旋转90度
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

            self.FRAME_SIZE = image.shape
            frame_number = self.cv2_camera.get(cv2.CAP_PROP_POS_FRAMES)
            # Calculate FPS
            current_frame_time = time.time()    # Should be using "time.perf_counter()", not worth ~3x cycles?
            delta_time = current_frame_time - self.last_frame_time
            self.last_frame_time = current_frame_time
            current_fps = 1 / delta_time if delta_time > 0 else 0
            # Exponential moving average (EMA). ~1100ns savings, delicious..
            self.fps = 0.02 * current_fps + 0.98 * self.fps
            self.bps = image.nbytes * self.fps

            self.push_image_to_queue(image, frame_number + 1, self.fps)
        except Exception:
            print(f"!!!!  warn.captureProblem")
            self.cancellation_event.set()
            self.camera_status = CameraState.DISCONNECTED
            self.cv2_camera.release()
            self.cv2_camera = None
            pass


    def clamp_max_res(self, image): # MatLike
        shape = image.shape
        max_value = np.max(shape)
        if max_value > MAX_RESOLUTION:
            scale: float = MAX_RESOLUTION/max_value
            width: int = int(shape[1] * scale)
            height: int = int(shape[0] * scale)
            image = cv2.resize(image, (width, height))

            return image
        else: return image


    def push_image_to_queue(self, image, frame_number, fps):
        # If there's backpressure, just yell. We really shouldn't have this unless we start getting
        # some sort of capture event conflict though.
        qsize = self.camera_output_outgoing.qsize()
        if qsize == self.camera_output_outgoing.maxsize:
            print('Warn: capture queue is full. The consumer may have stopped.')
            for _ in range(qsize//2):
                self.camera_output_outgoing.get_nowait()

        self.camera_output_outgoing.put((self.clamp_max_res(image), frame_number, fps))
        self.capture_event.clear()
