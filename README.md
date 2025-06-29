# NaoLLMControl
Repository that contains the essential files regarding the paper "Intuitive Control of a Social Robot Using Natural Language with Large Language Model and Error Correction Capabilities". 
The files cannot be replicated or downloaded for commercial purposes. 
The files have been made available to the viewer for research and informative purposes.

## Description
The repository allows reviewers and users to inspect the main files involved in the project. The repository is structured as follows:
- **GPT_error_correction.py**: the file illustrates the script used to trigger the Error Correction explained in _Sec.6 Error Correction_.
- **GPT_prompt_chat_client.py**: the file illustrates the script used to trigger the framework to control the Nao Robot through voice without the Error Correction involved.
- **main_server.py**: this is the script to activate the Local Server used to mediate between the Nao Robot Controller and the OpenAI Service.
- **server.py**: this script contains the class and methods referenced in the main_server.py script.
- **nao_file_transfer.py**: this file illustrates the class used to transfer audio files between laptop and Nao Robot via FTP.
- **nao_robot_wrapper.py**: this file contains the wrapper class to convert GPT code into NAOqi interpretable code for the Robot Controller.
- **performance_results.ipynb**: the notebook file illustrates the code used to compute the results and graph shown in the _Sec. 7 Performance Evaluation_ chapter of the paper.
- **prompt_manager.py**: this file contains the class to manipulate the Instruction Prompt.
- **PromptTable_eval_with_Score.csv**: this csv file collects the tests of the Performance Evaluation.
- **demo.py**: this file contains a demonstration of the Error Collection pipeline involved in the project, as well as a demo of how ChatGPT tries to satisfy the user's request by issuing commands to the robot.

## Requirements
A virtual environment is recommended.
- Python 3.7+
- OpenAI Account
- OpenAI API Key

## Installation
Clone the repository on a dedicated directory and use the package manager [pip](https://pip.pypa.io/en/stable/) to install the required Python libraries.
```bash
pip install -r requirements.txt
```

## Usage
1) Set up your OpenAI API KEY as an environment variable called "OPENAI_API_KEY"
2) Open a terminal and launch the Local Server running the Python script main_server.py:
   ```bash
    C:/location/on/laptop/python.exe main_server.py
    ```
3) Open another terminal and run the demo.py script:
   ```bash
    C:/location/on/laptop/python.exe demo.py
    ```
4) Write a request on the demo.py terminal as if you were asking to the robot


## Demo Video Example
This video shows an interaction with the chatbot that is able to control the robot. The error correction algorithm gets activated.
The user asks the robot to move closer. After an initial unsatisfactory response, the chatbot gets corrected. In the subsequente interaction, the chatbot no longer commits the same error.

https://github.com/user-attachments/assets/7b7ac515-fc2d-4c97-ad3c-f3a99e3440ba




## NAO Robot Video Example:
This video shows a doctor asking a request to the robot which was not previously mapped on the system. The framework provides actions to satisfy the doctor's request and the robot is correctly able to execute them.

https://github.com/user-attachments/assets/aed689d4-c6fa-4d63-92b9-7d93558749b2

This video shows the simulation of a complete visit with the LLM-enabled control.

https://github.com/user-attachments/assets/3e5845a0-ffa0-4446-b39d-9cf07eb49843



## Note:
Sentences pronounced by the robot and users' requests saved on the .csv file are issued in Italian language as the research project has been pursued in "Policlinico di Modena" Hospital in Italy.


## Task Completion Output Examples
This table provides some interesting examples of the code produced by ChatGPT for the task completion, along with the difficulty score.

| Request | Code | Score |
|---|---|---|
| Show me where the heart is | `nao.setAngle(['RShoulderPitch'], [1.5])\nnao.setAngle(['RElbowRoll'], [-1.0])\nnao.setAngle(['RElbowYaw'], [1.0])\nnao.openHand('RHand')\nnao.closeHand('RHand')` | 5.93 |
| Let's play rock paper scissors, I choose rock | `nao.say("Okay, let's play! I choose rock!")\nnao.setAngle(['RShoulderPitch'], [1.5])\nnao.closeHand('RHand')` | 2.7 |
| Give me your hand and guide me along the corridor | `nao.setAngle(['RShoulderPitch'], [1.8])\nnao.openHand('RHand')\nnao.moveForward(2.0)\nnao.setAngle(['RShoulderPitch'], [1.8])\nnao.closeHand('RHand')\nnao.moveForward(2.0)\nnao.say("Of course, let's start the visit.")` | 3.3 |
| Assist the patient during the cardiologic examination | `nao.setAngle(['RShoulderPitch'], [1.5])\nnao.setAngle(['RElbowRoll'], [-1.0])\nnao.setAngle(['RElbowYaw'], [1.0])\nnao.openHand('RHand')\nnao.say("Here is where the heart is.")\nnao.closeHand('RHand')\nnao.say("Now breathe deeply while we listen to your heart.")\nnao.moveForward(0.5)\nnao.say("Alright, now move a little back.")\nnao.moveForward(-0.5)\nnao.say("The visit is over!")` | 6.42 |
| Give me a High Five! | `nao.setAngle(['RElbowRoll'], [-0.0349])\nnao.setAngle(['RShoulderPitch'], [2.0])\nnao.setAngle(['RElbowRoll'], [0.0])\nnao.setAngle(['RWristYaw'], [1.0])\nnao.openHand('RHand')\nnao.setAngle(['RShoulderPitch'], [1.8])` | 3.2 |
| Scratch your head | `nao.setAngle(['RElbowRoll'], [-1.57])\nnao.setAngle(['RWristYaw'], [1.0])\nnao.openHand('RHand')\nnao.closeHand('RHand')` | 3.9 |







