# Xverse VRFace Tracking

<a href="./LICENSE">
        <img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-blue.svg"></a>


[
  <img src="images/XVERSE.jpg" width="800" />
](http://xverse.cn/)



# Introduction

 Xverse VRFace Tracking is a lower face tracking solution developed by XVERSE Technology Inc. (Shenzhen, China), aiming to provide real-time face tracking with any VR headset in different lighting. We have trained a new deep learning model to better detect facial expression changes. Currently, our face tracking project is implemented based on VRface and VRCFaceTracking，leveraging the simplicity and convenience of VRCFT.

We will actively release new features in this repo, please stay tuned. Some future updates will contain:
- [ ] Enhance Facial Expression Prediction
- [ ] Inplement Tongue Expression Prediction
- [ ] Extend Hardware Support for VR Devices

      
Below are examples of our method applied to different VRFace avatars.


  <img src="images/VRface_demo3.gif" width="800" />
  <img src="images/VRface_demo4.gif" width="800" />


# Getting Started

You can make your own camera hardware following [Hardware](#hardware) or contact us via email xengine@xverse.cn to purchase finished products. Below are visuals of the camera’s appearance, installation, and how it looks in use.


 <img src="images/camera.jpg" width="800" />
 
 <img src="images/hardware_install.gif" width="800" />
 
 <img src="images/install_demo.png" width="800" />


## System Requirements
- Windows 10 or 11
- Python 3.12
- VRface and VRCFaceTracking





## Software Install 

The file structure of this project is as below:
```
├── software/                        
│   ├── CameraIPReciver.py              # camera IP reciver
│   └── XverseVRfaceMouthDetectionUI.py # lower face detection UI
├── CameraWebServer/                    # Camera web service
│   ├── app_httpd.cpp                   # HTTP server implementation
│   ├── CameraWebServer.ino             # Arduino main sketch
│   ├── camera_index.h                  # Web interface template
│   ├── camera_pins.h                   # Hardware pin definitions
│   ├── ci.json                         # CI configuration
│   ├── partitions.csv                  # ESP32 partition table
│   ├── README.md                       # README doc
│   ├── remote_post.cpp                 # Remote communication module
│   └── remote_post.h                   # Communication header
├── assets/                             # plugin folder
│   ├── VRCFaceTracking.Xverse.dll      # VRCFT plugin
│   └── XverseConfig.json               # plugin json
├── images/                             # pictures for readme
│   └── ...
├── models/                             # onnx model
│   └── XVRFaceTracking.onnx            # onnx model for lower face tracking         
├── 3D_hardware/                        # hardware files for 3D print 
│   ├── hardware-led.blend              # blend file for 3D print
│   └── hardware-led.stl                # stl file for 3D print
├── requirements.txt                    # Python requriements
├── README.md                           
├── LICENSE                          

```


0.Install the dependency packages listed in [**requriements.txt**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/requirements.txt).

```
pip install -r requirements.txt
```

 1.Install [**ardunio**](https://www.arduino.cc/en/software/). 
 Connect ESP32S3 to your PC with a micro-USB/mini-USB/USB type-c cable. Open [**CameraWebServer.ino**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/CameraWebServer/CameraWebServer.ino)       in [**CameraWebServer**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/CameraWebServer/) via ardunio. Change board type to XIAO_ESP32S3 and fill your WiFi network name and password.

 <img src="images/camerawebserverino.png" width="800" />


 Open [**remote_post.cpp**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/CameraWebServer/remote_post.cpp)       in [**CameraWebServer**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/CameraWebServer/). Fill in your PC IP, verify and upload.

 <img src="images/remotepostcpp.png" width="800" />
 
 You can run 'ipconfig' in terminal to know your PC IP. 
 
<img src="images/ipconfig.png" width="800" />

After successful upload, the arduino will display the notification shown in the figure below.


<img src="images/ardi_sucess.png" width="800" />
 
After uploading [**CameraWebServer**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/CameraWebServer/) to ESP32S3, run  [**CameraIPReciver.py**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/software/CameraIPReciver.py) to recieve Stream URL. Ensure that ports 8889 on your PC is not blocked or already in use.



<img src="images/cameraIPreciever.png" width="800" />






 2.Install [**VRCFaceTracking**](https://github.com/benaclejames/VRCFaceTracking). 
 Drop the VRCFaceTracking.Xverse.dll and XverseConfig.json into AppData\Roaming\VRCFaceTracking\CustomLibs. If you can't find this path, you can use [**Everything**](https://www.voidtools.com/zh-cn/) for search. If this folder does not exist you can create it, VRCFaceTracking will create it on launch.


  <img src="images/CustomLibs.png" width="800" />




 3.Run [**XverseVRfaceMouthDetectionUI.py**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/software/XverseVRfaceMouthDetectionUI.py). 
 Stream Url is from [**CameraIPReciver.py**](https://github.com/xverse-engine/XVRFaceTracking/blob/main/software/CameraIPReciver.py)(step 1). Remeber to keep 'http://' in Stream Url. ONNX file is our pretrained deep learning model in folder [**model**](https://github.com/xverse-engine/XVRFaceTracking/tree/main/models). ONNX Path refers to the file path of the ONNX model on your computer. Generally, the default ONNX path should work. ROI settings can change the region of your capture picture.  For OneEuro filter, you can check the official [**website**](https://gery.casiez.net/1euro/) for reference.




  <img src="images/VRfaceUI.jpg" width="800" />


 


 4.Open VRCFaceTracking and VRChat.
 In VRChat, select an avatar that supports VRCFT and enable OCT. If you are unable to animate the avatar's facial expressions, ensure that ports 8888 and 9000 on your local machine are not blocked or already in use. If you are unable to establish an OSC connection between your PC and VR, please refer to [**VRCFT**](https://docs.vrcft.io/docs/vrcft-software/vrcft) website. Remember to open OSC in your VR device.


  <img src="images/VRCFT.png" width="800" />

  <img src="images/OSCVR.jpg" width="800" />



## Hardware



 

You will need [**Xiao_ESP32S3**](https://wiki.seeedstudio.com/cn/xiao_esp32s3_getting_started/)(It has compact size with both wireless and wired support and no need for additional  antennas) and OV2640 with a viewing angle of 160 degrees. These two components, when powered through the Type-C port, can stream the signal to the computer. Alternative device for Xiao_ESP32S3 is Freenove ESP 32-S3 WROOM, which is larger and  more expensive than Xiao_ESP32S3, and lacks support for an external antenna. Alternative cameras with a narrower viewing angle may reduce recognition accuracy and demand higher lighting conditions. 




  <img src="images/esp32.png" width="800" />

  
Optional components: 3.7V battery, 5mm White Through Hole LED. Either 3.3V or 5V can be used to power the LEDs, however the resistors used will be different. 5V can only be used when powered over USB while 3.3V can be used with both USB and battery power. For 3.3V power: Use 82-ohm resistors in series with the LEDs. For 5V power: Use 160-ohm resistors in series with the LEDs. Connect the GND pin on the ESP32 to the cathode (short leg) of the LED. Add an appropriate resistor (82 ohms for 3.3V, 160 ohms for 5V) in series with the anode (long leg) of the LED. Do not connect LEDs directly to the ESP32 pins without a resistor, as it may damage the LEDs or the microcontroller. Refer to the following figure for LED connection.


  <img src="images/lightLED.png" width="800" />




If you want to connect a battery to the Xiao, we recommend that you purchase a qualified 3.7V rechargeable lithium battery. When soldering the battery, be careful to distinguish the positive and negative terminals. The negative terminal of the battery should be on the side closest to the USB port (BAT-), and the positive terminal of the battery should be on the side away from the USB port (BAT+). Refer to the following two figures for battery connection.


  <img src="images/battery.png" width="800" />







  <img src="images/battery_connect.jpg" width="800" />





Print the model inside folder '3D_hardware'. Currently, our 3D model is provided for the Quest 3. If you require hardware-related assistance or wish to purchase finished products, please contact us via email xengine@xverse.cn. 















