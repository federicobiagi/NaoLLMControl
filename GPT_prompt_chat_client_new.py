# coding=utf-8
#Questo file si occupa di porre il robot nelle condizioni di parlare liberamente con GPT e eseguire azioni via Whisper speech to text

from naoqi import ALProxy
from naoqi import ALBroker
import runpy
import os 
from os.path import dirname, abspath
#from vocal_commands import *
from record_speech import *
from global_var import *
from ftplib import FTP
from pathlib import Path
#import _thread as thread
import naorobot_wrapper
from naorobot_wrapper import NaoRobotWrapper
from naorobot_wrapper import *
#import _thread as thread
import argparse
import re
import requests
import json
import threading
import sys
import time
import nao_file_transfer
from nao_file_transfer import NAOFileTransfer
from utils import Utils

class GPT():
    #Inizializza tutti i moduli che servono per usare GPT
    def __init__(self,robot, context):
        
        parent_folder = dirname(dirname(abspath(__file__)))
        print(parent_folder)

        self.robot = robot
        self.Recorder = SpeechRecoder(robot)
        self.Utils = Utils(self.robot)
        self.animspeech = ALProxy("ALAnimatedSpeech",self.robot,9559)
        self.memory = ALProxy("ALMemory",self.robot,9559)
        self.dialog = ALProxy("ALDialog", self.robot, 9559)
        self.speech = ALProxy("ALTextToSpeech",self.robot,9559)
        self.autonomousLife = ALProxy("ALAutonomousLife",self.robot,9559)
        self.leds = ALProxy("ALLeds",self.robot,9559)
        self.AL = ALProxy("ALBasicAwareness",self.robot,9559)
        self.posture = ALProxy("ALRobotPosture",self.robot,9559)
        self.tactile = ALProxy('ALTouch',self.robot,9559)
        self.motion = ALProxy("ALMotion", self.robot, 9559)  #ALMotion
        self.nao = None
        self.code = None

        self.base_url = 'http://localhost:8080/gpt'
        self.whisper_url = 'http://localhost:8080/whisper'
        self.whisper_and_gpt_url = 'http://localhost:8080//whispertransprompt'


        #La keyword per triggerare il robot corrisponde al suo nome nell'ip nominale esempio: gino.local -> keyword = gino
        selected_robot = self.robot.split('.')
        print("Selected robot: "+ selected_robot[0])


        self.Utils.prepare_nao_GPT(selected_robot[0])  #metodo che disabilita la vita autonoma e prepara il robot a parlare con GPT


        #Comunica al Server di inizializzare ChatGpt col nome del robot scelto
        self.url = self.base_url+'/{0}'.format(selected_robot[0])
        context = {'context':context}
        r = requests.post(self.base_url+'/{0}'.format(selected_robot[0]), params={'conv_context':json.dumps(context)})
        print('Response code:%d'%r.status_code)
        if(r.status_code == 200):
            print("GPT server correctly initialized")
        
        r = requests.get('http://localhost:8080/gptinfo')
        if(r.status_code == 200):
            self.gpt_model = r.content.decode()
            self.gpt_model = self.gpt_model.replace('\n','')
            print("Selected GPT model: {}".format(self.gpt_model))
        
        #Notifica che NAO è pronto ad ascoltare
        self.speech.say("I am ready")


    #ripulisce il dialogo e riattiva la vita autonoma al NAO. Metodo da usare quando si stoppa GPT.
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
        code_block_regex = re.compile(r"```(.*?)```",re.DOTALL)  #prende il pezzo di codice che è specificato in "assistant" "content" tra 3 apici inversi
        code_blocks = code_block_regex.findall(content) #trova quanto specificato secondo le regole definite prima con re.compile, cioè estrae il testo compreso tra ```
        if code_blocks:
            full_code = "\n".join(code_blocks) #aggrega le stringhe separandole con un 'a capo'

            if full_code.startswith("python"):
                full_code = full_code[8:]  #prende il codice dalla parola 'python' in poi, non compresa
                full_code = full_code.replace("\\n", "\n")
                open('./temp/code.txt','w').write(full_code)
   
            return full_code.rstrip()
        else:
            return None

    #Avvia ascolto (eventualmente esecuzione di un comando vocale) e risposta con GPT
    def execute(self):
        self.AL.setEnabled(False)
        #autonomouseLife.stopFocus()
        #autonomousLife.stopAll()
        self.AL.setStimulusDetectionEnabled('Sound',False)
        self.AL.setStimulusDetectionEnabled('People',False)
        self.AL.setStimulusDetectionEnabled('Movement',False)


        ### REGISTRA VOCE DELL'UTENTE VIA NAO ROBOT##########################################################
        self.Recorder.record()

        ### TRASFERISCI AUDIO DELLA VOCE DA NAO A LAPTOP
        #runpy.run_path(path_name='./nao_file_transfer.py') #il comando runpy richiede che non via sia un main method nel file
        try:
            filetransfer = NAOFileTransfer(self.robot,"nao","NAO")
            filetransfer.transfer()
            print("Audio transfer successful")
        except Exception as e:
            print(e)

        ###INVIA A WHISPER L'AUDIO INTERROGANDO IL SERVER HTTP
        audiofile = './sounds/voice.wav'
        with open(audiofile,'rb') as audio:
            r = requests.post(url=self.whisper_and_gpt_url, files={'audio':audio})
        print("Translation: " + r.content.decode())
        answer = r.content.decode()
        command = answer.replace("\n", " ")

        question = command

        #question = open('./temp/question.txt',"r").read() #domanda/comando da sottoporre a GPT
        r = {'question':question, 'response': None}

        #self.posture.post.goToPosture("Stand",0.3)

        loadtime = threading.Thread(target=self.no_response_in_due_time) 
        loadtime.start()

        start = time.time() #per calcolo tempo processing di ChatGPT
        response=requests.get(self.url,params={'prompt':json.dumps(r)})
        print('Gpt Response:\n'+ response.content.decode())
        print('Response code:%d'%response.status_code)
        end = time.time()

        #CALCOLO TEMP0 PROCESSING DI GPT
        print("Elapsed GPT processing time: ")
        elapsed_time = end-start
        print(elapsed_time)

        response = response.content.decode()
        self.code = response
        if not '```python' in response:
            #Sta solo chattando con l'utente, non ha prodotto codice
            print("Gino dice:")
            print(response)
            try:
                #self.animspeech = ALProxy("ALAnimatedSpeech",self.robot,9559)
                self.animspeech.say(str(response)) 
                self.code = None  #per far capire al controllo del timeout di risposta che deve ricominciare a controllare dopo
            except Exception as e:
                print(e)
        else:
            print("Attendi mentre eseguo il codice...")
            try:
                codeblocks = self.extract_python_code(response)

                #UPDATE DATABASE CON I RECORD RICHIESTE E RISPOSTE DI GPT
                parent_folder = dirname(dirname(abspath(__file__)))
                if 'feder' in parent_folder:   #il percorso della tabella contente i prompt salvati è diverso a seconda che io avvii nel pc Pascia o nel mio
                    path = 'C:/Users/feder/Desktop/GPT_Server/data/PromptTable.csv'
                elif 'maria' in parent_folder:
                    path = 'C:/Users/maria/Desktop/GPT_Server/data/PromptTable.csv'
                df = pd.read_csv(path,sep=';')
                manipulated_blocks = codeblocks.replace(',',' ')
                df.iloc[-1, df.columns.get_loc('Answer')] = manipulated_blocks
                df.iloc[-1, df.columns.get_loc('Elapsed Time')] = elapsed_time
                df.to_csv(path,index=False,sep=';')

                #exec(self.extract_python_code(response))
                f = open("./temp/code.txt", "r")
                linesofcode = f.readlines()
                #print("Codice da eseguire:")
                #print(linesofcode)

                nao = NaoRobotWrapper(self.robot)  #prova se funziona altrimenti metti la definizione della classe in questo script
                self.nao = nao
                for code in linesofcode:  #esegui la lista di metodi che GPT ha prodotto
                    try:
                        #print("Codice da eseguire: " + code)
                        code = code.replace('\n','')
                        print("Step di codice da eseguire: ")
                        print(code)
                        exec(code.replace('\\',""))
                        self.code = None
                    except:
                        print("Comando non eseguibile: " + code)
                print("Fatto!\n")                   
            except Exception as e:
                print(e)
                print("Impossibile eseguire l'azione")
            
    def execute_whisper_and_gpt(self): ####QUESTO METODO INVIA A WHISPER AUDIO E SENZA RITORNARE LA TRASCRIZIONE, COMPUTA LA RISPOSTA CON GPT PER RISPARMIARE TEMPO##########
        
        """"
        self.AL.setEnabled(False)
        #autonomouseLife.stopFocus()
        #autonomousLife.stopAll()
        self.AL.setStimulusDetectionEnabled('Sound',False)
        self.AL.setStimulusDetectionEnabled('People',False)
        self.AL.setStimulusDetectionEnabled('Movement',False)
        """

        ### REGISTRA VOCE DELL'UTENTE VIA NAO ROBOT##########################################################
        self.Recorder.record()

        ### TRASFERISCI AUDIO DELLA VOCE DA NAO A LAPTOP
        #runpy.run_path(path_name='./nao_file_transfer.py') #il comando runpy richiede che non via sia un main method nel file
        try:
            filetransfer = NAOFileTransfer(self.robot,"nao","NAO")
            filetransfer.transfer()
            print("Audio transfer successful")
        except Exception as e:
            print(e)

        ###INVIA A WHISPER L'AUDIO INTERROGANDO IL SERVER HTTP E ATTENDI LA RISPOSTA DI GPT CON I COMANDI DA ESEGUIRE
        audiofile = './sounds/voice.wav'
        with open(audiofile,'rb') as audio:
            loadtime = threading.Thread(target=self.no_response_in_due_time) 
            loadtime.start()
            start = time.time() #per calcolo tempo processing di ChatGPT + Whisper
            r = requests.post(url=self.whisper_and_gpt_url, files={'audio':audio})
            response = r.content.decode()
            print('Gpt Response:\n'+ response)
            end = time.time()
            #self.posture.post.goToPosture("Stand",0.3)

        #CALCOLO TEMP0 PROCESSING DI GPT
        print("Elapsed GPT processing time: ")
        elapsed_time = end-start
        print(elapsed_time)

        self.code = response
        if not '```python' in response:
            #Sta solo chattando con l'utente, non ha prodotto codice
            print("Gino dice:")
            print(response)
            try:
                #self.animspeech = ALProxy("ALAnimatedSpeech",self.robot,9559)
                self.speech.say(str(response)) 
                self.code = None  #per far capire al controllo del timeout di risposta che deve ricominciare a controllare dopo
            except Exception as e:
                print(e)
        else:
            print("Attendi mentre eseguo il codice...")
            try:
                codeblocks = self.extract_python_code(response)

                #UPDATE DATABASE CON I RECORD RICHIESTE E RISPOSTE DI GPT
                parent_folder = dirname(dirname(abspath(__file__)))
                if 'feder' in parent_folder:   #il percorso della tabella contente i prompt salvati è diverso a seconda che io avvii nel pc Pascia o nel mio
                    path = 'C:/Users/feder/Desktop/GPT_Server/data/PromptTable.csv'
                elif 'maria' in parent_folder:
                    path = 'C:/Users/maria/Desktop/GPT_Server/data/PromptTable.csv'
                df = pd.read_csv(path,sep=';')
                manipulated_blocks = codeblocks.replace(',',' ')
                df.iloc[-1, df.columns.get_loc('Answer')] = manipulated_blocks
                df.iloc[-1, df.columns.get_loc('Elapsed Time')] = elapsed_time
                df.to_csv(path,index=False,sep=';')

                #exec(self.extract_python_code(response))
                f = open("./temp/code.txt", "r")
                linesofcode = f.readlines()
                print("Codice da eseguire:")
                print(linesofcode)

                nao = NaoRobotWrapper(self.robot)  #prova se funziona altrimenti metti la definizione della classe in questo script
                self.nao = nao
                for code in linesofcode:  #esegui la lista di metodi che GPT ha prodotto
                    try:
                        #print("Codice da eseguire: " + code)
                        code = code.replace('\n','')
                        print("Step di codice da eseguire: ")
                        print(code)
                        exec(code.replace('\\',""))
                        self.code = None
                    except:
                        print("Comando non eseguibile: " + code)
                print("Fatto!\n")                   
            except Exception as e:
                print(e)
                print("Impossibile eseguire l'azione")

    #Avvia il loop di attesa della trigger word "gino" o "ugo" per iniziare ad ascoltare la richiesta dell'utente    
    def start(self):
        t = threading.current_thread()
        stopthread = threading.Thread(target=self.Utils.check_stop_talk) #thread che controlla se l'utente tocca la testa del robot per fermarlo
        stopthread.start()
        
        while getattr(t,"run",True):
            valask = self.memory.getData("listen")
            valstop = self.memory.getData("stop")
            valblock = self.memory.getData("block") 
            #self.autonomousLife.setState("disabled")

            if valask == "1":
                try:
                    self.speech.post.say("I am listening")
                    ######VERSIONE PIU' VELOCE CON WHISPER E GPT ESEGUITI INSIEME NELLO STESSO SERVER METHOD
                    self.execute_whisper_and_gpt()

                    """
                    if (self.AL.isEnabled() is True):
                        self.AL.setEnabled(False)
                        print("Basic Awareness disabled")
                    self.AL.setStimulusDetectionEnabled('Sound',False)
                    self.AL.setStimulusDetectionEnabled('People',False)
                    self.AL.setStimulusDetectionEnabled('Movement',False)
                    self.posture.post.goToPosture("Stand",0.5)
                    """
                    while 1:  #controlla se ha smesso di muoversi prima di abbassare le braccia
                        try:
                            if self.motion.moveIsActive() is False:
                                if self.motion.getAngles('LHipRoll',True) > 0.1 or self.motion.getAngles('RHipRoll',True) < -0.1:
                                    self.posture.goToPosture("Stand",0.5) #se le gambe sono aperte, torna in posizione eretta
                                    break
                                self.motion.closeHand("LHand")
                                self.motion.closeHand("RHand")
                                self.motion.setAngles(['LShoulderPitch','RShoulderPitch'], [1.43, 1.43], 0.3) 
                                self.motion.setAngles(['RElbowRoll','LElbowRoll'], [0.0349,-0.0349], 0.3)
                                self.motion.setAngles(["LHipYawPitch","LHipRoll","LHipPitch","LKneePitch","LAnklePitch","LAnkleRoll","RHipYawPitch","RHipRoll","RHipPitch","RKneePitch","RAnklePitch","RAnkleRoll"],[0.0,0.0925024504,0.0,0.0,0.0,0.0,0.0,-0.0925024504,0.0,0.0,0.0,0.0],0.2)
                                break
                        except Exception as e:
                            pass
                    self.memory.insertData("listen","0")
                except:
                    #se c'è un errore, ferma il robot 
                    valstop = "1"
                    break #exit GPT
                
            if valstop == "1":
                break #exit GPT

            if valblock == "1": #se deve stoppare l'attività che sta facendo ma non il programma
                try:
                    self.speech.stopAll() #prova a mutarlo
                    self.nao.stop_behavior() #prova a fermare il behavior in corso
                    self.nao.motion_stop() #prova a fermare il movimento
                    self.posture.post.goToPosture("Stand",0.5)
                    self.memory.insertData("block","0") 
                except Exception as e:
                    print(e)
                    print("Error in stopping task")
        
        
        self.Utils.stop_nao_GPT()
        print("Stopping GPT")

    def no_response_in_due_time(self):
        lasttime = time.time()
        while(1):
            current = time.time()
            if current - lasttime >=40:
                self.animspeech.say("Mi dispiace, non sono riuscito a generare una risposta in tempo")
                print("Connection problems or heavy network load")
                self.stop()
                sys.exit(0)
            if self.code is not None:  #se del codice è stato prodotto nel mentre, stoppa questo thread
                break


    def update_prompttable_success(self,df,path):
        df.iloc[-1, df.columns.get_loc('Failure')] = 'No'
        df.to_csv(path,sep=';',index=False)

    def update_prompttable_failure(self,df,path):
        df.iloc[-1, df.columns.get_loc('Failure')] = 'Yes'
        df.to_csv(path,sep=';',index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Start GPT chat client for NAO Robot")
    parser.add_argument('--robot_ip', type=str, required=True, help='IP address of the NAO Robot')
    args = parser.parse_args()
    robot_ip = args.robot_ip
    Gpt = GPT(robot_ip, "You are a NAO Robot that helps children at the hospital") 
    Gpt.start()

