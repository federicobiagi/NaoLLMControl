import torch
import time
from transformers import pipeline
from openai import OpenAI
import os
def transcribe(audio,pipe):
    """
    Transcribe the audio to text

    :param audio: audio file path
    """
    #device = 0 if torch.cuda.is_available() else -1
    #pipe = pipeline("automatic-speech-recognition", model="fredbi/whisper-small-italian-tuned", device=device)
    text = pipe(audio)["text"]
    return text


if __name__ == "__main__":
    path = 'RECORDED_REQUEST_FOR_GPT.wav'
    key= os.getenv("OPENAI_Personal_Key")
    #client = OpenAI(api_key=key)
    #print("Comparison time between whisper online transcription via API and custom finetuned whisper model")
    device = 0 if torch.cuda.is_available() else -1
    pipe = pipeline("automatic-speech-recognition", model="fredbi/whisper-small-italian-tuned", device=device)
    result = pipe(path)
    print(result)
    start_time = time.time()
    audio_file= open(path, "rb")
    #richiesta = client.audio.transcriptions.create(model = "whisper-1", file = audio_file, language="it")
    #print(richiesta)
    end_time = time.time()
    #print("Time taken for online whisper transcription: ", end_time - start_time)

    start_time = time.time()
    richiesta = transcribe(path,pipe)
    print(richiesta)
    end_time = time.time()
    print("Time taken for custom whisper model transcription: ", end_time - start_time)