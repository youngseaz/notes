import re

import socket


from time import sleep

HOST = "puffer.utctf.live"
PORT = 8625


def validate(pan):
    if len()
    return isValidLuhn(pan)


def isValidLuhn(number):
    result = []
    count = 0
    arr = list(number)
    arr.reverse()
    for i in arr:
        if count == 0 or count % 2 == 0:
            result.append(int(i))
        else:
            a = int(i) * 2
            n = a % 10
            m = a // 10
            result.append(n + m)
        count += 1
    s = sum(result)
    return s % 10 == 0        



def parse(data):
    pattern = re.compile(r"PAN: (\d*), date: (\d*), code: (\d*), cvv: (\d*)", re.DOTALL)
    res = re.search(pattern, data)
    try:
        return res.groups()
    except:
        return None

def main():
    result = []
    s = socket.socket()
    s.connect((HOST, PORT))
    while True:
        while True:
            data = s.recv(2048).decode()
            if "Valid?" in data:
                print(data)
                break
        data = parse(data)
        if data:
            if validate(data[0], data[1], data[2], data[3]):
                s.send("1\n".encode())
                result.append("1")
                print("1")
            else:
                s.send("0\n".encode())
                result.append("0")
                print("0")
        sleep(1)
    print("".join(result))
    

def test():
    #print(parse("PAN: 999554623155882931, date: 0873, code: 473, cvv: 900"))
    print(parse("'Damn another invalid card...\nPAN: 184260195432722838, date: 0761, code: 563, cvv: 132\nValid? \n'"))


if __name__ == "__main__":
    # main()
    #print(isValidLuhn("4556737586899855"))
    #print(isValidLuhn("4024007109022143"))
    #print(isValidLuhn("6225767571664101"))
    print(isValidLuhn('303862057218516248'))
    #test()

