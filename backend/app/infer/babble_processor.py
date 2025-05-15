from operator import truth
from dataclasses import dataclass
import sys
import time
import os

sys.path.append( os.path.dirname(__file__) )
sys.path.append( os.path.join(os.path.dirname(__file__), '..') )

import queue
import threading
import numpy as np
import cv2
from enum import Enum
from app.infer.one_euro_filter import OneEuroFilter
from app.infer.osc_calibrate_filter import *
from app.infer.tab import CamInfo, CamInfoOrigin

from loguru import logger
from collections import deque
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, lfilter

from babbleonnx_landmark import BabbleLandmark
# from mediapipe_landmark import MediaPipeLandmark
from xverse_landmark import XverseLandmark
from datetime import datetime
from loguru import logger



class SequenceSmooth:
    def __init__(self, window_size=5, sigma=1.0, alpha=0.8, cutoff=0.1 ):
        self.data = deque()  # 用于存储接收的数据
        self.window_size = window_size  # 滑动窗口的大小
        self.sigma = sigma  # 高斯滤波的标准差
        self.alpha = alpha  # 平滑系数，0 < alpha < 1
        self.last_ewma = None  # 记录上一次的EWMA值
        self.cutoff = cutoff  # 低通滤波器的截止频率
        self.b, self.a = self._design_filter()  # 设计滤波器

    def _design_filter(self):
        """
        设计一个一阶低通巴特沃斯滤波器。
        """
        nyq = 0.5  # 奈奎斯特频率
        order = 1 # 滤波器阶数
        normal_cutoff = self.cutoff / nyq  # 归一化截止频率
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a
    
    def isFull(self):
        return len(self.data) == self.window_size
    
    def add(self, new_data):
        """
        接收一组新的数据并进行存储。
        new_data: list 或 np.array，1行N列的浮动数据
        """
        # 将新数据添加到存储列表中
        if isinstance(new_data, list):
            new_data = np.array(new_data)
        
        # 应用低通滤波器
        # new_data = lfilter(self.b, self.a, new_data)

        self.data.append(new_data)
        
        ## 指数加权移动平均（EWMA） 
        # 如果是第一次添加数据，初始化last_ewma
        if self.last_ewma is None:
            self.last_ewma = new_data
        else:
            # 使用递归公式更新EWMA
            self.last_ewma = self.alpha * new_data + (1 - self.alpha) * self.last_ewma
    
        # 保持队列的最大长度为 window_size
        if len(self.data) > self.window_size:
            self.data.popleft()

    def get(self):
        """
        返回滤波后的数据。
        """
        if not self.data:
            return None
        # 对接收到的数据应用不同的滤波算法并返回结果
        data_array = np.array(self.data)

        # 使用中值滤波
        median_filtered = np.median(data_array, axis=0)
        # 使用滑动窗口平均
        window_avg_filtered = np.mean(data_array, axis=0)
        # 高斯滤波
        gaussian_filtered = gaussian_filter1d(data_array, sigma=self.sigma, axis=0)

        # 返回中值滤波和滑动窗口平均的结果
        return {
            "median_filtered": median_filtered,
            "window_avg_filtered": window_avg_filtered,
            "gaussian_filtered": gaussian_filtered[-1],
            "ewma_filtered": self.last_ewma
        }


