import subprocess
import time

p = subprocess.Popen(['/home/metin/env/3108/bin/python', '/home/metin/codes/LinkedIn-Easy-Apply-Bot/easyapplybot.py'])
time.sleep(20)
p.terminate()