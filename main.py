#!C:\\ProgramData\\Anaconda3\\python.exe

# coding=utf-8
import os 
from pathlib import Path
import openai
import unidecode
import argparse
import re
import time
from server import Server
from flask import Flask,request, Response
from flask_restful import Resource,Api
import json
import threading
import pandas as pd
import speech_recognition as sr
import speech_rec_engine
from speech_rec_engine import SpeechRecEngine



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
speechrecchattingPath = '/speechrecchatting'
speechreccontrolPath = '/speechreccontrol'
whispertranspromptPath = '/whispertransprompt'


def update_prompt_table(question):
        #new_row = {'question' : prompt['question'], 'answer': prompt['response']}
        df1 = pd.read_csv('./data/PromptTable.csv',sep=';')
        df2 = pd.DataFrame([[question, None, None]], columns = ['Question','Answer','Failure']) 
        df = pd.concat([df1,df2],axis=0,ignore_index=False)
        df.to_csv('./data/PromptTable.csv',sep=';',index=False)
        path = './data/PromptTable.csv'
        df = pd.read_csv(path,sep=';')
        gpt_model = server.get_gpt_version()
        df.iloc[-1, df.columns.get_loc('GPT-version')] = gpt_model
        df.to_csv(path,index=False,sep=';')

#endpoint of the local http server to mediate between Python2.7 robot controller and OpenAI services
class PromptResource(Resource):
    #request is a dictionary containing question and answer for the related prompt
    def get(self,robot_name):
        prompt = json.loads(request.args['prompt'])
        if prompt is None:  
            return 400 #bad request
        response = server.ask(prompt['question'])
        prompt['response'] = response
        #Save question and answer on the database
        try:
            #new_row = {'question' : prompt['question'], 'answer': prompt['response']}
            df1 = pd.read_csv('./data/PromptTable.csv',sep=';')
            df2 = pd.DataFrame([[prompt['question'], None, None]], columns = ['Question','Answer','Failure']) 
            df = pd.concat([df1,df2],axis=0,ignore_index=False)
            df.to_csv('./data/PromptTable.csv',sep=';',index=False)
            path = './data/PromptTable.csv'
            df = pd.read_csv(path,sep=';')
            gpt_model = server.get_gpt_version()
            df.iloc[-1, df.columns.get_loc('GPT-version')] = gpt_model
            df.to_csv(path,index=False,sep=';')
        except Exception as e:
            print(e)
            print("Impossibile aggiornare database dei prompt")
        
        return prompt['response'], 200
    
    def post(self,robot_name): #post method triggered at GPT Service startup to instruct ChatGPT with the Instruction Prompt
        intialization_info = json.loads(request.args['conv_context'])
        try:
            server.startUpGPT(robot_name, intialization_info['context'])
        except:
            return 400
        return 200

class WhisperResource(Resource):  #Whisper endpoint for speech to text translation
    def post(self): 
        try:
            save_path = os.path.join('./audio','voice.wav')
            request.files['audio'].save(save_path)
            transcription = server.whisperTranscribe()
        except Exception as e:
            print(e)
            return 400
        return transcription,200
    
class WhisperandGPTPromptResource(Resource):  #Whisper + GPT endpoint for translation and action execution tasks
    def post(self): 
        response = None
        try:
            save_path = os.path.join('./audio','voice.wav')
            request.files['audio'].save(save_path)
            transcription = server.whisperTranscribe()
            question = transcription
            response = server.ask(question)
            update_prompt_table(question=question)
        except Exception as e:
            print(e)
            return 400
        return response,200
        

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

class YoutubeResource(Resource):  
    def get(self,search):
        save_path = None
        try:
            save_path = server.download_music(search)
        except Exception as e:
            print(e)
        if save_path is not None:
            print(save_path)
            return save_path,200
        else:
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
    def get(self):
        update = json.loads(request.args['update'])
        try:
            df1 = pd.read_csv('./PromptTable_eval.csv',sep=';')
            gpt_model = server.get_gpt_version()
            df2 = pd.DataFrame([[update['Question'], update['Answer'], update['Failure'],update['Elapsed Time'],update['Num_tries'],update['Corrected'],gpt_model]], columns = ['Question','Answer','Failure','Elapsed Time','Num_tries','Corrected','GPT-version']) 
            df = pd.concat([df1,df2],axis=0,ignore_index=False)
            df.to_csv('./PromptTable_eval.csv',index=False,sep=';')
        except Exception as e:
            print(e)
            print("Impossibile aggiornare database di evaluation")

    def post(self):
        try:
            server.reload_gpt_server()
        except Exception as e:
            print(e)
            return 500
        return 200


########## Resources dedicated to the speech recognition part to enable interaction with NAO Robot via external wireless microphone, the section is not part of the research paper###########

class SpeechRecForChatting(Resource):
    #app.run(host='127.0.0.1',port=8080,debug=True)
    def post(self,robot_name):  #method used to provide a request to ChatPT and retrieve the answer
        keyword = robot_name.split('.')[0]
        self.speechengine = SpeechRecEngine(keyword,robot_name, 'just_chat')
        speechenginethread = threading.Thread(target=self.speechengine.start) #it must be a non blocking thread, as the speechengine goes in loop and thus blocks the server
        try:
            speechenginethread.start()
        except Exception as e:
            print(e)

class SpeechRecForControl(Resource):
    #app.run(host='127.0.0.1',port=8080,debug=True)
    def post(self,robot_name):  #method used to provide a request to ChatPT and retrieve the answer
        keyword = robot_name.split('.')[0]
        self.speechengine = SpeechRecEngine(keyword, robot_name, 'control')
        speechenginethread = threading.Thread(target=self.speechengine.start) #it must be a non blocking thread, as the speechengine goes in loop and thus blocks the server
        try:
            speechenginethread.start()
            return 200
        except Exception as e:
            print(e)
            return 500
    
    """
    def get(self, robot_name):
        response = None
        while(1):  #try until the response is ready
            if os.path.isfile('./temp/response.txt'):  #if the file exists
                try:
                    print("Retrieving GPT response...")
                    with open('./temp/response.txt', 'r') as file:
                        response = file.read()
                    os.remove('./temp/response.txt')  #remove the file, it will be created again once a new response is needed
                    return response, 200
                except Exception as e:
                    print(e)
                    return 500
    """
########################################################################################################################################

api.add_resource(PromptResource,f'{basePath}/<string:robot_name>')
api.add_resource(WhisperResource,f'{whisperPath}')
api.add_resource(ChattingResource,f'{chatPath}/<string:robot_name>')
api.add_resource(YoutubeResource,f'{ytPath}/<string:search>')
api.add_resource(GPTInfoResource,f'{gptinfoPath}')
api.add_resource(GPTServerManagement,f'{gptmanagementPath}')
api.add_resource(SpeechRecForChatting,f'{speechrecchattingPath}/<string:robot_name>')
api.add_resource(SpeechRecForControl, f'{speechreccontrolPath}/<string:robot_name>')
api.add_resource(WhisperandGPTPromptResource,f'{whispertranspromptPath}')

if __name__=='__main__': #the server runs locally
    
    app.run(host='127.0.0.1',port=8080,debug=True, use_reloader = False)