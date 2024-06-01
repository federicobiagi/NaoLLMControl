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
![Video Example](https://github.com/federicobiagi/NaoLLMControl/blob/main/demo_example.gif)
![Video Example2](https://github.com/federicobiagi/NaoLLMControl/blob/main/demo_example_2.gif)

## Video Demonstration

## Note:
Sentences pronounced by the robot and users' requests saved on the .csv file are issued in Italian language as the research project has been pursued in "Policlinico di Modena" Hospital in Italy.