class BabbleProcessor:
    
    def __init__(
        self,
        camConfig: "BabbleCameraConfig",
        settings: "BabbleSettingsConfig",
        cancellation_event: "threading.Event",
        capture_event: "threading.Event",
        capture_queue_incoming: "queue.Queue(maxsize=2)",
        osc_queue: queue.Queue,
        mac_address: str
    ):
        
        logger.info('>> Ready to Init Processor')

        self.camConfig = camConfig
        self.settings = settings 
        # Cross-thread communication management
        self.capture_queue_incoming = capture_queue_incoming
        self.cancellation_event = cancellation_event
        self.capture_event = capture_event 
        self.osc_queue = osc_queue

        # Image state
        self.previous_image = None
        self.current_image = None
        self.current_image_gray = None
        self.current_frame_number = None
        self.current_fps = None # capture fps
        self.FRAMESIZE = [0, 0, 1]

        ## 作为相机的唯一标识符
        self.mac_address = mac_address
        
        # Inference FPS
        self.last_frame_time = time.time()
        self.fps = 0

        self.calibration_frame_counter = None

        self.current_algo = CamInfoOrigin.MODEL

        
        if self.settings.landmark_alg == 'babble':
            self.babbleLM = BabbleLandmark(settings)
            noisy_point = np.array([45])

        # elif self.settings.landmark_alg == 'mediapipe':
        #     self.mediaLM = MediaPipeLandmark()
        #     noisy_point = np.array([52])

        elif self.settings.landmark_alg == 'xverse':
            self.xverseLM = XverseLandmark(settings)
            noisy_point = np.array([32])

        logger.info('>> Processor Init Finish')

        #### 做实验用的一些平滑算法 
        self.smooth = SequenceSmooth(window_size=3, )
        self.output = []

        #### Babble 内自带的 one euro 低通滤波器
        try:
            min_cutoff = float(self.settings.gui_min_cutoff)
            beta = float(self.settings.gui_speed_coefficient)
        except:
            logger.info(
                f'warn.oneEuroValues'
            )
            min_cutoff = 0.9
            beta = 0.9
        
        self.one_euro_filter = OneEuroFilter(
            noisy_point, min_cutoff=min_cutoff, beta=beta
        )

    def output_images_and_update(self, output_information: CamInfo):
        try:    
            self.previous_image = self.current_image

            # logger.info("self.osc_queue.qsize() >= self.osc_queue.maxsize is {}".format(self.osc_queue.qsize() >= self.osc_queue.maxsize) )

            # Relay information to OSC
            if self.osc_queue.qsize() >= self.osc_queue.maxsize:
                # logger.info('Warn. inference queue is full. The consumer may have stopped.')
                # 数据满了，直接开始丢弃最开始的一半
                for _ in range( self.osc_queue.maxsize // 2):
                    self.osc_queue.get_nowait()

            # logger.info("(self.mac_address, output_information) = {}".format((self.mac_address, len(output_information.output)) ) )
            self.osc_queue.put((self.mac_address, output_information))
        except:  # If this fails it likely means that the images are not the same size for some reason.
            logger.info(
                f'output_images_and_update error'
            )

    def capture_crop_rotate_image(self):
        # Get our current frame

        try:
            # Get frame from capture source, crop to ROI
            self.FRAMESIZE = self.current_image.shape

        except:
            # Failure to process frame, reuse previous frame.
            self.current_image = self.previous_image
            logger.info(
                f'error.capture。 use previous image'
            )

        try:
            # Apply rotation to cropped area. For any rotation area outside of the bounds of the image,
            # fill with white.
            try:
                rows, cols, _ = self.current_image.shape
            except:
                rows, cols, _ = self.previous_image.shape

            if self.camConfig.gui_vertical_flip:
                self.current_image = cv2.flip(self.current_image, 0)

            if self.camConfig.gui_horizontal_flip:
                self.current_image = cv2.flip(self.current_image, 1)

            img_center = (cols / 2, rows / 2)
            rotation_matrix = cv2.getRotationMatrix2D(
                img_center, self.camConfig.rotation_angle, 1
            )
            avg_color_per_row = np.average(self.current_image, axis=0)
            avg_color = np.average(avg_color_per_row, axis=0)
            ar, ag, ab = avg_color
            self.current_image = cv2.warpAffine(
                self.current_image,
                rotation_matrix,
                (cols, rows),
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(ar + 10, ag + 10, ab + 10),  # (255, 255, 255),
            )
            self.current_image_white = cv2.warpAffine(
                self.current_image,
                rotation_matrix,
                (cols, rows),
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255),
            )
            return True
        except:
            pass


    def run(self):
        while True:
            # Check to make sure we haven't been requested to close
            if self.cancellation_event.is_set():
                logger.info(
                    f'info.exitTrackingThread'
                )
                return

            try:
                # 检查是否有重组的待处理数据
                if self.capture_queue_incoming.empty():
                    self.capture_event.set()
                # Wait a bit for images here. If we don't get one, just try again.
                # 阻塞最多0.1秒，等待新帧进入
                (
                    self.current_image,
                    self.current_frame_number,
                    self.current_fps,
                ) = self.capture_queue_incoming.get(block=True, timeout=0.1)
            except queue.Empty:
                # logger.info("No image available")
                continue

            if not self.capture_crop_rotate_image():
                continue

            self.current_image_gray = cv2.cvtColor(
                self.current_image, cv2.COLOR_BGR2GRAY
            )

            self.run_model()
            if self.settings.use_calibration: # UI中的 Enable Calibration按钮
                self.output = cal.cal_osc(self, self.output)

            # logger.info(self.output)
            self.output_images_and_update(CamInfo(self.current_algo, self.output))

            # Calculate FPS
            current_frame_time = time.time()    # Should be using "time.perf_counter()", not worth ~3x cycles?
            delta_time = current_frame_time - self.last_frame_time
            self.last_frame_time = current_frame_time
            current_fps = 1 / delta_time if delta_time > 0 else 0
            self.fps = 0.02 * current_fps + 0.98 * self.fps

    def get_framesize(self):
        return self.FRAMESIZE
    
    
    def run_model(self):

        # self.current_image = 
        self.current_image = cv2.flip(self.current_image, 0)
        # 对输入图片做crop
        self.current_image = self.current_image[60:300,:,:]

        # 转换为灰度图
        gray_img = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2GRAY)
        # 将灰度图转换为三通道灰度图
        self.current_image = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)

        if self.settings.landmark_alg == 'babble':
            output = self.babbleLM.inference(self.current_image_gray)
        elif self.settings.landmark_alg == 'mediapipe':        
            output = self.mediaLM.inference(self.current_image)
        elif self.settings.landmark_alg == 'xverse':
            output = self.xverseLM.inference(self.current_image)

        no_filter = np.array(output)
        no_filter = no_filter.astype(np.float64)

        # 加一个自带的低通滤波
        # output = self.one_euro_filter(output)
 

        ## 如果不加低通滤波
        # output = output.astype(np.float64)

        ## Clip values between 0 - 1
        output = np.clip(no_filter, 0, 1)

        # TODO 固定的视频，推测表情系数，然后看每一种smooth输出结果的曲线变化
        self.smooth.add( output )
        if self.smooth.isFull():
            output = self.smooth.get()['ewma_filtered']
        '''
        "median_filtered": median_filtered,
        "window_avg_filtered": window_avg_filtered,
        "gaussian_filtered": gaussian_filtered[-1],
        "ewma_filtered": self.last_ewma
        '''
        if False: # or self.current_frame_number % 10 == 0:
            name = "{}".format(int(self.current_frame_number))
            now = datetime.now()
            # 格式化时间，精确到毫秒
            formatted_time = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]
            logger.info(formatted_time)
            cv2.imwrite("/app/app/log/{}.jpg".format(formatted_time), self.current_image )
            with open("/app/app/log/exp_{}.txt".format(formatted_time), "w") as f:
                # 设置打印精度，保留四位有效数字
                np.set_printoptions(precision=4, suppress=True)
                # 使用列表推导式将数组中的每个浮点数转换为字符串，并保留四位有效数字
                str_arr = [f"{x:.4g}" for x in output]
                result = ",".join(str_arr)
                f.write(result)
            
            with open("/app/app/log/exp_nofilter_{}.txt".format(formatted_time), "w") as f:
                # 设置打印精度，保留四位有效数字
                np.set_printoptions(precision=4, suppress=True)
                # 使用列表推导式将数组中的每个浮点数转换为字符串，并保留四位有效数字
                str_arr = [f"{x:.4g}" for x in no_filter]
                result = ",".join(str_arr)
                f.write(result)

        # logger.info( len(output) )
        self.output = output




if  __name__ == '__main__':
    imgdir = os.path.join(r"/app/app/log")
    imgfiles = [ os.path.join( imgdir, x) for x in os.listdir(imgdir) if x.endswith('jpg') ]

    from app.internal.config import BabbleConfig
    config: BabbleConfig = BabbleConfig.load()

    xverseLM = XverseLandmark(config.settings)
    
    for file in imgfiles:
        # 已经是240x240，上面20，下面60裁剪
        data = cv2.imread(file, cv2.IMREAD_UNCHANGED)
        output = xverseLM.inference(data)
        now = datetime.now()
        formatted_time = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]
        with open("/app/app/log/local/exp_{}.txt".format(formatted_time), "w") as f:
            # 设置打印精度，保留四位有效数字
            np.set_printoptions(precision=4, suppress=True)
            # 使用列表推导式将数组中的每个浮点数转换为字符串，并保留四位有效数字
            str_arr = [f"{x:.4g}" for x in output]
            result = ",".join(str_arr)
            f.write(result)


