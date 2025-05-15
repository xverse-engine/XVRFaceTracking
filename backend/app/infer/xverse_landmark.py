 
import os
import sys

sys.path.append(".")

import threading
import cv2
import numpy as np
import internal.image_transforms as transforms
from internal.config import BabbleSettingsConfig

from loguru import logger

os.environ["OMP_NUM_THREADS"] = "1"
import onnxruntime as ort

'''
=== xverse export ARKit52 ===
ARKIT_TAGS = [
    "cheekPuff",
    "cheekSquintLeft",
    "cheekSquintRight",
    "noseSneerLeft",
    "noseSneerRight",
    "jawOpen",
    "jawForward",
    "jawLeft",
    "jawRight",
    "mouthFunnel",
    "mouthPucker",
    "mouthLeft",
    "mouthRight",
    "mouthRollUpper",
    "mouthRollLower",
    "mouthShrugUpper",
    "mouthShrugLower",
    "mouthClose",
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthFrownLeft",
    "mouthFrownRight",
    "mouthDimpleLeft",
    "mouthDimpleRight",
    "mouthUpperUpLeft",
    "mouthUpperUpRight",
    "mouthLowerDownLeft",
    "mouthLowerDownRight",
    "mouthPressLeft",
    "mouthPressRight",
    "mouthStretchLeft",
    "mouthStretchRight",
]
'''

class XverseLandmark:
    # Thread-local storage for storing session
    thread_local = threading.local()
    def get_session(self,):
        if not hasattr(self.thread_local, "session"):
            # 如果需要用gpu：参考 https://github.com/Tencent/MimicMotion/issues/44
            if self.use_gpu:
                provider = "CUDAExecutionProvider"#  ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
            else:
                provider = "CPUExecutionProvider"  # Build onnxruntime to get both DML and OpenVINO
            self.thread_local.session = ort.InferenceSession(
                f"{self.model}onnx/vrface0318.onnx",
                self.opts,
                providers=[provider],
                provider_options=[{"device_id": self.gpu_index}],
            )
            logger.info(self.thread_local.session.get_providers())
            logger.info("Available providers:", ort.get_available_providers())
        return self.thread_local.session

    def __init__(self, settings: BabbleSettingsConfig):
        logger.info("Init xverse tracing")

        self.settings = settings
        self.model = self.settings.gui_model_file
        self.use_gpu = self.settings.gui_use_gpu
        self.gpu_index = self.settings.gui_gpu_index

        
        ort.disable_telemetry_events()
        self.opts = ort.SessionOptions()
        self.opts.inter_op_num_threads = 1
        self.opts.intra_op_num_threads = self.settings.gui_inference_threads
        self.opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.opts.add_session_config_entry("session.intra_op.allow_spinning", "0")  # ~3% savings worth ~6ms avg latency. Not noticeable at 60fps?
        self.opts.enable_mem_pattern = False
        self.sess = self.get_session()
        self.input_name = self.sess.get_inputs()[0].name
        # [0]: ldmks, [1]: sd, [2]: arkits
        self.output_name = self.sess.get_outputs()[2].name
        logger.info('>> Xverse Processor Init')

    def inference(self, image):
        
        frame = cv2.resize(image, (256, 256))
        frame_transposed = frame.transpose(2, 0, 1).astype(np.float32)  # CHW, BGR, 
        frame_transposed[0, :, :] = (frame_transposed[0, :, :] - 127.5)/127.5
        frame_transposed[1, :, :] = (frame_transposed[1, :, :] - 127.5)/127.5
        frame_transposed[2, :, :] = (frame_transposed[2, :, :] - 127.5)/127.5
        frame_transposed = np.expand_dims(frame_transposed,axis = 0)
        # frame = transforms.to_tensor(frame)
        # frame = transforms.unsqueeze(frame, 0)
        out = self.sess.run([self.output_name], {self.input_name: frame_transposed})

        return out[0][0]

 