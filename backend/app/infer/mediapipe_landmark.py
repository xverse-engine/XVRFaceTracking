
# import os
# import sys
# sys.path.append(".")

# import mediapipe as mp
# import numpy as np
# import math
# import time

# '''
# === mediapipe export ARKit52 ===
# _neutral
# browDownLeft
# browDownRight
# browInnerUp
# browOuterUpLeft
# browOuterUpRight
# cheekPuff
# cheekSquintLeft
# cheekSquintRight
# eyeBlinkLeft
# eyeBlinkRight
# eyeLookDownLeft
# eyeLookDownRight
# eyeLookInLeft
# eyeLookInRight
# eyeLookOutLeft
# eyeLookOutRight
# eyeLookUpLeft
# eyeLookUpRight
# eyeSquintLeft
# eyeSquintRight
# eyeWideLeft
# eyeWideRight
# jawForward
# jawLeft
# jawOpen
# jawRight
# mouthClose
# mouthDimpleLeft
# mouthDimpleRight
# mouthFrownLeft
# mouthFrownRight
# mouthFunnel
# mouthLeft
# mouthLowerDownLeft
# mouthLowerDownRight
# mouthPressLeft
# mouthPressRight
# mouthPucker
# mouthRight
# mouthRollLower
# mouthRollUpper
# mouthShrugLower
# mouthShrugUpper
# mouthSmileLeft
# mouthSmileRight
# mouthStretchLeft
# mouthStretchRight
# mouthUpperUpLeft
# mouthUpperUpRight
# noseSneerLeft
# noseSneerRight
# '''

# class MediaPipeLandmark:
#     BaseOptions = mp.tasks.BaseOptions
#     FaceLandmarker = mp.tasks.vision.FaceLandmarker
#     FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
#     FaceLandmarkerResult = mp.tasks.vision.FaceLandmarkerResult
#     VisionRunningMode = mp.tasks.vision.RunningMode

#     def __init__(self):
#         print("Init mediapipe")
#         model = self.BaseOptions(model_asset_path="Models/face_landmarker.task")  # This is the task file.
#         video_options = self.FaceLandmarkerOptions(
#             base_options=model,
#             output_face_blendshapes=True,
#             output_facial_transformation_matrixes=True,
#             num_faces=1,
#             running_mode=self.VisionRunningMode.VIDEO
#         )

#         # image_options = self.FaceLandmarkerOptions(
#         #     base_options=self.BaseOptions(model_asset_path="Models/face_landmarker.task"),
#         #     output_face_blendshapes=True,
#         #     output_facial_transformation_matrixes=True,
#         #     num_faces=1,
#         #     running_mode=self.VisionRunningMode.IMAGE)

#         self.detector = self.FaceLandmarker.create_from_options(video_options)
#         print('------ mediapipe init success-----')

#     def inference(self, image):
#         '''
#         image直接是从video采集的数据
#         '''
#         mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)

#         detection_result = self.detector.detect_for_video(mp_image, int(time.time()*1000) )
#         # Result: FaceLandmarkerResult(face_landmarks=[], face_blendshapes=[], facial_transformation_matrixes=[])

#         if len(detection_result.face_blendshapes) == 0:
#             print(f'{time.time()}. Error no face!')
#             return np.zeros(52)

#         face_blendshapes = detection_result.face_blendshapes[0]

#         result = []
#         for face_blendshapes_category in face_blendshapes:
#             result.append(face_blendshapes_category.score)
#         return np.array(result)

#     def getRTS(self, detection_result):
#         data = {       
#             "Position": {"x": 0.0, "y": 0.0, "z": 0.0},
#             "Rotation": {"x": 0.0, "y": 0.0, "z": 0.0}
#         }
#         if len(detection_result.facial_transformation_matrixes) == 0:
#             return data
    
#         mat = np.array(detection_result.facial_transformation_matrixes[0])
#         # Position is in forth column.
#         data["Position"]["x"] = -mat[0][3]
#         data["Position"]["y"] = mat[1][3]
#         data["Position"]["z"] = mat[2][3]

#         # Rotation matrix are the first 3x3 in matrix. Do some rotation matrix to euler angles magic.
#         data["Rotation"]["x"] = (
#             np.arctan2(-mat[2, 0], np.sqrt(mat[2, 1] ** 2 + mat[2, 2] ** 2))
#             * 180
#             / math.pi
#         )
#         data["Rotation"]["z"] = np.arctan2(mat[1, 0], mat[0, 0]) * 180 / math.pi
#         data["Rotation"]["y"] = np.arctan2(mat[2, 1], mat[2, 2]) * 180 / math.pi
#         return data
