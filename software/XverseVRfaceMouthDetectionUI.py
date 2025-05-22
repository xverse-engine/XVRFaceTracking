import sys
import cv2
import numpy as np
import onnxruntime as ort
from pythonosc import udp_client
from PyQt5 import QtWidgets, QtCore
import threading
import time
import numpy as np

def smoothing_factor(t_e, cutoff):
    r = 2 * np.pi * cutoff * t_e
    return r / (r + 1)

def exponential_smoothing(a, x, x_prev):
    return a * x + (1 - a) * x_prev

class OneEuroFilter:
    def __init__(self, x0, dx0=0.0, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.data_shape = x0.shape
        self.min_cutoff = np.full(x0.shape, min_cutoff)
        self.beta = np.full(x0.shape, beta)
        self.d_cutoff = np.full(x0.shape, d_cutoff)
        self.x_prev = x0.astype(float)
        self.dx_prev = np.full(x0.shape, dx0)
        self.t_prev = time.time()

    def __call__(self, x):
        x.shape == self.data_shape
        t = time.time()
        t_e = t - self.t_prev
        if t_e != 0.0:
            t_e = np.full(x.shape, t_e)
            a_d = smoothing_factor(t_e, self.d_cutoff)
            dx = (x - self.x_prev) / t_e
            dx_hat = exponential_smoothing(a_d, dx, self.dx_prev)
            cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)
            a = smoothing_factor(t_e, cutoff)
            x_hat = exponential_smoothing(a, x, self.x_prev)
            self.x_prev = x_hat
            self.dx_prev = dx_hat
            self.t_prev = t
            return x_hat


def normalize(numpy_array):
    """
    Normalize the values of a numpy array to a specified range.

    Args:
    - numpy_array (numpy.ndarray): Input numpy array.

    Returns:
    - numpy.ndarray: Normalized numpy array.
    """
    normalized_array = numpy_array / 255

    return normalized_array


def to_tensor(numpy_array, dtype=np.float32):
    """
    Convert a numpy array to a PyTorch tensor.

    Args:
    - numpy_array (numpy.ndarray): Input numpy array.
    - dtype (numpy.dtype): Data type of the resulting PyTorch tensor.

    Returns:
    - torch.Tensor: Converted PyTorch tensor.
    """
    if not isinstance(numpy_array, np.ndarray):
        raise ValueError("Input must be a numpy array")

    # Ensure the input array has the correct data type
    numpy_array = numpy_array.astype(dtype)

    # Add a batch dimension if the input array is 2D
    if len(numpy_array.shape) == 2:
        numpy_array = numpy_array[:, :, np.newaxis]

    # Transpose the array to match PyTorch tensor format (C x H x W)
    tensor = normalize(np.transpose(numpy_array, (2, 0, 1)))

    return tensor


def unsqueeze(numpy_array, axis: int):
    """
    Add a dimension of size 1 to a numpy array at the specified position.

    Args:
    - numpy_array (numpy.ndarray): Input numpy array.
    - axis (int): Position along which to add the new dimension.

    Returns:
    - numpy.ndarray: Numpy array with an additional dimension.
    """
    if not isinstance(numpy_array, np.ndarray):
        raise ValueError("Input must be a numpy array")

    result_array = np.expand_dims(numpy_array, axis=axis)

    return result_array
















class CamOnnxOscApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XverseVRfaceMouthDetectionUI.py")
        self.setGeometry(200, 200, 420, 320)
        self.init_ui()
        self.running = False
        self.thread = None

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.stream_url = QtWidgets.QLineEdit("81/stream")
        self.onnx_path = QtWidgets.QLineEdit(r"..\Models\XVRFaceTracking.onnx")
        self.osc_ip = QtWidgets.QLineEdit("127.0.0.1")
        self.osc_port = QtWidgets.QSpinBox()
        self.osc_port.setRange(1, 65535)
        self.osc_port.setValue(8888)
        self.osc_addr = QtWidgets.QLineEdit("")
        self.roi_x = QtWidgets.QSpinBox(); self.roi_x.setRange(0, 4096)
        self.roi_y = QtWidgets.QSpinBox(); self.roi_y.setRange(0, 4096)
        self.roi_w = QtWidgets.QSpinBox(); self.roi_w.setRange(1, 4096); self.roi_w.setValue(256)
        self.roi_h = QtWidgets.QSpinBox(); self.roi_h.setRange(1, 4096); self.roi_h.setValue(256)
        self.rotation = QtWidgets.QSpinBox(); self.rotation.setRange(0, 359)
       
        self.use_gpu = QtWidgets.QCheckBox("Use GPU (CUDA)")
        self.flip_horizontal = QtWidgets.QCheckBox("Flip Horizontal")
        self.use_filter = QtWidgets.QCheckBox("Enable Filter")
        self.min_cutoff = QtWidgets.QDoubleSpinBox(); self.min_cutoff.setRange(0.1, 10.0); self.min_cutoff.setValue(1.0)
        self.beta = QtWidgets.QDoubleSpinBox(); self.beta.setRange(0.0, 1.0); self.beta.setValue(0.01)
        self.d_cutoff = QtWidgets.QDoubleSpinBox(); self.d_cutoff.setRange(0.1, 10.0); self.d_cutoff.setValue(1.0)
        self.infer_threads = QtWidgets.QSpinBox(); self.infer_threads.setRange(1, 16); self.infer_threads.setValue(1)
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        
        
        layout.addRow(self.use_gpu)
        layout.addRow(self.flip_horizontal)
        layout.addRow(self.use_filter)
        
        layout.addRow("ONNX Path", self.onnx_path)
        layout.addRow("Stream Url", self.stream_url)
        layout.addRow("ROI x", self.roi_x)
        layout.addRow("ROI y", self.roi_y)
        layout.addRow("ROI width", self.roi_w)
        layout.addRow("ROI hight", self.roi_h)
        layout.addRow("Rotation", self.rotation)
        
        
        
        layout.addRow("OneEuro Fcmin", self.min_cutoff)
        layout.addRow("OneEuro Beta", self.beta)
        layout.addRow("OneEuro D Cutoff", self.d_cutoff)
        layout.addRow("Inference Threads", self.infer_threads)
        layout.addRow(self.start_btn, self.stop_btn)
        self.setLayout(layout)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        
        # 连接过滤器相关的信号和槽
        self.use_filter.stateChanged.connect(self.toggle_filter)
        self.min_cutoff.valueChanged.connect(self.update_filter_params)
        self.beta.valueChanged.connect(self.update_filter_params)
        self.d_cutoff.valueChanged.connect(self.update_filter_params)

    def start(self):
        if self.running:
            return
        self.running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.thread = threading.Thread(target=self.run_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def toggle_filter(self, state):
        self.filter_enabled = state == QtCore.Qt.Checked
        
    def update_filter_params(self):
        if hasattr(self, 'filter'):
            self.filter.min_cutoff = np.full(self.filter.data_shape, self.min_cutoff.value())
            self.filter.beta = np.full(self.filter.data_shape, self.beta.value())
            self.filter.d_cutoff = np.full(self.filter.data_shape, self.d_cutoff.value())
            
    def run_loop(self):
        stream_url = self.stream_url.text()
        onnx_path = self.onnx_path.text()
        osc_ip = self.osc_ip.text()
        osc_port = self.osc_port.value()
        osc_addr = self.osc_addr.text()
        roi_x = self.roi_x.value()
        roi_y = self.roi_y.value()
        roi_w = self.roi_w.value()
        roi_h = self.roi_h.value()
        rotation = self.rotation.value()
        use_gpu = self.use_gpu.isChecked()
        infer_threads = self.infer_threads.value()
        try:
            osc_client = udp_client.SimpleUDPClient(osc_ip, osc_port)
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = infer_threads
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            opts.add_session_config_entry("session.intra_op.allow_spinning", "0")
            opts.enable_mem_pattern = False
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else ["CPUExecutionProvider"]
            sess = ort.InferenceSession(onnx_path, opts, providers=providers)
            input_name = sess.get_inputs()[0].name
            output_name = sess.get_outputs()[0].name
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "ONNX/OSC Init Error", str(e))
            self.running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            QtWidgets.QMessageBox.critical(self, "Camera Error", f"无法打开摄像头流: {stream_url}")
            self.running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        cv2.namedWindow("Processed", cv2.WINDOW_NORMAL)
        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("无法从网络摄像头读取帧，3秒后重试...")
                time.sleep(3)
                continue
            try:
                y1 = int(roi_y)
                y2 = int(roi_y + roi_h)
                x1 = int(roi_x)
                x2 = int(roi_x + roi_w)
                roi_img = frame[y1:y2, x1:x2]
            except Exception as e:
                print(f"ROI剪切失败，使用原始帧: {e}")
                roi_img = frame
            try:
                rows, cols, _ = roi_img.shape
                img_center = (cols / 2, rows / 2)
                rotation_matrix = cv2.getRotationMatrix2D(img_center, rotation, 1)
                avg_color_per_row = np.average(roi_img, axis=0)
                avg_color = np.average(avg_color_per_row, axis=0)
                ar, ag, ab = avg_color
                rotated_img = cv2.warpAffine(
                    roi_img,
                    rotation_matrix,
                    (cols, rows),
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(ar+10 , ag+10 , ab+10 ),
                )
            except Exception as e:
                print(f"旋转处理失败: {e}")
                rotated_img = roi_img
            #############################################################################
            frame = cv2.resize(rotated_img, (256, 256))
            if self.flip_horizontal.isChecked():
                frame = cv2.flip(frame, 1)
            frame = to_tensor(frame)
            frame = unsqueeze(frame, 0)
            frame = np.concatenate([frame], axis=1)
            frame = frame*2-1
                
            
            # gray_img = cv2.cvtColor(rotated_img, cv2.COLOR_BGR2GRAY)
            # gray_img = cv2.resize(gray_img, (256, 256))
            # # 转为三通道BGR
            # bgr_img = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
            # # 转为float32并归一化
            # input_img = bgr_img.astype(np.float32) / 127-1
            # # 调整shape为(1,3,256,256)
            # input_img = np.transpose(input_img, (2, 0, 1))
            # input_img = np.expand_dims(input_img, axis=0)
            # input_img = np.expand_dims(input_img, axis=0)
            try:
                output = sess.run(['arkits'], {input_name: frame})
                # print(output)
                # print(output)
                output_list = output[0].tolist()
                # print(f"ONNX输出长度: {len(output_list)}，内容: {output_list}")
                output_list=output_list[0]
                import math
                multi = 1 # 可根据实际需求设为界面参数
                try:
                    max_clip_value = 10 ** math.floor(math.log10(multi))
                except:
                    max_clip_value = 1.0
                arr = np.array(output_list)
                # arr[5] = arr[5] * 1.2
                # arr[17] = arr[17] * 1.2 + 0.25 * arr[5]
                # arr[18] = arr[18] * 1.3
                # arr[19] = arr[19] * 1.3
                # arr[18:28] = arr[18:28] * 1.25
                arr = np.clip(arr * multi, 0, max_clip_value)
                # 初始化OneEuroFilter
                if self.use_filter.isChecked():
                    if not hasattr(self, 'filter'):
                        self.filter = OneEuroFilter(arr, min_cutoff=self.min_cutoff.value(), beta=self.beta.value(), d_cutoff=self.d_cutoff.value())
                    arr = self.filter(arr)
                # print(arr)
                # OSC发送（与原工程一致）
                location=''
                
                    
                
                
                
                osc_client.send_message(location + "/cheekPuffLeft", arr[0])
                osc_client.send_message(location + "/cheekPuffRight", arr[0])
                osc_client.send_message(location + "/cheekSuckLeft", arr[1])
                osc_client.send_message(location + "/cheekSuckRight", arr[2])
                osc_client.send_message(location + "/jawOpen", arr[5])
                osc_client.send_message(location + "/jawForward", arr[6])
                osc_client.send_message(location + "/jawLeft", arr[7])
                osc_client.send_message(location + "/jawRight", arr[8])
                osc_client.send_message(location + "/noseSneerLeft", arr[3])
                osc_client.send_message(location + "/noseSneerRight", arr[4])
                osc_client.send_message(location + "/mouthFunnel", arr[9])
                osc_client.send_message(location + "/mouthPucker", arr[10])
                osc_client.send_message(location + "/mouthLeft", arr[11])
                osc_client.send_message(location + "/mouthRight", arr[12])
                osc_client.send_message(location + "/mouthRollUpper", arr[13])
                osc_client.send_message(location + "/mouthRollLower", arr[14])
                osc_client.send_message(location + "/mouthShrugUpper", arr[15])
                osc_client.send_message(location + "/mouthShrugLower", arr[16])
                osc_client.send_message(location + "/mouthClose", arr[17])
                osc_client.send_message(location + "/mouthSmileLeft", arr[18])
                osc_client.send_message(location + "/mouthSmileRight", arr[19])
                osc_client.send_message(location + "/mouthFrownLeft", arr[20])
                osc_client.send_message(location + "/mouthFrownRight", arr[21])
                osc_client.send_message(location + "/mouthDimpleLeft", arr[22])
                osc_client.send_message(location + "/mouthDimpleRight", arr[23])
                osc_client.send_message(location + "/mouthUpperUpLeft", arr[24])
                osc_client.send_message(location + "/mouthUpperUpRight", arr[25])
                osc_client.send_message(location + "/mouthLowerDownLeft", arr[26])
                osc_client.send_message(location + "/mouthLowerDownRight", arr[27])
                osc_client.send_message(location + "/mouthPressLeft", arr[28])
                osc_client.send_message(location + "/mouthPressRight", arr[29])
                osc_client.send_message(location + "/mouthStretchLeft", arr[30])
                osc_client.send_message(location + "/mouthStretchRight", arr[31])
                # 其余通道可按需补充
            except Exception as e:
                print(f"onnx推理或后处理/OSC发送失败: {e}")
                output_list = []
            
            
            if self.flip_horizontal.isChecked():
                rotated_img = cv2.flip(rotated_img, 1)
            cv2.imshow("Processed", rotated_img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
        cap.release()
        cv2.destroyAllWindows()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = CamOnnxOscApp()
    win.show()
    sys.exit(app.exec_())
