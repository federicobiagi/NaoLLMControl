# coding=utf-8
#ERROR CORRECTION PIPELINE SCRIPT

from naoqi import ALProxy
from naoqi import ALBroker
import runpy
import os 
from os.path import dirname, abspath
from vocal_commands import *
from record_speech import *
from global_var import *
from ftplib import FTP
from pathlib import Path
import _thread as thread
import naorobot_wrapper
from naorobot_wrapper import NaoRobotWrapper
from naorobot_wrapper import *
import _thread as thread
import argparse
import re
import requests
import json
import threading
import sys
import time
import pandas as pd
import nao_file_transfer
from nao_file_transfer import NAOFileTransfer

class GPT():
    #Initialize all the required modules
    def __init__(self,robot):
        
        parent_folder = dirname(dirname(abspath(__file__)))
        print(parent_folder)

        self.robot = 'gino.local'
        self.Recorder = SpeechRecoder(self.robot)
        self.animspeech = ALProxy("ALAnimatedSpeech",self.robot,9559)
        self.tts = ALProxy("ALTextToSpeech",self.robot,9559)
        self.memory = ALProxy("ALMemory",self.robot,9559)
        self.dialog = ALProxy("ALDialog", self.robot, 9559)
        self.speech = ALProxy("ALTextToSpeech",self.robot,9559)
        self.speech.setLanguage('Italian')
        self.autonomousLife = ALProxy("ALAutonomousLife",self.robot,9559)
        self.leds = ALProxy("ALLeds",self.robot,9559)
        self.AL = ALProxy("ALBasicAwareness",self.robot,9559)
        self.posture = ALProxy("ALRobotPosture",self.robot,9559)
        self.tactile = ALProxy('ALTouch',self.robot,9559)
        self.motion = ALProxy("ALMotion", self.robot, 9559)
        self.lastcorrect = True
        self.questions_with_wrong_execution = []
        self.speechStopped = False

        self.path = None
        self.nao = None
        self.code = None
        self.gpt_model = None
        self.failure = 'No'
        self.num_tries = 0
        self.corrected= 'No'

        vocal_command = VocalCommands()
        print("Vocal Commands initialized")

        self.base_url = 'http://localhost:8080/gpt'
        self.whisper_url = 'http://localhost:8080/whisper'
        self.gptmanagement_url = 'http://localhost:8080/gptmanagement'

        try:
            if self.autonomousLife.getState() != "disabled":
                self.autonomousLife.setState("disabled")
        except:
            pass
 
        if (self.AL.isEnabled() is True):
            self.AL.setEnabled(False)
            print("Basic Awareness disabled")
        self.AL.setStimulusDetectionEnabled('Sound',False)
        self.AL.setStimulusDetectionEnabled('People',False)
        self.AL.setStimulusDetectionEnabled('Movement',False)

        self.posture.post.goToPosture("Stand",0.5)

        #self.dialog.setLanguage("Italian")
        self.memory.insertData("listen","0")
        self.memory.insertData("stop","0")
        self.memory.insertData("block","0")
        self.memory.insertData("okay","0")
        self.memory.insertData("error","0")


        try:
            topiclist = self.dialog.getActivatedTopics()
            for topic in topiclist:
                self.dialog.deactivateTopic(topic)
                self.dialog.unloadTopic(topic)
            if ("Chat" in topiclist):     
                self.dialog.deactivateTopic("Chat")
                self.dialog.unloadTopic("Chat")
            if ("Learn" in topiclist):
                self.dialog.deactivateTopic("Learn")
                self.dialog.unloadTopic("Learn")
        except:
            print("Okay")

        
        selected_robot = self.robot.split('.')
        print("Selected robot: "+ selected_robot[0])

        #Initialize GPT instance with the correct robot name
        self.url = self.base_url+'/{0}'.format(selected_robot[0])
        r = requests.post(self.base_url+'/{0}'.format(selected_robot[0]))
        print('Response code:%d'%r.status_code)
        if(r.status_code == 200):
            print("GPT server correctly initialized")

        r = requests.get('http://localhost:8080/gptinfo')
        if(r.status_code == 200):
            self.gpt_model = r.content.decode()
            self.gpt_model = self.gpt_model.replace('\n','')
            print("Selected GPT model: {}".format(self.gpt_model))

       
        self.topicContent = "topic: ~Chat()\n language: iti\nconcept: (trigger) [{0} ascoltami ascolta]\nconcept: (stop) [ferma fermati]\nconcept: (block) [stop]\nconcept: (yes) [si Si sì Sì]\nconcept: (no) [no No]\nu: (~trigger)  $listen=1\nu: (~stop) Okay $stop=1\nu: (~block) Okay $block=1\nu: (~yes) Okay! $okay=1 \nu: (~no) Mi dispiace, ho sbagliato! $error=1".format(selected_robot[0])


        try:
            self.dialog.unsubscribe("dialog_chat")
        except:
            print("Non existing subscription for Chat Dialog")
        self.topicName = self.dialog.loadTopicContent(self.topicContent)
        print("Topic Name: "+self.topicName)
        self.dialog.activateTopic(self.topicName)
        self.dialog.subscribe('dialog_chat')
        print("Topics attivi:")
        print(self.dialog.getActivatedTopics())
        print("Topics loaded:")
        print(self.dialog.getAllLoadedTopics())


        #NAO is ready
        self.speech.say("Sono pronto")


   
    def stop(self):
        self.speech.stopAll()
        self.AL.setEnabled(True)
        self.AL.setStimulusDetectionEnabled('Sound',True)
        self.AL.setStimulusDetectionEnabled('People',True)
        self.AL.setStimulusDetectionEnabled('Movement',True)
        self.autonomousLife.setState("solitary")
        self.memory.insertData("stop","0")
        self.dialog.unsubscribe("dialog_chat")
        self.dialog.deactivateTopic(self.topicName)
        self.dialog.unloadTopic(self.topicName)
        self.dialog.unloadTopic("Learn")
   
    
    def extract_python_code(self,content):
        code_block_regex = re.compile(r"```(.*?)```",re.DOTALL) 
        code_blocks = code_block_regex.findall(content) 
        if code_blocks:
            full_code = "\n".join(code_blocks) 

            if full_code.startswith("python"):
                full_code = full_code[8:]
                full_code = full_code.replace("\\n", "\n")
                open('./temp/code.txt','w').write(full_code)
   
            return full_code.rstrip()
        else:
            return None


    def execute(self):
        self.AL.setEnabled(False)
        #autonomouseLife.stopFocus()
        #autonomousLife.stopAll()
        self.AL.setStimulusDetectionEnabled('Sound',False)
        self.AL.setStimulusDetectionEnabled('People',False)
        self.AL.setStimulusDetectionEnabled('Movement',False)
        self.speechStopped = False


           
        
        #RECORD USER VOICE
        self.Recorder.record()

        #TRANSFER RECORDED VOICE FROM NAO TO LAPTOP
        try:
            filetransfer = NAOFileTransfer(self.robot,"nao","NAO")
            filetransfer.transfer()
            print("Audio transfer successful")
        except Exception as e:
            print(e)

        ###SEND THE AUDIO TO WHISPER
        audiofile = './sounds/voice.wav'
        with open(audiofile,'rb') as audio:
            r = requests.post(url=self.whisper_url, files={'audio':audio})
        print("Translation: " + r.content.decode())
        answer = r.content.decode()
        command = answer.replace("\n", " ")

        question = command

        #question = open('./temp/question.txt',"r").read() #domanda/comando da sottoporre a GPT
        r = {'question':question, 'response': None}

        self.posture.post.goToPosture("Stand",0.5)

        loadtime = threading.Thread(target=self.no_response_in_due_time) 
        loadtime.start()

        start = time.time() #calculate processing time
        response=requests.get(self.url,params={'prompt':json.dumps(r)})
        print('Gpt Response:\n'+ response.content.decode())
        print('Response code:%d'%response.status_code)
        end = time.time()

        
        print("Elapsed GPT processing time: ")
        elapsed_time = end-start
        print(elapsed_time)

        response = response.content.decode()
        self.code = response
        if '```python' in response:
            self.num_tries = self.num_tries + 1
            print("Attendi mentre eseguo il codice...")
            codeblocks = self.extract_python_code(response)

            #DATASET UPDATE, FOR EVALUATION PURPOSES
            parent_folder = dirname(dirname(abspath(__file__)))
            if 'feder' in parent_folder:   #LOCAL LAPTOP FILES
                self.path = 'C:/Users/feder/Desktop/GPT_Server/data/PromptTable.csv'
            elif 'maria' in parent_folder:
                self.path = 'C:/Users/maria/Desktop/GPT_Server/data/PromptTable.csv'
            df = pd.read_csv(self.path,sep=';')
            manipulated_blocks = codeblocks.replace(',',' ') 
            df.iloc[-1, df.columns.get_loc('Answer')] = manipulated_blocks
            df.iloc[-1, df.columns.get_loc('Elapsed Time')] = elapsed_time
            df.to_csv(self.path,index=False,sep=';')

            #exec(self.extract_python_code(response))
            f = open("./temp/code.txt", "r")
            linesofcode = f.readlines()
            print("Codice da eseguire:")
            linesofcode = [codeline.lstrip() for codeline in linesofcode ]
            print(linesofcode)

            nao = NaoRobotWrapper(self.robot) 
            self.nao = nao
            for code in linesofcode: 
                try:
                    code = code.replace('\n','')
                    print("Step di codice da eseguire: ")
                    print(code)
                    exec(code.replace('\\',""))
                    self.code = None
                except:
                    print("Comando non eseguibile: " + code)
                
            print("Speech Stopped: ")
            print(self.speechStopped)

            
            #CORRECTION AND SELF RECOVERY
            if self.speechStopped == False: 
                    #print("Topic Learn Activated")
                self.memory.insertData("okay","0")  
                self.memory.insertData("error","0")
                self.speech.say("Sono stato bravo?") 

                while(1):  
                    retrieved_okay = self.memory.getData("okay")
                    retrieved_error = self.memory.getData("error")
                    if retrieved_okay == "1":
                        print("Gino did everything right")
                        self.speech.say("Molto bene!")
                        if self.num_tries == 1:
                            self.corrected = 'No'
                            update = {'Question': question,'Answer': response,'Failure':self.failure,'Elapsed Time':elapsed_time, 'Num_tries':self.num_tries,'Corrected':self.corrected}
                            r=requests.get(self.gptmanagement_url,params={'update':json.dumps(update)})
                            self.num_tries = 0
                        if self.lastcorrect == False: 
                            parent_folder = dirname(dirname(abspath(__file__)))
                            path = None
                            if 'feder' in parent_folder:  
                                path = 'C:/Users/feder/Desktop/GPT_Server/'
                            elif 'maria' in parent_folder:
                                path = 'C:/Users/maria/Desktop/GPT_Server/'
                                
                            f = open(path + 'prompts/initial_setup.txt',"a") 
                            f.write('\n\n') # vai a capo due volte
                            print("Question with wrong execution to correct: " + self.questions_with_wrong_execution[0])
                            f.write(self.questions_with_wrong_execution[0] + ':' +'\n') 
                            fcode = open("./temp/code.txt", "r")
                            linesofcode = fcode.readlines()
                            for code in linesofcode: 
                                code = code.replace('\n','').replace('\\',"")
                                f.write(code + '\n')
                            fcode.close()
                            f.close()
                            self.corrected = 'Yes'
                            update = {'Question': self.questions_with_wrong_execution[0],'Answer': str(response),'Failure':self.failure,'Elapsed Time':elapsed_time, 'Num_tries':self.num_tries,'Corrected':self.corrected}
                            r=requests.get(self.gptmanagement_url,params={'update':json.dumps(update)})
                            
                            r = requests.post(url=self.gptmanagement_url)
                            if r.status_code == 200:
                                self.speech.say("Grazie per la correzione!")
                                self.lastcorrect = True
                                self.num_tries = 0
                                self.failure = 'No'
                                self.corrected = 'No'
                                self.questions_with_wrong_execution = []
                            #self.dialog.deactivateTopic(self.topicLearn)
                        self.memory.insertData("okay","0")
                        self.memory.insertData("error","0")
                        df = pd.read_csv(self.path,sep=';')  
                        df.iloc[-1, df.columns.get_loc('Failure')] = 'No'
                        df.to_csv(self.path,sep=';',index=False)
                        break      

                    if retrieved_error == '1':
                        self.failure = 'Yes'
                        print("Gino did something wrong")
                        self.speech.say("Potresti correggermi?")
                        self.posture.post.goToPosture("Stand",0.5)
                        self.questions_with_wrong_execution.append(question)
                        self.lastcorrect = False
                        #self.dialog.deactivateTopic(self.topicLearn)
                        self.memory.insertData("okay","0")
                        self.memory.insertData("error","0")
                        df = pd.read_csv(self.path,sep=';')  #update colonna Failure = Yes
                        df.iloc[-1, df.columns.get_loc('Failure')] = 'Yes'
                        df.to_csv(self.path,sep=';',index=False)
                        break
                self.posture.post.goToPosture("Stand",0.5)
                print("Fatto!")  
        elif '```python' not in response: #if GPT doesnt use python-like method format, gpt just tries to chat with the user through NAO
      
            print("Gino dice:")
            print(response)
            response = response.replace('\n',' ')
            try:
                #self.animspeech = ALProxy("ALAnimatedSpeech",self.robot,9559)
                self.speech.say(str(response)) 
                self.code = None  
            except Exception as e:
                print(e)       
            parent_folder = dirname(dirname(abspath(__file__)))
            if 'feder' in parent_folder: 
                self.path = 'C:/Users/feder/Desktop/GPT_Server/data/PromptTable.csv'
            elif 'maria' in parent_folder:
                self.path = 'C:/Users/maria/Desktop/GPT_Server/data/PromptTable.csv'
            df = pd.read_csv(self.path,sep=';')
            df.iloc[-1, df.columns.get_loc('Answer')] = response
            df.iloc[-1, df.columns.get_loc('Elapsed Time')] = elapsed_time
            df.to_csv(self.path,index=False,sep=';')

            if self.speechStopped == False: 
                    #print("Topic Learn Activated")
                self.speech.say("Sono stato bravo?")
                       
                while(1):  
                    retrieved_okay = self.memory.getData("okay")
                    retrieved_error = self.memory.getData("error")
                    if retrieved_okay == "1":
                        print("Gino did everything right")
                        self.speech.say("Molto bene!")
                        if self.lastcorrect == False: 
                            #salva tale esempio nel prompt testuale di insegnamento
                            parent_folder = dirname(dirname(abspath(__file__)))
                            path = None
                            if 'feder' in parent_folder:   
                                path = 'C:/Users/feder/Desktop/GPT_Server/'
                            elif 'maria' in parent_folder:
                                path = 'C:/Users/maria/Desktop/GPT_Server/'

                            if 'gpt-3.5-turbo' in self.gpt_model:
                                f = open(path + 'prompts/initial_setup.txt',"a") #scrivi in append
                            elif 'gpt-4' in self.gpt_model:
                                f = open(path + 'prompts/initial_setup_gpt4.txt',"a") #scrivi in append
                            f.write('\n\n') # vai a capo due volte
                            print("Question with wrong execution to correct: " + self.questions_with_wrong_execution[0])
                            f.write(self.questions_with_wrong_execution[0] + ':' +'\n') 
                            f.write(str(response))
                            f.close()

                            self.speech.say("Grazie per la correzione!")
                            self.lastcorrect = True
                            self.questions_with_wrong_execution = []
                            #self.dialog.deactivateTopic(self.topicLearn)
                        self.memory.insertData("okay","0")
                        self.memory.insertData("error","0")
                        df = pd.read_csv(self.path,sep=';')  #update colonna Failure = No
                        df.iloc[-1, df.columns.get_loc('Failure')] = 'No'
                        df.to_csv(self.path,sep=';',index=False)
                        break      

                    if retrieved_error == '1':
                        print("Gino did something wrong")
                        self.speech.say("Potresti correggermi?")
                        self.posture.post.goToPosture("Stand",0.5)
                        self.questions_with_wrong_execution.append(question)
                        self.lastcorrect = False 
                        #self.dialog.deactivateTopic(self.topicLearn)
                        self.memory.insertData("okay","0")
                        self.memory.insertData("error","0")
                        df = pd.read_csv(self.path,sep=';')  #update colonna Failure = Yes
                        df.iloc[-1, df.columns.get_loc('Failure')] = 'Yes'
                        df.to_csv(self.path,sep=';',index=False)
                        break
                self.posture.post.goToPosture("Stand",0.5)  #go back to stand posture
                print("Fatto!")  

                
            
            


    #START THE LOOP waiting for the keyword to trigger NAO's recording
    def start(self):
        t = threading.current_thread()
        stopthread = threading.Thread(target=self.check_stop_talk) 
        stopthread.start()
        
           
        while getattr(t,"run",True):
            valask = self.memory.getData("listen")
            valstop = self.memory.getData("stop")
            valblock = self.memory.getData("block") 

            try:
                self.AL.setEnabled(False)
                self.AL.setStimulusDetectionEnabled('Sound',False)
                self.AL.setStimulusDetectionEnabled('People',False)
                self.AL.setStimulusDetectionEnabled('Movement',False)
            except:
                pass

            if valask == "1":
                try:
                    self.speech.post.say("Ti ascolto")
                    #GPT = NaoGPT(autonomousLife,AL)
                    self.execute()
                    #self.posture.post.goToPosture("Stand",1.0)
         
                    if (self.AL.isEnabled() is True):
                        self.AL.setEnabled(False)
                        print("Basic Awareness disabled")
                    self.AL.setStimulusDetectionEnabled('Sound',False)
                    self.AL.setStimulusDetectionEnabled('People',False)
                    self.AL.setStimulusDetectionEnabled('Movement',False)
                    self.memory.insertData("listen","0")
                except Exception as e:
                    print(e)
                    print("Error in GPT speech startup")
                    self.speech.stopAll()
                    self.AL.setEnabled(True)
                    self.AL.setStimulusDetectionEnabled('Sound',True)
                    self.AL.setStimulusDetectionEnabled('People',True)
                    self.AL.setStimulusDetectionEnabled('Movement',True)
                    if self.autonomousLife.getState() == "disabled":
                        self.autonomousLife.post.setState("solitary")
                    self.memory.insertData("stop","0")
                    self.dialog.unsubscribe("dialog_chat")
                    self.dialog.deactivateTopic(self.topicName)
                    self.dialog.unloadTopic(self.topicName)
                    #self.dialog.unloadTopic("Learn")
                    #self.dialog.deactivateTopic(self.topicLearn)
                    #self.dialog.unloadTopic(self.topicLearn)
                    valstop = "1"
                    break #exit GPT
                
            if valstop == "1":
                path = './temp/question.txt'
                resp_file = open(path,"w")
                resp_file.write("Stop")
                resp_file.close()
                self.speech.say("Va bene")
                self.speech.stopAll()
                self.AL.setEnabled(True)
                print("Basic Awareness renabled")
                self.AL.setStimulusDetectionEnabled('Sound',True)
                self.AL.setStimulusDetectionEnabled('People',True)
                self.AL.setStimulusDetectionEnabled('Movement',True)
                if self.autonomousLife.getState() == "disabled":
                    self.autonomousLife.post.setState("solitary")
                self.memory.insertData("stop","0")
                self.dialog.unsubscribe("dialog_chat")
                self.dialog.deactivateTopic(self.topicName)
                self.dialog.unloadTopic(self.topicName)
                #self.dialog.unloadTopic("Learn")
                #self.dialog.deactivateTopic(self.topicLearn)
                #self.dialog.unloadTopic(self.topicLearn)
                self.posture.post.goToPosture("Stand",0.5)
                break #exit GPT

            if valblock == "1": 
                try:
                    self.speech.stopAll()
                    self.nao.stop_behavior() 
                    self.nao.motion_stop()
                    self.posture.post.goToPosture("Stand",0.5)
                    self.memory.insertData("block","0") 
                    self.posture.post.goToPosture("Stand",0.5)
                except Exception as e:
                    print(e)
                    print("Error in stopping task")

        try:
            self.speech.stopAll()
            self.AL.setEnabled(True)
            self.AL.setStimulusDetectionEnabled('Sound',True)
            self.AL.setStimulusDetectionEnabled('People',True)
            self.AL.setStimulusDetectionEnabled('Movement',True)
            if self.autonomousLife.getState() == "disabled":
                self.autonomousLife.post.setState("solitary")
            self.memory.insertData("stop","0")
            self.dialog.unsubscribe("dialog_chat")
            self.dialog.deactivateTopic(self.topicName)
            self.dialog.unloadTopic(self.topicName)
            #self.dialog.unloadTopic("Learn")
            #self.dialog.deactivateTopic(self.topicLearn)
            #self.dialog.unloadTopic(self.topicLearn)
            self.posture.post.goToPosture("Stand",0.5)
        except:
            print("Everything already stopped")
            return



            
    def check_stop_talk(self):
        while(1):
            status = self.tactile.getStatus()
            if status[0][1] == True:  
                #print('Touched')
                self.speech.stopAll()
                try:
                    self.motion.stopMove()
                    self.posture.goToPosture("Stand",0.5)
                except:
                    print("Can't stop moving")
                self.speechStopped = True
                #sys.exit(0)

    def no_response_in_due_time(self):
        lasttime = time.time()
        while(1):
            current = time.time()
            if current - lasttime >=50:
                self.animspeech.say("Mi dispiace, non sono riuscito a generare una risposta in tempo")
                print("Connection problems or heavy network load")
                self.stop()
                sys.exit(0)
            if self.code is not None:  
                break


if __name__ == '__main__':
        Gpt = GPT('gino.local') #for testing purpose
    Gpt.start()
    print("End")
