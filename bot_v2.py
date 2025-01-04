#!/usr/bin/env python
# --coding:utf-8--

from http.server import BaseHTTPRequestHandler, HTTPServer
from os import path, environ
import json
from urllib import request, parse
from dotenv import load_dotenv
import threading
import redis

from dialogflow_helper import DialogflowHelper

# Load environment variables from .env
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

# Redis client
redis_client = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

# Check if message_id already processed
def is_message_processed(message_id: str, expiration_seconds=43200) -> bool:
    """
    Returns True if message_id already processed (exists in Redis),
    else sets it in Redis and returns False.
    """
    if not message_id:
        return True
    
    # If key already exists => duplicated message
    if redis_client.exists(message_id):
        return True
    
    # If not exists => set it, with a 12 hour (43200s) expiration
    redis_client.setex(message_id, expiration_seconds, "processed")
    return False

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read request body
        req_body = self.rfile.read(int(self.headers['content-length']))
        obj = json.loads(req_body.decode("utf-8"))

        # Verify token
        token = obj.get("token", "") or obj.get("header", {}).get("token", "")
        if token != APP_VERIFICATION_TOKEN:
            print("verification token not match, token =", token)
            self.response("")
            return

        # Get event type
        event_type = obj.get("type", "") or obj.get("header", {}).get("event_type", "")
        print("event_type =", event_type)

        if event_type == "url_verification":
            # Respond to Feishu's URL verification challenge
            self.handle_request_url_verify(obj)
            return
        elif event_type == "im.message.receive_v1":
            # Immediately acknowledge receipt so Feishu won't resend:
            self.response(json.dumps({"msg": "ok"}))

            # Spawn a separate thread to handle Dialogflow
            event = obj.get("event", {})
            message = event.get("message", {})
            
            # We'll handle message in a new thread (if it's text, etc.)
            if message.get("message_type", "") == "text":
                t = threading.Thread(target=self.handle_message_in_thread, args=(message, threading.get_ident()))
                t.start()

            return
        else:
            # For other event types, just return 200 quickly
            self.response("")
            return

    def handle_request_url_verify(self, post_obj):
        challenge = post_obj.get("challenge", "")
        rsp = {'challenge': challenge}
        self.response(json.dumps(rsp))

    def handle_message_in_thread(self, message, thread_id):
        """
        This method will run in a background thread to handle:
          - sending user message to Dialogflow
          - getting back the result
          - sending the result to the user
        """
        msg_type = message.get("message_type", "")
        if msg_type != "text":
            print("unknown msg_type =", msg_type)
            return
        

        # Acquire the message_id for dedup
        message_id = message.get("message_id", "")
        
        # If we have already processed this exact message_id, skip
        if is_message_processed(message_id):
            print(f"[DUPLICATE] message_id={message_id} was processed before; ignoring.")
            print(f"Thread {thread_id} finished")
            return
        
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "")
        chat_id = message.get("chat_id", "")
        
        
        print("Message", message)
        print("[RECEIVED]", text)

        # Get tenant access token
        access_token = self.get_tenant_access_token()
        if access_token == "":
            print("get tenant_access_token failed")
            return

        # Pass the user message to Dialogflow
        single_response = df_helper._detect_intent_text(text)
        fulfillment_text = df_helper.get_fulfillment_text(single_response)
        reply_text = fulfillment_text if fulfillment_text else "Sorry, I don't understand."
        print("[SEND]", chat_id, reply_text)
    
        # Asynchronously send message back to user
        self.send_message(access_token, chat_id, reply_text)
        print(f"Thread {thread_id} finished")

    def response(self, body):
        """Send an immediate HTTP 200 response with provided body."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body.encode())

    def get_tenant_access_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        headers = {"Content-Type": "application/json"}
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