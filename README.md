# NaoLLMControl
Repository that contains the essential files regarding the paper "Intuitive Control of Social Robots using Natural Language with ChatGPT". 
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

## Demo Example:
In the following video, a demo of the Error Correction algorithm is shown. In the first 2 minutes of the video the robot gets corrected as he is not capable of satisfying the user when playing "Rock Paper Scissor" game. After the correction, the server and demo are interrupted. Upon reboot, virtually, the LLM is able to play "Rock Paper Scissor" with no further correction by the user. This means that the robot has learned a new task that he can reproduce.

https://github.com/user-attachments/assets/3f5d3704-3057-4798-ad5c-a874f62c7057

## Video Example:
The first video shows a doctor asking a request to the robot which was not previously mapped on the system. The framework provides actions to satisfy the doctor's request and the robot is correctly able to execute them.

https://github.com/user-attachments/assets/aed689d4-c6fa-4d63-92b9-7d93558749b2

The second video shows the doctor correcting the robot's mistake.
https://github.com/user-attachments/assets/a9175313-85df-4866-97d4-13691b234095







## Note:
Sentences pronounced by the robot and users' requests saved on the .csv file are issued in Italian language as the research project has been pursued in "Policlinico di Modena" Hospital in Italy.







