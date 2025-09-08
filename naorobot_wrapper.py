# coding=utf-8

from naoqi import ALProxy
from naoqi import ALBroker
import pandas as pd
import os 
from os.path import dirname, abspath
import time
import math

class NaoRobotWrapper():  #wrapper to convert custom ChatGPT code into NAOqi code for the execution on the robot
    def __init__(self,robot):
        self.robot = robot
        self.motion = ALProxy("ALMotion", self.robot, 9559)  #ALMotion
        self.animspeech = ALProxy("ALAnimatedSpeech", self.robot, 9559)
        self.behaviormanager = ALProxy("ALBehaviorManager", self.robot, 9559) #ALBehaviorManager
        self.speech = ALProxy("ALTextToSpeech",self.robot,9559)
        self.speech.setLanguage('English')
        parent_folder = dirname(dirname(abspath(__file__)))
        self.path = './data/PromptTable.csv'  #csv file to keep track of the results for the performance evaluation


        self.df = pd.read_csv(self.path, sep=';')
        self.motion.wbEnable(True)
        pass

    def update_prompttable_success(self):
        self.df.iloc[-1, self.df.columns.get_loc('Failure')] = 'No'
        self.df.to_csv(self.path,sep=';',index=False)

    def update_prompttable_failure(self):
        self.df.iloc[-1, self.df.columns.get_loc('Failure')] = 'Yes'
        self.df.to_csv(self.path,sep=';',index=False)

    def moveforward(self,X):
        anglelist = None
        try:
            try:
                angleslist = self.motion.getAngles('RShoulderPitch',False)
            except Exception as e:
                print(e)
            leftArmEnable  = True
            rightArmEnable  = True
            if angleslist[0] <= 0: #enables arm movement while walking
                leftArmEnable  = False
                rightArmEnable  = False
            self.motion.setMoveArmsEnabled(leftArmEnable, rightArmEnable)
            self.motion.post.moveTo(X,0.0,0.0)
            print("Nao Robot moves {0} meters forward".format(X))
        except Exception as e:
            print(e)
            

    def movelateral(self,Y):
        angleslist = None
        try:
            try:
                angleslist = self.motion.getAngles('RShoulderPitch',False)  
            except Exception as e:
                print(e)
            leftArmEnable  = True
            rightArmEnable  = True
            if angleslist[0] <= 0: 
                leftArmEnable  = False
                rightArmEnable  = False
            self.motion.setMoveArmsEnabled(leftArmEnable, rightArmEnable)
            self.motion.post.moveTo(0.0,Y,0.0)
            print("Nao Robot moves {0} meters to the right"..format(Y))
        except Exception as e:
            print(e)

        
    def rotate(self,Z):
        try:
            if Z > 3.14:   #if gpt provides a degrees value and not a radians value
                self.motion.post.moveTo(0.0,0.0,math.radians(Z))
            else:
                self.motion.post.moveTo(0.0,0.0,Z)
            print("Nao Robot rotates of {0}".format(Z))
        except Exception as e:
            print(e)
 
        
        
    def bye(self):
        try:
            self.animspeech.post.say("Bye bye pal!")
        except Exception as e:
            print(e)

        
    def say(self,frase):
        try:
            self.speech.say(frase)
            print("Nao robot pronounced a sentence")
        except Exception as e:
            print(e)

        
    
    def setAngle(self,joints,angles):
        jointlist = joints
        jointangles = []
        timelist = []

        for i in angles:
            if i != 'RKneePitch' or i != 'LKneePitch':
                jointangles.append(i*(-1))  #correct the axis convention
                timelist.append(1.0)
            else:
                jointangles.append(i)  
                timelist.append(1.0)

        print("Jointlist:")
        print(jointlist)
        print("Angles value list:")
        print(jointangles)
        
        try:
            absolute = False
            self.motion.angleInterpolation(jointlist,jointangles,timelist,absolute)
        except Exception as e:
            print(e)
            print("Joint configuration is not valid")

    
    def correct_zero_negative(self,jointangles): #it may happen that GPT assigns -0.0 as joint value, thus generating an error
        for i in range(len(jointangles)):
            if abs(jointangles[i]) == 0.0:
                jontangles[i] = 0.0

        return jointangles
                

    #not used with the 'gpt-3.5-model'
    def angleInterpolation(self,joints,angles,times):
        jointlist = joints
        jointangles = angles
        timelist = times
        absolute = False
        jointangles = self.correct_zero_negative(jointangles)
        try:
            self.motion.angleInterpolation(jointlist,jointangles,timelist,absolute)
        except Exception as e:
            print(e)
            print("Joint configuration is not valid")

    def openHand(self,handName):
        try:
            self.motion.post.openHand(handName)
        except Exception as e:
            print(e)
            print("Cannot open Hand")

    def closeHand(self,handName):
        try:
            self.motion.post.closeHand(handName)
        except Exception as e:
            print(e)
            print("Cannot open Hand")


    def motion_stop(self):
        self.motion.stopMove()


#for testing                              
if __name__ == '__main__':
    wrapper = NaoRobotWrapper('gino.local')

    wrapper.moveforward(0.5)
