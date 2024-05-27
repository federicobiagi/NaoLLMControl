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
    #code_block_regex = re.compile(r"```(.*?)```",re.DOTALL)  #take the python code part in the ChatGPT response
    #code_blocks = code_block_regex.findall(content) 
    code_blocks = content
    if code_blocks:
        #full_code = "\n".join(code_blocks) #aggregate the sentences and separate them with '\n'
        #full_code = full_code[8:]  #take the code piece from the 'python' word, till the end of the response 
        code_blocks = code_blocks.replace("\\n", "\n")
        code_blocks = code_blocks.replace("\"","")
        open('./temp/code.txt','w').write(code_blocks)
   
        return code_blocks.rstrip()
    else:
        return None

lastcorrect = True
question_with_wrong_execution = []
r = requests.post(base_url+'/gino')
print('Response code:%d'%r.status_code)

print("Do you want to activate the Error Correction algorithm? (y/n)")
error_corr_mode = input("-> ")

if error_corr_mode == 'y':
    while(1):
        print("Insert request:  'exit'-> shut down")
        question = input('->  ')
        if question == 'exit':
            break
        r = {'question':question, 'response': None}
        response=requests.get(base_url+'/gino',params={'prompt':json.dumps(r)})
        answer = response.content.decode()
        print('Gpt Response:\n'+ answer)
        print('Response code:%d'%response.status_code)  
        codeblocks = extract_python_code(answer)

        print("nao.say(\"Did I do well?\")")
        correct = input("Answer 'yes' or 'no' -> ")

        if correct == 'yes' or correct == 'Yes':
            if lastcorrect == False:
                print("nao.say(\"All right!\")")
                f = open('./system_prompts/initial_setup.txt',"a")
                f.write('\n\n')
                print("Question with wrong execution to correct: " + question_with_wrong_execution[0])
                f.write('\"' + question_with_wrong_execution[0] + '\"' + ':' +'\n')
                question_with_wrong_execution = []
                fcode = open("./temp/code.txt", "r")
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
                print("nao.say(\"All right! Very well\")")

        if correct == 'no' or correct == 'No':
            print("nao.say(\"I'm sorry, could you please correct me?\")")
            lastcorrect = False
            question_with_wrong_execution.append(question)
else:
    while(1):
        print("Insert request:  'exit'-> shut down")
        question = input('->  ')
        if question == 'exit':
            break
        r = {'question':question, 'response': None}
        response=requests.get(base_url+'/gino',params={'prompt':json.dumps(r)})
        answer = response.content.decode()
        print('Gpt Response:\n'+ answer)
        print('Response code:%d'%response.status_code)
    


print("End")