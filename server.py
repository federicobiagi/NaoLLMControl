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
import threading
from threading import Thread
import concurrent.futures
from queue import Queue
from speech_engine import transcribe
import torch
from transformers import pipeline

class Server(object):
    def __init__(self): 
        self.robot_name = None 
        self.whisper_pipeline = None
        self.device = None
        #Initialize client OpenAI with the correct API key
        #key= os.getenv("OPENAI_API_KEY")
        key = os.getenv("OPENAI_Personal_Key")
        if key is None:
            raise Exception("OpenAI API Key not found")
        self.client = OpenAI(api_key=key)
        self.gpt_model = 'gpt-4.1-mini'
        #self.gpt_model = 'llama'
        print("Selected model for prompting: {}".format(self.gpt_model))
        self.device = 0 if torch.cuda.is_available() else -1
        self.whisper_pipeline = pipeline("automatic-speech-recognition", model="fredbi/whisper-small-italian-tuned", device=self.device)
        print("Whisper model loaded")
        self.llama_pipeline = None
        self.chat_history = []
        self.justchatting_history = []  
        self.que = Queue() 
        self.threads_list = list()

    def download_music(self, search):
        yt = MusicUtility()
        savedpath = yt.download(search)
        return savedpath


    def get_gpt_version(self):
        return self.gpt_model


    def reload_gpt_server(self):  #reload ChatGPT with new instruction prompt configuration
        """
        Server method to reload the ChatGPT instance with a new instruction prompt configuration.
        """
        self.chat_history = []
        self.startUpGPT(self.robot_name)
        print("ChatGPT server reinitialized")
    
    def num_tokens_from_messages(self, messages, model):
        """
        Returns the number of tokens used by a list of messages.
        """
        try:
            if "gpt-4" in model:
                encoding = tiktoken.encoding_for_model("gpt-4-0613")
        except KeyError:
            #encoding = tiktoken.get_encoding(self.gpt_model)
            print("Encoding for the selected model not supported")
        if model == "gpt-3.5-turbo" or "gpt-4o-mini":  # note: future models may deviate from this
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

    """
    def extract_python_code(self,content):
        code_block_regex = re.compile(r"```(.*?)```",re.DOTALL) 
        if code_blocks:
            full_code = "\n".join(code_blocks) 

            if full_code.startswith("python"):
                full_code = full_code[7:]  
            return full_code.rstrip()
        else:
            return None    
    """
        
    def set_robot_name(self,name):
        self.robot_name = name
        pass

    def check_sentiment(self, prompt):
        """
        Method to check the sentiment of the user's request for the error correction algorithm
        """

        instruction = """Sei un bot che deve analizzare le richieste di un utente. Data la frase in input che ti sto per fornire,
        effettua una analisi del sentiment per capire se l'utente è soddisfatto o meno. L'utente non è soddisfatto quando usa nelle frase parole come:
        "hai sbagliato", "non è corretto", "è errato", "hai fatto un errore".
        L'utente è soddisfatto se non specifica le frasi prima riportate.
        Dati i criteri specificati, rispondi con 
        <satisfied> (se l'utente è soddisfatto) 
        <dissatisfied> (se l'utente è insoddisfatto): """                                                       
        try:
            completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages = [{
                "role":"user",
                "content": instruction + "{}".format(prompt)
            }],
            temperature = 0
            )
        except openai.APIError as e:
            print("OpenAI Unknown Error")
            print(e)
            return "Non sono riuscito a fare sentiment analysys"
        except openai.APIConnectionError as e:
            print("OpenAI Connection Error")
            print(e)
            return "Non sono riuscito a fare sentiment analysys"
        except openai.RateLimitError as e:
            print("Token Rate Limit Reached")
            print(e)
            return "Non sono riuscito a fare sentiment analysys"

        sentiment = unidecode.unidecode(str(completion.choices[0].message.content))
        print("The user is "+ sentiment)
        return sentiment  
    

    def send_request_to_model(self, chat_history):
        """
        Method to send a request to the model and get a response, the user request and the response get appended in the chat history
        """
        if "gpt" in self.gpt_model:
            try:
                completion = self.client.chat.completions.create(
                model=self.gpt_model,
                messages= self.chat_history,  
                temperature = 0.3
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
            response = unidecode.unidecode(str(completion.choices[0].message.content))
            print("Tokens in request: {}".format(completion.usage.prompt_tokens))
            print("Tokens in output: {}".format(completion.usage.completion_tokens))
            print("Total tokens processed after request: {}".format(completion.usage.total_tokens))
            return response

        if self.gpt_model == "llama":
            outputs = self.llama_pipeline(
                chat_history,
                max_new_tokens=256,
            )
            response = outputs[0]["generated_text"][-1]['content']
            print("Llama model loaded")
            print("Tokens in request: {}".format(outputs[0]["generated_text"][-1]['prompt_tokens']))
            print("Tokens in output: {}".format(outputs[0]["generated_text"][-1]['completion_tokens']))
            print("Total tokens processed after request: {}".format(outputs[0]["generated_text"][-1]['total_tokens']))
            return response


        
    def ask(self,prompt):
        """
        Method to ask something to ChatGPT and get a response, the user request and the response get appended in the chat history
        """
        #t = Thread(target=lambda q, arg1: q.put(self.check_sentiment(arg1)), args=(self.que, prompt))
        #t.start()
        #with concurrent.futures.ThreadPoolExecutor() as executor:
        #    sentiment_result = executor.submit(self.check_sentiment, prompt)
        #self.threads_list.append(t)

        print(prompt)
        self.chat_history.append(
            {
                "role":"user",
                "content" : prompt
            } )
        #completion = openai.ChatCompletion.create(  #old version
        #the message inserted in the request contains the whole conversation up the i-th timestep, this is done to mantain dialog context
        
        num_input_tokens = self.num_tokens_from_messages(self.chat_history, 'gpt-4o-mini')

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

        response = self.send_request_to_model(self.chat_history)  #send the request to the model and get the response
        
        """
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
        """
        if len(self.chat_history) > 2: #if I'm not initializing ChatGPT
            self.chat_history.append(
                {
                    "role" : "assistant",
                    "content" : response  #insert the response to the user prompt to keep track of the flow of the conversation

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

        #for t in self.threads_list:
        #    t.join()
        #while not self.que.empty():
        #    sentiment = self.que.get()
        
        #if sentiment_result.done() is True:
        #    sentiment = sentiment_result.result()
        #else:
        #    sentiment = '<None>'

        print('Response')
        print(response)
        #response = unidecode.unidecode(str(completion.choices[0].message.content))
        #print(sentiment + response)
        print(response)
        #return sentiment + response  #return gpt response to last request, extracted from the "assistant" field 
        return response

    def startUpGPT(self,robotname,context = " "):#initialize ChatGPT
        
        self.robot_name = robotname
        self.context = context
        print("Context defined: {}".format(self.context))
        """
        self.device = 0 if torch.cuda.is_available() else -1
        self.whisper_pipeline = pipeline("automatic-speech-recognition", model="fredbi/whisper-small-italian-tuned", device=self.device)
        print("Whisper model loaded")
        """

        sysprompt = Path("./system_prompts/initial_setup.txt").read_text(encoding='utf-8')
        sysprompt = context + ' ' + sysprompt
        print("System Prompt:")
        print(sysprompt)
        if '192' in self.robot_name:
           robot_name = 'gino'

        initial_prompt = sysprompt + '\n'
        
        self.chat_history = [
        {
            "role" : "system",  #this role modifies the behavior of the GPT instance and injects the teachings of the Instruction Prompt
            "content" : initial_prompt
        }
        ]

        if self.gpt_model == "llama":
            self.llama_pipeline = pipeline(
                "text-generation",
                model="meta-llama/Llama-3.2-3B-Instruct",
                torch_dtype=torch.bfloat16,
                device_map="auto",
            )
            outputs = self.llama_pipeline(
                self.chat_history,
                max_new_tokens=256,
            )
            print("Llama model loaded")

        
        #self.ask('Ciao {}!'.format(self.robot_name))  #Instruction Prompt provided to ChatGPT, together with an initial greet

        ##PROVO A TOGLIERE LA INITIAL USER REQUEST E PASSO DIRETTAMENTE SYSTEM E BASTA
        if "gpt" in self.gpt_model:
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
            
            #print(str(completion.choices[0].message.content))

            print("ChatGPT loaded")
        print("Benvenuto nel ChatBot Nao!")


    def whisperTranscribe(self):
        path = "./audio/voice.wav"
        audio_file= open(path, "rb")
        #richiesta = self.client.audio.transcriptions.create(model = "whisper-1", file = audio_file, language="it")
        richiesta = self.whisper_pipeline(path)["text"]
        print(richiesta)
        return richiesta
    
####### Code section dedicated to chatting feature (no robot control) with GPT via Nao Robot ###############
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

        """
        Send ChatGPT response via streaming mode, instantiating a socket between the local server and the robot controller to send the response in real-time.
        """

        answer = ''
        self.justchatting_history.append(      
            {
                "role":"system", 
                "content" : "Rispondi come se tu fossi un NAO Robot della SoftBank Robotics di nome {0}, che opera nel reparto Pascia dell'ospedale per aiutare i dottori durante visite a bambini autistici, il tuo ruolo è distrarre il paziente e assisterlo durante la visita. Quando rispondi NON inserire emoticon o emoji nella risposta.".format(robot_name)
                }
             )
        self.justchatting_history.append(
            {
                "role":"user",
                "content" : prompt
            }
            )
        
        print("Length of just chatting history:")
        num_input_tokens = self.num_tokens_from_messages(self.justchatting_history, 'gpt-4o-mini')
        print(num_input_tokens)
        if num_input_tokens >= 16300:  #Iif the user already made 6 chat requests (3 components in the chat list per request), then the older requests are deleted to avoid overload
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
                print(f"MESSAGE {MESSAGE}")
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





#Per fini di debug del server
if __name__=='__main__': #il server runna localmente
    server = Server()

    server.startUpGPT('gino.local')
    #server.send_chat_chunk('gino',"raccontami una storia in tre frasi")

    server.ask("ciao gino come stai?")


