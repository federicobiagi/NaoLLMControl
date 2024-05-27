import paramiko
from ftplib import FTP


NAO_IP = "gino.local"
NAO_USERNAME = "nao"
NAO_PASSWORD = "NAO"

class NAOFileTransfer():

    def __init__(self, nao_ip, nao_username, nao_password):
        self.ip = nao_ip
        self.username = nao_username
        self.password = nao_password

    def transfer(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.ip, username=self.username, password=self.password)
        sftp = ssh.open_sftp()
        #localpath = './First Component/audio/voice.wav'
        localpath = "./sounds/voice.wav"
        remotepath = '/data/home/nao/voice1.wav'
        sftp.get(remotepath, localpath)
        sftp.close()
        ssh.close()

    
    def getfilelist(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.ip, username=self.username, password=self.password)
        sftp = ssh.open_sftp()
        #localpath = './First Component/audio/voice.wav'
        filelist = sftp.listdir('/data/home/nao/')
        sftp.close()
        ssh.close()
        return filelist

