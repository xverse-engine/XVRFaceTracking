#include "remote_post.h"

// 要连接的服务器和端口
const char* remotehost = "http://192.168.50.26";
const int remotehostPort = 8889;

// 生成随机的UUID
String generateUUID() {
    String uuid = "";
    for (int i = 0; i < 16; i++) {
        char c = random(0, 16);
        if (c < 10) c += '0';
        else c += 'a' - 10;
        uuid += c;
    }
    return uuid;
}


String userId =  generateUUID();
// POST 请求的目标 URL
String url = "/facecap?userID=" + userId;

/////////////////////////////////////////////////////////

int post_func(JsonDocument payloadjson){

  String payload;
  serializeJson(payloadjson, payload);
  
  // 创建 HTTP 客户端对象
  HTTPClient http;

  // 配置请求目标
  // String posturl = remotehost;
  // posturl += ":";
  // posturl += remotehostPort;
  // posturl += url;

  String posturl = String(remotehost) + ":" + remotehostPort + url;
  // Serial.println(posturl);

  http.begin(posturl);
  // 设置请求头
  http.addHeader("Content-Type", "application/json");
  // 发送 POST 请求
  int httpCode = http.POST (payload);

  // 检查响应状态码
  if (httpCode > 0) {
    // Serial.print("HTTP Response code: ");
    // Serial.println(httpCode);
    //// 打印响应体
    // String res = http.getString();
    // Serial.println(res);
  } else {
    Serial.print("Error code: ");
    Serial.println(httpCode);
    Serial.println( http.errorToString(httpCode).c_str() );
  }
  // 断开连接
  http.end();

  return httpCode;
}