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
import threading
from threading import Thread
import concurrent.futures
from queue import Queue


class Server(object):
    def __init__(self): 
        self.robot_name = None 
        
        #Initialize client OpenAI with the correct API key
        key= os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=key)
        #self.finetuner = FineTuner(self.client)
        #self.gpt_model = self.finetuner.get_custom_model_name()
        self.gpt_model = 'gpt-4-turbo'  #default model to use for the server
        print("Selected model for prompting: {}".format(self.gpt_model))
        
        self.chat_history = []
        self.justchatting_history = []  
        self.que = Queue() 
        self.threads_list = list()

    def get_gpt_version(self):
        return self.gpt_model


    def reload_gpt_server(self):  #reload ChatGPT with new instruction prompt configuration
        self.chat_history = []
        self.startUpGPT(self.robot_name)
        print("ChatGPT server reinitialized")
    
    def num_tokens_from_messages(self, messages, model):
        """Returns the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(self.gpt_model)  
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "role":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        except Exception as e:
            print(e)
            raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {self.gpt_model}.""")

            
    def set_robot_name(self,name):
        self.robot_name = name
        pass

        
    def ask(self,prompt):
        print(prompt)
        self.chat_history.append(
            {
                "role":"user",
                "content" : prompt
            } )
        #the message inserted in the request contains the whole conversation up the i-th timestep, this is done to mantain dialog context
        
        num_input_tokens = self.num_tokens_from_messages(self.chat_history, self.gpt_model)

        if num_input_tokens >= 16300:  #if the request's length has reached the context size limit, the tokens will exceed the context window and ChatGPT will loose the instruction prompt information
            #proceed with the truncation
            first = self.chat_history[:2]  #keep the first 2 elements for the setup (instruction prompt + initial greet to Nao)
            last = self.chat_history[-4:] #keep the last N = 3 requests
            self.chat_history = first + last 
            print("Chat History Length after cut: ")
            print(len(self.chat_history))
            promptmanager = PromptManager("./prompts/initial_setup.txt")
            promptmanager.free_space()
       
        print("Tokens in request: {}".format(num_input_tokens)) 
        
        try:
            completion = self.client.chat.completions.create(
            model=self.gpt_model,
            messages= self.chat_history,  
            temperature = 0
            )
        except openai.APIError as e:
            print("OpenAI Unknown Error")
            print(e)
            return "I could not generate an answer, I am sorry, please reboot me"
        except openai.APIConnectionError as e:
            print("OpenAI Connection Error")
            print(e)
            return "There has been a connection problem, reboot"
        except openai.RateLimitError as e:
            print("Token Rate Limit Reached")
            print(e)
            return "I am tired, I cannot talk anymore, reboot me"

        print("Tokens in request: {}".format(completion.usage.prompt_tokens))
        print("Tokens in output: {}".format(completion.usage.completion_tokens))
        print("Total tokens processed after request: {}".format(completion.usage.total_tokens))

        if len(self.chat_history) > 2: #if I'm not initializing ChatGPT
            self.chat_history.append(
                {
                    "role" : "assistant",
                    "content" : unidecode.unidecode(str(completion.choices[0].message.content))  #insert the response to the user prompt to keep track of the flow of the conversation

                }
            )
      
        print("Chat History Length:")
        print(len(self.chat_history))
        #if len(self.chat_history) >= 19:  #if there are at least 8 user requests (5 required for the setup + 16 user messages) then I free the chat history from older requests to avoid token limit issue
        #    first = self.chat_history[:5]  #keep the first 5 elements for the setup
        #    last = self.chat_history[-2:] #keep the last request
        #    self.chat_history = first + last 
        #    print("Chat History Length after cut: ")
        #    print(len(self.chat_history))
        

        print('Response')
        response = unidecode.unidecode(str(completion.choices[0].message.content))
        print(response)
        return response  #return gpt response to last request, extracted from the "assistant" field 

    def startUpGPT(self,robotname):#initialize ChatGPT
        
        self.robot_name = robotname
        
        #parser = argparse.ArgumentParser()
        #parser.add_argument("--prompt",type=str,default="prompts/initial_setup.txt")
        #parser.add_argument("--sysprompt",type=str,default="system_prompts/initial_setup.txt")
        #args = parser.parse_args()

        sysprompt = Path("./system_prompts/initial_setup.txt").read_text(encoding='utf-8')
        sysprompt = "You are a NAO Robot named {0} that works in the pediatric department of an hospital and you must always interact with children, ".format(self.robot_name) + sysprompt
        
        self.chat_history = [
        {
            "role" : "system",  #this role modifies the behavior of the GPT instance and injects the teachings of the Instruction Prompt
            "content" : sysprompt
        }
        ]

        try:
            completion = self.client.chat.completions.create(
            model=self.gpt_model,
            messages= self.chat_history,  
            temperature = 0
            )
        except openai.APIError as e:
            print("OpenAI Unknown Error")
            print(e)
            return "Non sono riuscito a generare una risposta, mi dispiace, riavviami"
        except openai.APIConnectionError as e:
            print("OpenAI Connection Error")
            print(e)
            return "C'è stato un errore di connessione, riavviami"
        except openai.RateLimitError as e:
            print("Token Rate Limit Reached")
            print(e)
            return "Sono stanco, non riesco più a parlare, riavviami"
        
        print("ChatGPT loaded")
        print("Benvenuto nel ChatBot Nao!")


    def whisperTranscribe(self):
        path = "./audio/voice.wav"
        audio_file= open(path, "rb")
        transcript = self.client.audio.transcriptions.create(model = "whisper-1", file = audio_file, language="it")
        richiesta = transcript.text
        print(richiesta)
        return richiesta
    
