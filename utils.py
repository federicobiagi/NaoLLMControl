# coding=utf-8
#QUESTO FILE CONTIENE FUNZIONI DI UTILITA' PER IL NAO MANAGER
from naoqi import ALProxy
import global_var
import time


class Utils():

    def __init__(self, robot):
        self.robot = robot
        self.AL = ALProxy("ALAutonomousLife", self.robot, 9559)
        self.autonomousLife = ALProxy("ALAutonomousLife", self.robot, 9559)
        self.tactile = ALProxy("ALTouch", self.robot, 9559)
        self.motion = ALProxy("ALMotion", self.robot, 9559)
        self.posture = ALProxy("ALRobotPosture", self.robot, 9559)
        self.speech = ALProxy("ALTextToSpeech", self.robot, 9559)
        self.dialog = ALProxy("ALDialog", self.robot, 9559)
        self.memory = ALProxy("ALMemory", self.robot, 9559)
        self.topicName = ""
        self.topicContent = None

    
    def check_stop_talk(self):
        while(1):
            status = self.tactile.getStatus()
            if status[0][1] == True:  #se gli si tocca la testa si ferma di parlare
                print('Touched')
                self.speech.stopAll()
                try:
                    self.motion.stopMove()
                    self.posture.goToPosture("Stand",0.5)
                except:
                    print("Can't stop moving")
                #sys.exit(0)

    def stop_nao_GPT(self):
        path = './temp/question.txt'
        resp_file = open(path,"w")
        resp_file.write("Stop")
        resp_file.close()
        self.speech.say("Va bene")
        self.speech.stopAll()
        self.autonomousLife.setState("solitary")
        self.memory.insertData("stop","0")
        self.dialog.unsubscribe("dialog_chat")
        self.dialog.deactivateTopic(self.topicName)
        self.dialog.unloadTopic(self.topicName)

    def prepare_nao_GPT(self,robot_name="gino"):
        self.autonomousLife.stopFocus()
        if self.autonomousLife.getState() != "disabled":
            print("Disabling autonomous life")
            self.autonomousLife.setState("disabled")
        self.posture.post.goToPosture("Stand",0.5)
        self.dialog.setLanguage("English")
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
        except:
            print("Okay")
        selected_robot = self.robot.split('.')
        if selected_robot[0] == "192":
            robot_name = 'gino'
        topicContent = "topic: ~Chat()\n language: iti\nconcept: (trigger) [{0} listen]\nconcept: (stop) [ferma fermati]\nconcept: (block) [stop]\nu: (~trigger)  $listen=1\nu: (~stop) Okay $stop=1\nu: (~block) Okay $block=1".format(robot_name)
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

    

class AudioStreamer():
    def __init__(self):
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1  
        self.RATE = 44100  
        self.audio = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out = None
        self.is_streaming = False
    
    def list_audio_devices(self):
        """Lista tutti i dispositivi audio disponibili"""
        print("Dispositivi audio disponibili:")
        print("-" * 50)
        
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            print("ID: {} - {}".format(i, info['name']))
            print("  Canali input: {}".format(info['maxInputChannels']))
            print("  Canali output: {}".format(info['maxOutputChannels']))

            print("  Sample rate: {} Hz".format(info['defaultSampleRate']))
