
import os
import sys

sys.path.append(".")

import threading
import cv2
import internal.image_transforms as transforms
from internal.config import BabbleSettingsConfig

os.environ["OMP_NUM_THREADS"] = "1"
import onnxruntime as ort


class BabbleLandmark:
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
                f"{self.model}onnx/model.onnx",
                self.opts,
                providers=[provider],
                provider_options=[{"device_id": self.gpu_index}],
            )
            print(self.thread_local.session.get_providers())
            print("Available providers:", ort.get_available_providers())
        return self.thread_local.session
    
    def __init__(self, settings: BabbleSettingsConfig):

        self.settings = settings

        self.model = self.settings.gui_model_file
        # self.runtime = self.settings.gui_runtime
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
        self.output_name = self.sess.get_outputs()[0].name
        print('>> Babble landmark Processor Init')

    def inference(self, current_image_gray):
        frame = cv2.resize(current_image_gray, (256, 256))
        frame = transforms.to_tensor(frame)
        frame = transforms.unsqueeze(frame, 0)
        out = self.sess.run([self.output_name], {self.input_name: frame})

        return out[0][0]


        