####### Code section dedicated to chatting feature (no robot control) with GPT via Nao Robot, not part of the Research Project ###############
    def checkClientStop(self,sock):
        try:
            tostop, address = sock.recv(1024)
            if tostop.decode('utf-8') == 'stop': #if it receives a stop signal by the client, it meas that the user requested the robot to stop talking and the socket between local server and robot controller must be closed
                try:
                    sock.close()
                    print("Stopped response")
                except Exception as e:
                    print(e)
        except:
            pass
    
    def send_chat_chunk(self,robot_name,prompt):
        answer = ''
        self.justchatting_history.append(      
            {
                "role":"system", 
                "content" : "Answer as if you are a NAO Robot of SoftBank Robotics named {0}, who works in the Pascia department of the hospital to help doctors during the examinations to autistic choldren. Your role is to distract the patient and assist him during the examination".format(robot_name)
                }
             )
        self.justchatting_history.append(
            {
                "role":"user",
                "content" : prompt
            }
            )
        
        print("Length of just chatting history:")
        num_input_tokens = self.num_tokens_from_messages(self.justchatting_history, self.gpt_model)
        print(num_input_tokens)
        if num_input_tokens >= 16300:  #If the user already made 6 chat requests (3 components in the chat list per request), then the older requests are deleted to avoid overload
            self.justchatting_history = self.justchatting_history[-8:] #keep only the last 2 requests + the latest request that still waits for an answer

        TCP_IP = "127.0.0.1"
        TCP_PORT = 1025      
        
        sock = socket.socket(socket.AF_INET, # Internet
                    socket.SOCK_STREAM) # TCP
        sock.bind((TCP_IP,TCP_PORT))
        sock.listen(1)
        conn,addr = sock.accept()
        print("Connection with Client established")
        conn.settimeout(0.1)

        response = self.client.chat.completions.create(
        model=self.gpt_model,
           messages = self.justchatting_history,
            temperature = 0.5,
            stream = True
        )

        for chunck in response:
            try:
                tostop, address = conn.recvfrom(1024)
                #print('To Stop value:' + tostop)
                if tostop.decode('utf-8') == 'stop': #if the local server receives a stop signal, it means the robot has been ordered to stop talking e and the socket has been closed client-side
                    try:
                        print(tostop.decode('utf-8'))
                        sock.close()
                        print("Stopped response")
                        break
                    except Exception as e:
                        print(e)
            except:
                pass
            try:
                print(chunck.choices[0].delta.content)
                MESSAGE = chunck.choices[0].delta.content
                answer = answer + str(MESSAGE)
                conn.send(MESSAGE.encode('latin-1'))
            except Exception as e:
                print("Response ended or Stop Signal triggered")
                print(e)
                #sock.close()
                break
        try:
            #sock.sendto(str.encode("STOP."), (UDP_IP, UDP_PORT))  #end of transmission
            conn.send(str.encode("STOP."))
            print("STOP. sent")
            conn.close()
            self.justchatting_history.append(
            {
                "role" : "assistant",
                "content" : answer  #insert the response as a teaching for the assistant role to keep track of the conversation

            }
            )
            path = './data/PromptTable.csv'
            df = pd.read_csv(path,sep=';')
            df.iloc[-1, df.columns.get_loc('GPT-version')] = self.gpt_model
            df.to_csv(path,index=False,sep=';')    
        except Exception as e:
            print(e)
            print("Socket closed via client request")





#For server debug purposes
if __name__=='__main__': #the server runs locally
    server = Server()
    server.startUpGPT('gino.local')
    server.ask("Hi gino how are you?")

