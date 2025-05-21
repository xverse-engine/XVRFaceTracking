from fastapi import FastAPI
import uvicorn
import threading
import sys
import os

class Filter404Stdout:
    def write(self, s):
        if "-" in s:
            idx = s.find("-")
            line = s[:idx].rstrip()
            # 找到最后一个冒号
            colon_idx = line.rfind(":")
            if colon_idx != -1 and len(line) - colon_idx - 1 >= 1:
                # 替换最后一个冒号后的五个字符为 '81/stream'
                line = line[:colon_idx+1] + '81/stream'
                line =  line[:19]+r'stream URL : http://' + line[19:]
            sys.__stdout__.write(line + "\n")
            threading.Timer(0, os._exit, args=(0,)).start()
        else:
            sys.__stdout__.write(s)
    def flush(self):
        sys.__stdout__.flush()
    def isatty(self):
        return sys.__stdout__.isatty()
sys.stdout = Filter404Stdout()

app = FastAPI()
send_count = 0

def stop_server():
    os._exit(0)

@app.get("/")
async def root():
    global send_count
    if send_count == 0:
        send_count += 1
        return {"message": "服务器运行正常"}
    else:
        return {}

if __name__ == "__main__":
    # # 启动后1秒自动停止服务
    # threading.Timer(3, stop_server).start()
    uvicorn.run(app, host="0.0.0.0", port=8889)