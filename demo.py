#!C:\\ProgramData\\Anaconda3\\python.exe

# coding=utf-8
#Demo script to show the output ChatGPT is able to produce based on the provided Instruction Prompt
#Produced code must then be processed by the Nao Wrapper in the naorobot_wrapper.py script so that Nao Robot may execute the actions

import re
import requests
import json
import socket
import time

base_url='http://localhost:8080/gpt'
gptmanagement_url = 'http://localhost:8080/gptmanagement'

def extract_python_code(content):
    code_blocks = content
    if code_blocks:
        code_blocks = code_blocks.replace("\\n", "\n")
        code_blocks = code_blocks.replace("\"","")
        code_blocks = code_blocks.replace("```python","")
        code_blocks = code_blocks.replace("```","")
        open('./temp/code.txt','w').write(code_blocks)
   
        return code_blocks.rstrip()
    else:
        return None

def save_previous_code(content):
    code_blocks = content
    if code_blocks:
        code_blocks = code_blocks.replace("\\n", "\n")
        code_blocks = code_blocks.replace("\"","")
        code_blocks = code_blocks.replace("```python","")
        code_blocks = code_blocks.replace("```","")
        open('./temp/previous_code.txt','w').write(code_blocks)
   
        return code_blocks.rstrip()
    else:
        return None


lastcorrect = True
question_with_wrong_execution = []
r = requests.post(base_url+'/gino')
print('Response code:%d'%r.status_code)

print("Ready to communicate with Server")

print("Do you want to activate the Error Correction algorithm? (y/n)")
error_corr_mode = input("-> ")

if error_corr_mode == 'y':
    while(1):
        print("Insert request:  'exit'-> shut down")
        question = input('->  ')
        if question == 'exit':
            break
        r = {'question':question, 'response': None}
        response=requests.get(base_url + '/gino',params={'prompt':json.dumps(r)})
        print('Response code:%d'%response.status_code)

        response = response.content.decode()
        #code = extract_python_code(response)
        print('Code:\n'+ response)


        correctness = input("Have I done well? (y/n) ")


        if correctness == 'y':
            last_question = question
            retrieved_okay = 1
        if correctness == 'n':
            print("nao.say(\"I'm sorry, I'll try to correct myself\")")
            #question_with_wrong_execution.append(question)
            retrieved_okay = 0
        
            

        if retrieved_okay == 1:
            #print("Gino did right")
            if lastcorrect == False:
                print("nao.say(\"All right!\")")
                f = open('./system_prompts/initial_setup.txt',"a")
                f.write('\n')
                print("Question with wrong execution to correct: " + question_with_wrong_execution[0])
                f.write('\"' + question_with_wrong_execution[0] + '\"' + ':' +'\n')
                question_with_wrong_execution = []
                fcode = open("./temp/previous_code.txt", "r")
                linesofcode = fcode.readlines()
                for code in linesofcode:  #write the correct code lines for the previously wrong response
                    code = code.replace('\n','').replace('\\',"")
                    f.write(code + '\n')
                fcode.close()
                f.close()
                r = requests.post(url=gptmanagement_url)
                if r.status_code == 200:
                    print("speech.say(\"Thanks for the correction!\")")
                    lastcorrect = True
            else:
                pass

        if retrieved_okay == 0:
            #print("nao.say(\"I'm sorry, I'll try to correct myself\")")
            lastcorrect = False
            save_previous_code(response)
            question_with_wrong_execution.append(question)
else:
    while(1):
        print("Insert request:  'exit'-> shut down")
        question = input('->  ')
        if question == 'exit':
            break
        r = {'question':question, 'response': None}
        response=requests.get(base_url + '/gino',params={'prompt':json.dumps(r)})
        print('Response code:%d'%response.status_code)
        response = response.content.decode().replace
        print('Gpt Response:\n'+ response)
    


print("End")
