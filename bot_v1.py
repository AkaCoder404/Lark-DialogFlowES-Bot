#!/usr/bin/env python
# --coding:utf-8--

from http.server import BaseHTTPRequestHandler, HTTPServer
from os import path, environ
import json
from urllib import request, parse
from dotenv import load_dotenv
from dialogflow_helper import DialogflowHelper

# 加载 .env 文件中的环境变量
load_dotenv()

APP_ID = environ.get("APP_ID")
APP_SECRET = environ.get("APP_SECRET")
APP_VERIFICATION_TOKEN = environ.get("APP_VERIFICATION_TOKEN")
DIALOGFLOW_PROJECT_ID = environ.get("DIALOGFLOW_PROJECT_ID")
DIALOGFLOW_SESSION_ID = environ.get("DIALOGFLOW_SESSION_ID")
language_code = "en"

print("APP_ID =", APP_ID)
print("APP_SECRET =", APP_SECRET)
print("APP_VERIFICATION_TOKEN =", APP_VERIFICATION_TOKEN)
print("DIALOGFLOW_PROJECT_ID =", DIALOGFLOW_PROJECT_ID)
print("DIALOGFLOW_SESSION_ID =", DIALOGFLOW_SESSION_ID)

df_helper = DialogflowHelper(DIALOGFLOW_PROJECT_ID, 
                             DIALOGFLOW_SESSION_ID, 
                             language_code)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 解析请求 body
        req_body = self.rfile.read(int(self.headers['content-length']))
        obj = json.loads(req_body.decode("utf-8"))


        # 校验 verification token 是否匹配，token 不匹配说明该回调并非来自开发平台
        token = obj.get("token", "") or obj.get("header", {}).get("token", "")
        if token != APP_VERIFICATION_TOKEN:
            print("verification token not match, token =", token)
            self.response("")
            return

        # 根据 type 处理不同类型事件
        event_type = obj.get("type", "") or obj.get("header", {}).get("event_type", "")
        # event_id = obj.get("header", {}).get("event_id", "") # 字段判断事件唯一性
        print("event_type =", event_type)
        if "url_verification" == event_type:  # 验证请求 URL 是否有效
            self.handle_request_url_verify(obj)
        elif "im.message.receive_v1" == event_type:  # 事件回调
            # 获取事件内容和类型，并进行相应处理，此处只关注给机器人推送的消息事件
            event = obj.get("event", {})
            message = event.get("message", {})
            
            if message.get("message_type", "") == "text":
                self.handle_message(message)
                return
        return

    def handle_request_url_verify(self, post_obj):
        # 原样返回 challenge 字段内容
        challenge = post_obj.get("challenge", "")
        rsp = {'challenge': challenge}
        self.response(json.dumps(rsp))
        return

    def handle_message(self, message):
        # 此处只处理 text 类型消息，其他类型消息忽略
        msg_type = message.get("message_type", "")
        if msg_type != "text":
            print("unknown msg_type =", msg_type)
            return
        
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "")
    
        # Message_id 
        print("Message", message)
        print("[RECIEVED]", text)

        # 调用发消息 API 之前，先要获取 API 调用凭证：tenant_access_token
        access_token = self.get_tenant_access_token()
        if access_token == "":
            print("get tenant_access_token failed")
            self.response("")
            return

        # 机器人 echo 收到的消息
        print("[SEND]", message.get("chat_id"), text)
        self.send_message(access_token, message.get("chat_id"), text)
        self.response(json.dumps({"msg": "ok"}))
        return

    def response(self, body):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body.encode())
        # Force the buffer to flush
        # self.wfile.flush()

    def get_tenant_access_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        headers = {
            "Content-Type" : "application/json"
        }
        req_body = {
            "app_id": APP_ID,
            "app_secret": APP_SECRET
        }

        data = bytes(json.dumps(req_body), encoding='utf8')
        req = request.Request(url=url, data=data, headers=headers, method='POST')
        try:
            response = request.urlopen(req)
        except Exception as e:
            print(e.read().decode())
            return ""

        rsp_body = response.read().decode('utf-8')
        rsp_dict = json.loads(rsp_body)
        code = rsp_dict.get("code", -1)
        if code != 0:
            print("get tenant_access_token error, code =", code)
            return ""
        return rsp_dict.get("tenant_access_token", "")

    def send_message(self, token, chat_id, text):
        url = "https://open.feishu.cn/open-apis/message/v4/send/"
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json"
        }
        req_body = {
            "chat_id": chat_id,
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        data = bytes(json.dumps(req_body), encoding='utf8')
        req = request.Request(url=url, data=data, headers=headers, method='POST')
        try:
            response = request.urlopen(req)
            rsp_body = response.read().decode('utf-8')
            print("[RESPONSE]", rsp_body)
        except Exception as e:
            print(e.read().decode())

def run():
    port = 8000
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print("start.....")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
