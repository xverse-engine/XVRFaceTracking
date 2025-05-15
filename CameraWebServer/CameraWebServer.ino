#include "esp_camera.h"
#include <WiFi.h>
#include <esp_wifi.h>
#include "remote_post.h"
//
// WARNING!!! PSRAM IC required for UXGA resolution and high JPEG quality
//            Ensure ESP32 Wrover Module or other board with PSRAM is selected
//            Partial images will be transmitted if image exceeds buffer size
//
//            You must select partition scheme from the board menu that has at least 3MB APP space.
//            Face Recognition is DISABLED for ESP32 and ESP32-S2, because it takes up from 15
//            seconds to process single frame. Face Detection is ENABLED if PSRAM is enabled as well

// ===================
// Select camera model
// ===================
//#define CAMERA_MODEL_WROVER_KIT // Has PSRAM
//#define CAMERA_MODEL_ESP_EYE  // Has PSRAM
//#define CAMERA_MODEL_ESP32S3_EYE // Has PSRAM
//#define CAMERA_MODEL_M5STACK_PSRAM // Has PSRAM
//#define CAMERA_MODEL_M5STACK_V2_PSRAM // M5Camera version B Has PSRAM
//#define CAMERA_MODEL_M5STACK_WIDE // Has PSRAM
//#define CAMERA_MODEL_M5STACK_ESP32CAM // No PSRAM
//#define CAMERA_MODEL_M5STACK_UNITCAM // No PSRAM
//#define CAMERA_MODEL_M5STACK_CAMS3_UNIT  // Has PSRAM
//#define CAMERA_MODEL_AI_THINKER // Has PSRAM
//#define CAMERA_MODEL_TTGO_T_JOURNAL // No PSRAM
#define CAMERA_MODEL_XIAO_ESP32S3 // Has PSRAM
// ** Espressif Internal Boards **
//#define CAMERA_MODEL_ESP32_CAM_BOARD
//#define CAMERA_MODEL_ESP32S2_CAM_BOARD
//#define CAMERA_MODEL_ESP32S3_CAM_LCD
//#define CAMERA_MODEL_DFRobot_FireBeetle2_ESP32S3 // Has PSRAM
//#define CAMERA_MODEL_DFRobot_Romeo_ESP32S3 // Has PSRAM
#include "camera_pins.h"

// ===========================
// Enter your WiFi credentials
// ===========================
// const char *ssid = "OfficeWiFi-17F";
const char *ssid = "asus";
const char *password = "yuanxiang";

void startCameraServer();
void setupLedFlash(int pin);


// for LED , link to D0
int LED_pin = D0; 

JsonDocument streamPayload;
bool startStream = false;


String readMacAddressAsString() {
  uint8_t baseMac[6];
  esp_err_t ret = esp_wifi_get_mac(WIFI_IF_STA, baseMac);
  String macAddress;
  if (ret == ESP_OK) {
    char macStr[18]; // MAC地址长度为17个字符加上一个结束符
    sprintf(macStr, "%02x:%02x:%02x:%02x:%02x:%02x",
            baseMac[0], baseMac[1], baseMac[2],
            baseMac[3], baseMac[4], baseMac[5]);
    macAddress = String(macStr);
  } else {
    macAddress = "FailedReadMacAddress";
  }
  return macAddress;
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG;  // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if (config.pixel_format == PIXFORMAT_JPEG) {
    Serial.printf("find PIXFORMAT_JPEG\n");
    if (psramFound()) {
      Serial.printf("psramFound\n");

      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      Serial.printf("no psramFound\n");
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_QVGA; //FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
      config.jpeg_quality = 12;
    }
  } else {
    Serial.printf("no find PIXFORMAT_JPEG\n");
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  }
  // drop down frame size for higher initial frame rate
  if (config.pixel_format == PIXFORMAT_JPEG) {
    s->set_framesize(s, FRAMESIZE_QVGA);
  }

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

#if defined(CAMERA_MODEL_ESP32S3_EYE)
  s->set_vflip(s, 1);
#endif

// Setup LED FLash if LED pin is defined in camera_pins.h
#if defined(LED_GPIO_NUM)
  setupLedFlash(LED_GPIO_NUM);
#endif

// ////////////////////
//   //Init WiFi as Station, start SmartConfig
//   WiFi.mode(WIFI_AP_STA);
//   WiFi.beginSmartConfig();
//   //Wait for SmartConfig packet from mobile
//   Serial.println("Waiting for SmartConfig.");
//   while (!WiFi.smartConfigDone()) {
//     delay(500);
//     Serial.print(".");
//   }
//   Serial.println("");
//   Serial.println("SmartConfig received.");  
//   //Wait for WiFi to connect to AP
//   Serial.println("Waiting for WiFi");
//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }
//   Serial.println("WiFi Connected.");
// // ////////////////////

  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");

// TODO: 如果摄像头挂了，应该通知后台
  startCameraServer();

  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");

  streamPayload["stream"] = String("http://") + WiFi.localIP().toString() + String(":81/stream") ;
  streamPayload["mac_address"] = readMacAddressAsString();


  // declaring LED pin as output
  pinMode(LED_pin, OUTPUT);
  Serial.print("Set LED_pin set 115\n"); // output Voltage about 1.48v  (  3.3v * 115/255)
  analogWrite(LED_pin, 60 ); 
  // analogWrite(LED_pin, 60); 

  startStream = true;
  post_func( streamPayload );  

}

uint32_t interval = 400; // 500ms
void loop() {
  // delay(10000);
  // the next time that you want to do your action
  static uint32_t nextTime;
  // check if it's time
  if (millis() - nextTime >= interval && startStream)
  {
    // update next time
    nextTime += interval;
    post_func( streamPayload );
  }
}