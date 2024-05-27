#!C:\\ProgramData\\Anaconda3\\python.exe


# MAIN SCRIPT TO RUN THE LOCAL MIDDLEWARE SERVER 

# coding=utf-8
import os 
from pathlib import Path
import openai
import unidecode
import re
import time
from server import Server
from flask import Flask,request, Response
from flask_restful import Resource,Api
import json
import threading
import pandas as pd


#DEFAULT API

app = Flask (__name__, static_url_path='/static', static_folder='static')

api = Api(app)
server = Server()

basePath='/gpt'
whisperPath='/whisper'
chatPath = '/chat'
ytPath = '/youtube'
gptinfoPath = '/gptinfo'   
gptmanagementPath = '/gptmanagement' 

#endpoint of the local http server to mediate between Python2.7 robot controller and OpenAI services
class PromptResource(Resource):
    #request is a dictionary containing question and answer for the related prompt
    def get(self,robot_name):
        prompt = json.loads(request.args['prompt'])
        if prompt is None:
            return 400 #bad request
        response = server.ask(prompt['question'])
        prompt['response'] = response
        return prompt['response'], 200
    
    def post(self,robot_name): #post method triggered at GPT Service startup to instruct ChatGPT with the Instruction Prompt
        try:
            server.startUpGPT(robot_name)
        except:
            return 400
        return 200

class WhisperResource(Resource):  #Whisper endpoint for speech to text translation
    def post(self): 
        try:
            save_path = os.path.join('./audio','voice.wav')
            request.files['audio'].save(save_path)
            transcription = server.whisperTranscribe()
        except:
            return 400
        return transcription,200

class ChattingResource(Resource):
    def get(self,robot_name):  #method used to provide a request to ChatPT and retrieve the answer
        prompt = json.loads(request.args['prompt'])
        if prompt is None:
            return 400 #bad request
        response = server.chatting(robot_name,prompt['question'])
        prompt['response'] = response
        return prompt['response'], 200

    def post(self,robot_name):
        prompt = json.loads(request.args['prompt'])
        if prompt is None:
            return 400 #bad request
        tcpconn = threading.Thread(target=server.send_chat_chunk,args=(robot_name,prompt['question'])) #instantiate udp connection with client
        try:
            tcpconn.start()
            return 200
        except:
            return 500


class GPTInfoResource(Resource):  
    def get(self):
        gpt_model = None
        try:
            gpt_model = server.get_gpt_version()
        except Exception as e:
            print(e)
        if gpt_model is not None:
            print(gpt_model)
            return gpt_model,200
        else:
            return 500


class GPTServerManagement(Resource):  #resource used to reload ChatGPT with the new Instruction Prompt configuration updated after the Error Correction and updated the PromptTable_eval with all the gathered results
    def post(self):
        try:
            server.reload_gpt_server()
        except Exception as e:
            print(e)
            return 500
        return 200



api.add_resource(PromptResource,f'{basePath}/<string:robot_name>')
api.add_resource(WhisperResource,f'{whisperPath}')
api.add_resource(ChattingResource,f'{chatPath}/<string:robot_name>')
api.add_resource(GPTInfoResource,f'{gptinfoPath}')
api.add_resource(GPTServerManagement,f'{gptmanagementPath}')

if __name__=='__main__': #the server runs locally
    app.run(host='127.0.0.1',port=8080,debug=True)