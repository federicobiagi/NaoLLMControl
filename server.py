#!C:\\ProgramData\\Anaconda3\\python.exe

# coding=utf-8
import os 
from pathlib import Path
import openai
import unidecode
import argparse
import re
import time
import socket
import threading
import pandas as pd
from openai import OpenAI
import prompt_manager
from prompt_manager import PromptManager
import tiktoken

class Server(object):
    def __init__(self): 
        self.robot_name = None 
        
        #Initialize client OpenAI with the correct API key
        key= os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=key)
        self.gpt_model = 'gpt-3.5-turbo'
        print("Selected model for prompting: {}".format(self.gpt_model))
        
        self.chat_history = []
        self.justchatting_history = []  


    def get_gpt_version(self):
        return self.gpt_model


    def reload_gpt_server(self):  #reload ChatGPT with new instruction prompt configuration
        self.chat_history = []
        self.startUpGPT(self.robot_name)
        print("ChatGPT server reinitialized")
    
        
    def set_robot_name(self,name):
        self.robot_name = name
        pass

#Courtesy of OpenAI, this function has been taken from their blog and it calculates the input's tokens
    def num_tokens_from_messages(self, messages, model):
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        if model == "gpt-3.5-turbo" or "gpt-4":  
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "role":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        else:
            raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.""")

    def ask(self,prompt):
        num_input_tokens = self.num_tokens_from_messages(self.chat_history, 'gpt-3.5-turbo')

        if num_input_tokens >= 16300:  #if the request's length has reached the context size limit, the tokens will exceed the context window and ChatGPT will loose the instruction prompt information
            #proceed with the truncation
            first = self.chat_history[:2]  #keep the first 2 elements for the setup (instruction prompt + initial greet to Nao)
            last = self.chat_history[-6:] #keep the last 3 requests, N = 2 
            self.chat_history = first + last 
            print("Chat History Length after cut: ")
            print(len(self.chat_history))
            promptmanager = PromptManager("./system_prompts/initial_setup.txt")
            promptmanager.free_space()
       
        print("Tokens in request: {}".format(num_input_tokens))

        print(prompt)
        self.chat_history.append(
            {
                "role":"user",
                "content" : prompt
            } )
    
        #the message inserted in the request contains the whole conversation up the i-th timestep, this is done to mantain dialog context
        
        
        try:
            completion = self.client.chat.completions.create(
            model=self.gpt_model,
            messages= self.chat_history,  
            temperature = 0
            )
        except openai.APIError as e:
            print("OpenAI Unknown Error")
            print(e)
            return "I can't generate a response for you, please reboot me"  #answerts provided by Nao Robot for any given error
        except openai.APIConnectionError as e:
            print("OpenAI Connection Error")
            print(e)
            return "There was a connection error, please retry"
        except openai.RateLimitError as e:
            print("Token Rate Limit Reached")
            print(e)
            return "I'm tired, I can't cooperate anymore, please reboot me"

        print("Tokens in request: {}".format(completion.usage.prompt_tokens))
        print("Tokens in output: {}".format(completion.usage.completion_tokens))
        print("Total tokens processed after request: {}".format(completion.usage.total_tokens))

        if len(self.chat_history) > 2: #if I'm not initializing ChatGPT, I can save the answer to the previous request
            self.chat_history.append(
                {
                    "role" : "assistant",
                    "content" : unidecode.unidecode(str(completion.choices[0].message.content))  #insert the response to the user prompt to keep track of the flow of the conversation

                }
            )
      
        print("Chat History Length:")
        print(len(self.chat_history))
        
        print('Response')
        response = unidecode.unidecode(str(completion.choices[0].message.content))
        print(response)
        return response  #return gpt response to last request, extracted from the "assistant" field 
        

    def startUpGPT(self,robotname):#initialize ChatGPT
        
        self.robot_name = robotname

        sysprompt = Path("./system_prompts/initial_setup.txt").read_text(encoding='utf-8')
        instruction_prompt = "You are a NAO Robot named {0} who works in the paediatric ward of a hospital and always interacts with children and ".format(self.robot_name) + sysprompt

       
        self.chat_history = [
        {
            "role" : "system",  #this role modifies the behavior of the GPT instance 
            "content" : instruction_prompt
        }
        ]

        self.ask('Hello {}!'.format(self.robot_name))  #Instruction Prompt provided to ChatGPT
        

    def whisperTranscribe(self):
        path = "./audio/voice.wav"
        audio_file= open(path, "rb")
        transcript = self.client.audio.transcriptions.create(model = "whisper-1", file = audio_file, language="it")
        richiesta = transcript.text
        print(richiesta)
        return richiesta
    


if __name__=='__main__': #the server runs locally
    server = Server()
