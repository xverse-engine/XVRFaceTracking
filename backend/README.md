fastapi构建demo 服务侧代码，用于提供HTTP请求，并对面捕发送的视频流做表情系数拟合并转发。

执行逻辑：在当前包含Dockerfile的目录下，执行
```
docker build -t test-vr-face:base .
```
创建名为test-vr-face:base的镜像

然后执行：
```
docker run --rm -it --gpus all -p 8889:8889 -v "D:\\face\\XVRFaceCap\\log":/app/app/log  test-vr-face:base
```
绑定8889端口以及输出目录映射到本地
