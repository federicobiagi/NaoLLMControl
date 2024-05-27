# coding=utf-8

# This script handles the configuration of the robot to be able to speak and act through Whisper and ChatGPT 


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
import nao_file_transfer
from nao_file_transfer import NAOFileTransfer

class GPT():

    def __init__(self,robot):
        
        parent_folder = dirname(dirname(abspath(__file__)))
        print(parent_folder)
        
        self.robot = robot
        self.Recorder = SpeechRecoder(robot)
        #NAOqi objects to connect to the robot's modules
        self.animspeech = ALProxy("ALAnimatedSpeech",self.robot,9559)
        vocal_command = VocalCommands()
        self.memory = ALProxy("ALMemory",self.robot,9559)
        self.dialog = ALProxy("ALDialog", self.robot, 9559)
        self.speech = ALProxy("ALTextToSpeech",self.robot,9559)
        self.autonomousLife = ALProxy("ALAutonomousLife",self.robot,9559)
        self.leds = ALProxy("ALLeds",self.robot,9559)
        self.AL = ALProxy("ALBasicAwareness",self.robot,9559)
        self.posture = ALProxy("ALRobotPosture",self.robot,9559)
        self.tactile = ALProxy('ALTouch',self.robot,9559)
        self.nao = None
        self.code = None

        vocal_command = VocalCommands()

        #local server endpoints' url
        self.base_url = 'http://localhost:8080/gpt'
        self.whisper_url = 'http://localhost:8080/whisper'

        
        #Deactivate the autonomous life of the robot to prevent the robot from listening to its own voice during ChatGPT usage
        try:
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
        except:
            pass

        #set the speech service of the robot to Italian language
        self.dialog.setLanguage("Italian")
        self.memory.insertData("listen","0")
        self.memory.insertData("stop","0")
        self.memory.insertData("block","0")

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

        topicContent = "topic: ~Chat()\n language: iti\nconcept: (trigger) [{0} ascoltami ascolta]\nconcept: (stop) [ferma fermati]\nconcept: (block) [stop]\nu: (~trigger)  $listen=1\nu: (~stop) Okay $stop=1\nu: (~block) Okay $block=1".format(selected_robot[0])

        try:
            self.dialog.unsubscribe("dialog_chat")
        except:
            print("Non existing subscription for Chat Dialog")
        self.topicName = self.dialog.loadTopicContent(topicContent)
        print("Topic Name: "+self.topicName)
        self.dialog.activateTopic(self.topicName)
        self.dialog.subscribe('dialog_chat')
        print("Topics attivi:")
        print(self.dialog.getActivatedTopics())
        print("Topics loaded:")
        print(self.dialog.getAllLoadedTopics())


        #Nao is ready
        self.speech.say("Sono pronto")

    #When ChatGPT service stop, deallocate the dialog topic and reactivate Autonomous Life on the robot
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
        if not '```python' in response:
            #Nao is just chatting with the user and the ChatGPT response is not in python-like format
            print("Nao says:")
            print(response)
            try:
                self.speech.say(str(response)) #pronounce the sentence
                self.code = None  
            except Exception as e:
                print(e)
        else: #Nao needs to move/act according to the custom python-like methods, to satisfy the user request
            print("Wait while the code gets executed")
            try:
                codeblocks = self.extract_python_code(response)

                #UPDATE DATABASE WITH REQUESTS AND ANSWERS
                parent_folder = dirname(dirname(abspath(__file__)))
                if 'feder' in parent_folder:  
                    path = 'C:/Users/feder/Desktop/GPT_Server/data/PromptTable.csv'
                df = pd.read_csv(path,sep=';')
                manipulated_blocks = codeblocks.replace(',',' ')
                df.iloc[-1, df.columns.get_loc('Answer')] = manipulated_blocks
                df.iloc[-1, df.columns.get_loc('Elapsed Time')] = elapsed_time
                df.to_csv(path,index=False,sep=';')

                f = open("./temp/code.txt", "r")
                linesofcode = f.readlines()
                print("Code to execute:")
                print(linesofcode)

                nao = NaoRobotWrapper(self.robot)  #Nao wrapper to convert the custom methods into NAOqi methods to issue commands to the robot
                self.nao = nao
                for code in linesofcode:  #execute the list of commands ChatGPT produced, sequentially
                    try:
                        code = code.replace('\n','')
                        print("Code steps to execute: ")
                        print(code)
                        exec(code.replace('\\',""))
                        self.code = None
                    except:
                        print("This command is not executable: " + code)
                print("Fatto!\n")                   
            except Exception as e:
                print(e)
                print("The action cannot be performed")
            


    #Start the loop waiting for the trigger word "gino" or "ugo" so that the robot may start listening to the user
    def start(self):
        t = threading.current_thread()
        stopthread = threading.Thread(target=self.check_stop_talk) 
        stopthread.start()
        
        while getattr(t,"run",True):
            valask = self.memory.getData("listen") 
            valstop = self.memory.getData("stop")
            valblock = self.memory.getData("block") 
            if (self.AL.isEnabled() is True):
                self.AL.setEnabled(False)
                self.AL.setStimulusDetectionEnabled('Sound',False)
                self.AL.setStimulusDetectionEnabled('People',False)
                self.AL.setStimulusDetectionEnabled('Movement',False)

            if valask == "1": #The robot heard the trigger word
                try:
                    self.speech.post.say("Ti ascolto")

                    self.execute() #start recording and execute an action

                    if (self.AL.isEnabled() is True):  #check if the autonomous life is still inactive
                        self.AL.setEnabled(False)
                        print("Basic Awareness disabled")
                    self.AL.setStimulusDetectionEnabled('Sound',False)
                    self.AL.setStimulusDetectionEnabled('People',False)
                    self.AL.setStimulusDetectionEnabled('Movement',False)
                    self.posture.post.goToPosture("Stand",1.0)
                    self.memory.insertData("listen","0")
                except:
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
                    break 
                
            if valstop == "1":  #if the program gets terminated
                path = './temp/question.txt'
                resp_file = open(path,"w")
                resp_file.write("Stop")
                resp_file.close()
                self.speech.say("All right")
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
                break 

            if valblock == "1": #if the robot needs to stay silent and stop the current activity
                try:
                    self.speech.stopAll() #try to mute the robot
                    self.nao.stop_behavior() #try to stop the current activity
                    self.nao.motion_stop() #try to stop its motion
                    self.posture.post.goToPosture("Stand",1.0)
                    self.memory.insertData("block","0") 
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
        except:
            print("Everything already stopped")
            pass

    
    def check_stop_talk(self):
        while(1):
            status = self.tactile.getStatus()
            if status[0][1] == True:  #if the user touches the robot's head, it stops moving and talking
                print('Touched')
                self.speech.stopAll()
                try:
                    self.motion.stopMove()
                    self.posture.goToPosture("Stand",0.5)
                except:
                    print("Can't stop moving")
                #sys.exit(0)

    def no_response_in_due_time(self):  #subprocess checking for latency problems
        lasttime = time.time()
        while(1):
            current = time.time()
            if current - lasttime >=40:
                self.animspeech.say("Sorry, I could not generate a response in time")
                print("Connection problems or heavy network load")
                self.stop()
                sys.exit(0)
            if self.code is not None:  
                break


    def update_prompttable_success(self,df,path):
        df.iloc[-1, df.columns.get_loc('Failure')] = 'No'
        df.to_csv(path,sep=';',index=False)

    def update_prompttable_failure(self,df,path):
        df.iloc[-1, df.columns.get_loc('Failure')] = 'Yes'
        df.to_csv(path,sep=';',index=False)

if __name__ == '__main__':
    Gpt = GPT('gino.local')  #for testing
    Gpt.start()