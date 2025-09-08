# coding=utf-8
from naoqi import ALProxy
from naoqi import ALBroker
from pydub import AudioSegment
from pydub.playback import play
import time
import qi
import paramiko
from ftplib import FTP
import global_var
from global_var import *
import random

#SCRIPT DA INVOCARE PER REGISTRARE UNA FRASE/COMANDO

class SpeechRecoder():
        def __init__(self,robot):
                #self.robot = 'gino.local'
                self.robot = robot
                self.robot_path = "/home/nao/voice1.wav"
                self.pc_path="recordings"
                self.audio = ALProxy("ALAudioRecorder", self.robot, 9559)
                self.player = ALProxy("ALAudioPlayer",self.robot,9559)
                self.animspeech = ALProxy("ALAnimatedSpeech",self.robot,9559)
                self.leds = ALProxy("ALLeds",self.robot,9559)
                self.speech = ALProxy("ALTextToSpeech",self.robot,9559)
                
        
        def record(self):
                self.player.unloadAllFiles()
                lasttime = time.time()
                print("Recording started")
                time.sleep(1.0)
                self.audio.startMicrophonesRecording("/home/nao/voice1.wav","wav",16000,(1,1,1,1))   
                self.leds.post.randomEyes(3.0)
                #while(1):
                #    ts = time.time()
                #    if ts-lasttime > 5:
                #        audio.stopMicrophonesRecording()
                #        print("Stopped recording")
                #        #fileid = player.loadFile("/home/nao/voice1.wav")
                        #print(player.getLoadedFilesNames())
                        #player.play(fileid)
                        #player.unloadAllFiles()
                #        break
                time.sleep(5.0)
                self.audio.stopMicrophonesRecording()
                print("Stopped recording")
                print("Audio saved in nao file system")
                waitingphraselist = ["Ora penso a come risponderti! Dammi un secondo","Ricevuto! Ora ci penso, dammi qualche secondo","Okay, dammi il tempo di pensarci","Certamente!", "Aspetta un attimo"]
                
                self.leds.reset("FaceLeds")
                self.speech.post.say(random.choice(waitingphraselist))
                self.leds.setIntensity("LeftFaceLedsGreen", 0.8)



if __name__ == '__main__':

    robot_path = "/home/nao/voice1.wav"
    pc_path="recordings"
    
    #ftp = FTP("169.254.174.147",user="nao",passwd="NAO")
    #ftp.connect("169.254.174.147",22)
   
    #ftp.login("nao","NAO")
    #try:
    #    ftp.retrlines("RETR " + "voice1.wav", open("voice1.wav",'w').write)
    #except:
    #    print("error")
    #    ftp.quit()


    #NON FUNZIONA, DA PROVARE SU PYTHON 3.9
    #with pysftp.Connection(host="169.254.174.147",username="nao",password="NAO",port = 22) as sftp:
    #    sftp.get("voice1.wav")

    robot = CONNECTED_ROBOT
    audio = ALProxy("ALAudioRecorder", robot, 9559)
    player = ALProxy("ALAudioPlayer",robot,9559)
    animspeech = ALProxy("ALAnimatedSpeech",robot,9559)
    player.unloadAllFiles()
    lasttime = time.time()
    print("Recording started")
    audio.startMicrophonesRecording("/home/nao/voice1.wav","wav",16000,(1,1,1,1))
    leds = ALProxy("ALLeds","gino.local",9559)
    leds.post.randomEyes(3.0)
    #while(1):
    #    ts = time.time()
    #    if ts-lasttime > 5:
    #        audio.stopMicrophonesRecording()
    #        print("Stopped recording")
    #        #fileid = player.loadFile("/home/nao/voice1.wav")
            #print(player.getLoadedFilesNames())
            #player.play(fileid)
            #player.unloadAllFiles()
    #        break
    time.sleep(4.0)
    audio.stopMicrophonesRecording()
    print("Stopped recording")
    print("Audio saved in nao file system")
    leds.reset("FaceLeds")
    animspeech.post.say("Okay")
    leds.post.rasta(10.0)   
    #filepath = qicorefile.openLocalFile("home/nao/recordings/voice1.wav")
    #recorded = AudioSegment.from_wav(filepath)
    #play(recorded)

    #runpy.run_path(path_name='.\Desktop\OpenAI_Python_Middleware\prova_transfer_main.py')

    #oppure prova
    #command = "C:\\ProgramData\\Anaconda3\\python.exe C:\Users\feder\Desktop\OpenAI_Python_Middleware\prova_transfer_main.py"   
    #os.system(command)

    #time.sleep(6)

    #SOCKET READ RESPONSE

    # Create a socket object
    #s = socket.socket()        
    
    # Define the port on which you want to connect
    #port = 12345               
    
    # connect to the server on local computer
    #s.connect(('127.0.0.1', port))
    
    # receive data from the server and decoding to get the string.
    #phrase = s.recv(1024).decode()
    #print(phrase)
    # close the connection
    #s.close()
