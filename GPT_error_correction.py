# coding=utf-8

# This script handles the Error Correction pipeline

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
    #Initialize all the modules to control the Nao Robot
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

        #Local Server endpoints
        self.base_url = 'http://localhost:8080/gpt'
        self.whisper_url = 'http://localhost:8080/whisper'
        self.gptmanagement_url = 'http://localhost:8080/gptmanagement'


        
        #Deactivate the autonomous life of the robot to prevent the robot from listening to its own voice during ChatGPT usage
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


        #Define variables in the robot's memory 
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

        #The keyword to trigger the robot listening is defined as: gino.local -> keyword = gino
        selected_robot = self.robot.split('.')
        print("Selected robot: "+ selected_robot[0])

        #Ask the Local Server to initialize the ChatGPT service with the current robot's name
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


        #Activate the robot's dialog service
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


        #Nao is ready
        self.speech.say("Sono pronto")


    #When ChatGPT service stops, deallocate the dialog topic and reactivate Autonomous Life on the robot
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
        code_block_regex = re.compile(r"```(.*?)```",re.DOTALL)  #take the python code part in the ChatGPT response
        code_blocks = code_block_regex.findall(content) 
        if code_blocks:
            full_code = "\n".join(code_blocks) #aggregate the sentences and separate them with '\n'

            if full_code.startswith("python"):
                full_code = full_code[8:]  #take the code piece from the 'python' word, till the end of the response 
                full_code = full_code.replace("\\n", "\n")
                open('./temp/code.txt','w').write(full_code)
   
            return full_code.rstrip()
        else:
            return None

    #Activate the listening of the robot and the following answer through GPT
    def execute(self):
        self.AL.setEnabled(False)
        #autonomouseLife.stopFocus()
        #autonomousLife.stopAll()
        self.AL.setStimulusDetectionEnabled('Sound',False)
        self.AL.setStimulusDetectionEnabled('People',False)
        self.AL.setStimulusDetectionEnabled('Movement',False)
        self.speechStopped = False


           
        
        ### RECORD USER'S VOICE ###
        self.Recorder.record()

        ### TRANSFER AUDIO FROM NAO TO LAPTOP VIA FTP
        try:
            filetransfer = NAOFileTransfer(self.robot,"nao","NAO")
            filetransfer.transfer()
            print("Audio transfer successful")
        except Exception as e:
            print(e)

        ###SEND TO WHISPER THE AUDIO.WAV BY QUERYING THE LOCAL SERVER VIA HTTP METHOD
        audiofile = './sounds/voice.wav'
        with open(audiofile,'rb') as audio:
            r = requests.post(url=self.whisper_url, files={'audio':audio})
        print("Translation: " + r.content.decode())
        answer = r.content.decode()
        command = answer.replace("\n", " ")

        question = command

        r = {'question':question, 'response': None}

        self.posture.post.goToPosture("Stand",0.5)

        loadtime = threading.Thread(target=self.no_response_in_due_time) 
        loadtime.start()

        start = time.time() 
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
            print("Wait while I execute the code...")
            codeblocks = self.extract_python_code(response)

            #UPDATE DATABASE WITH REQUESTS AND ANSWERS
            parent_folder = dirname(dirname(abspath(__file__)))
            if 'feder' in parent_folder:   
                self.path = 'C:/Users/feder/Desktop/GPT_Server/data/PromptTable.csv'
            elif 'maria' in parent_folder:
                self.path = 'C:/Users/maria/Desktop/GPT_Server/data/PromptTable.csv'
            df = pd.read_csv(self.path,sep=';')
            manipulated_blocks = codeblocks.replace(',',' ')  #salva codice nel dataset
            df.iloc[-1, df.columns.get_loc('Answer')] = manipulated_blocks
            df.iloc[-1, df.columns.get_loc('Elapsed Time')] = elapsed_time
            df.to_csv(self.path,index=False,sep=';')

            #exec(self.extract_python_code(response))
            f = open("./temp/code.txt", "r")
            linesofcode = f.readlines()
            print("Codice da eseguire:")
            linesofcode = [codeline.lstrip() for codeline in linesofcode ]
            print(linesofcode)

            nao = NaoRobotWrapper(self.robot)  #Nao wrapper to convert the custom methods into NAOqi methods to issue commands to the robot
            self.nao = nao
            for code in linesofcode:   #execute the list of commands ChatGPT produced, sequentially
                try:                    
                    code = code.replace('\n','')
                    print("Code steps to execute: ")
                    print(code)
                    exec(code.replace('\\',""))
                    self.code = None
                except:
                    print("Non executable command: " + code)
                
            print("Speech Stopped: ")
            print(self.speechStopped)
            
            if self.speechStopped == False:  #if the robot didn't stop talking
                  
                self.memory.insertData("okay","0")  
                self.memory.insertData("error","0")
                self.speech.say("Sono stato bravo?")

              #Start the error correction loop
                while(1):  
                    #check if the user is satisfied with the response or not
                    retrieved_okay = self.memory.getData("okay")  #if Nao hears a 'Yes', the "okay" variable is set to '1'
                    retrieved_error = self.memory.getData("error") #if Nao hears a 'No', the "error" variable is set to '1'
                    if retrieved_okay == "1":
                        print("Gino did everything right")
                        self.speech.say("Molto bene!")
                        if self.num_tries == 1:
                            self.corrected = 'No'
                            update = {'Question': question,'Answer': response,'Failure':self.failure,'Elapsed Time':elapsed_time, 'Num_tries':self.num_tries,'Corrected':self.corrected}
                            r=requests.get(self.gptmanagement_url,params={'update':json.dumps(update)})
                            self.num_tries = 0
                        if self.lastcorrect == False: #last response was incorrect, but now the user is satisfied with the answer so Nao needs to save the answer for future requests
                            #save the correct example in the instruction prompt
                            parent_folder = dirname(dirname(abspath(__file__)))
                            path = None
                            if 'feder' in parent_folder:  
                                path = 'C:/Users/feder/Desktop/GPT_Server/'
                            elif 'maria' in parent_folder:
                                path = 'C:/Users/maria/Desktop/GPT_Server/'

                            if 'gpt-3.5-turbo' in self.gpt_model:
                                f = open(path + 'prompts/initial_setup.txt',"a") #append the correct example
                            f.write('\n\n') 
                            print("Question with wrong execution to correct: " + self.questions_with_wrong_execution[0])
                            f.write(self.questions_with_wrong_execution[0] + ':' +'\n') #write the first formulation of the question that resulted in a wrong answer
                            fcode = open("./temp/code.txt", "r")
                            linesofcode = fcode.readlines()
                            for code in linesofcode:  #write the correct code lines for the previously wrong response
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
                        self.lastcorrect = False  #it Nao acted incorrectly, set the lastcorrect variable as False
           
                        self.memory.insertData("okay","0")
                        self.memory.insertData("error","0")
                        df = pd.read_csv(self.path,sep=';') 
                        df.iloc[-1, df.columns.get_loc('Failure')] = 'Yes'
                        df.to_csv(self.path,sep=';',index=False)
                        break
                self.posture.post.goToPosture("Stand",0.5)
                print("Fatto!")  
        elif '```python' not in response:
            #Nao is just chatting with the user and the ChatGPT response is not in python-like format
            print("Gino dice:")
            print(response)
            response = response.replace('\n',' ')
            try:
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

            if self.speechStopped == False:  #if Nao didn't stop talking
                    #print("Topic Learn Activated")
                self.speech.say("Sono stato bravo?")  #Nao asks if it performed good
                       
                while(1):  
                    retrieved_okay = self.memory.getData("okay")
                    retrieved_error = self.memory.getData("error")
                    if retrieved_okay == "1":  
                        print("Gino did everything right")
                        self.speech.say("Molto bene!")
                        if self.lastcorrect == False: 
                            
                            parent_folder = dirname(dirname(abspath(__file__)))
                            path = None
                            if 'feder' in parent_folder:  
                                path = 'C:/Users/feder/Desktop/GPT_Server/'
                            elif 'maria' in parent_folder:
                                path = 'C:/Users/maria/Desktop/GPT_Server/'

                            if 'gpt-3.5-turbo' in self.gpt_model:
                                f = open(path + 'prompts/initial_setup.txt',"a") 
                            f.write('\n\n') 
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
                        df = pd.read_csv(self.path,sep=';')  
                        df.iloc[-1, df.columns.get_loc('Failure')] = 'No'
                        df.to_csv(self.path,sep=';',index=False)
                        break      

                    if retrieved_error == '1':
                        print("Gino did something wrong")
                        self.speech.say("Potresti correggermi?")
                        self.posture.post.goToPosture("Stand",0.5)
                        self.questions_with_wrong_execution.append(question)
                        self.lastcorrect = False  #se ha sbagliato l'esecuzione settiamo questa variabile per correggersi dopo
                        #self.dialog.deactivateTopic(self.topicLearn)
                        self.memory.insertData("okay","0")
                        self.memory.insertData("error","0")
                        df = pd.read_csv(self.path,sep=';')  #update colonna Failure = Yes
                        df.iloc[-1, df.columns.get_loc('Failure')] = 'Yes'
                        df.to_csv(self.path,sep=';',index=False)
                        break
                self.posture.post.goToPosture("Stand",0.5)  #go back to stand posture
                print("Fatto!")  

                
            
            


    #Start the loop waiting for the trigger word "gino" or "ugo" so that the robot may start listening to the user
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

            if valask == "1": #The robot heard the trigger word
                try:
                    self.speech.post.say("Ti ascolto")
                    
                    self.execute()

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
                    valstop = "1"
                    break #exit GPT
                
            if valstop == "1": #if the program gets terminated
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

            if valblock == "1": #if the robot needs to stay silent and stop the current activity
                try:
                    self.speech.stopAll() #try to mute the robot
                    self.nao.stop_behavior() #try to stop the current activity
                    self.nao.motion_stop() #try to stop its motion
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
            if status[0][1] == True: #if the user touches the robot's head, it stops moving and talking
                print('Touched')
                #print('Touched')
                self.speech.stopAll()
                try:
                    self.motion.stopMove()
                    self.posture.goToPosture("Stand",0.5)
                except:
                    print("Can't stop moving")
                self.speechStopped = True
                #sys.exit(0)

    def no_response_in_due_time(self): #subprocess checking for latency problems
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
    Gpt = GPT('gino.local')  #for testing
    Gpt.start()
    print("End")