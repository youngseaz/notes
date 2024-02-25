# 应用场景

PC1 和 PC2 通过 190.X.X.X 建立 VPN 隧道，PC 想要访问位于内网的 server，可以在 server gateway 部署OpenVPN 服务端，在 PC 部署 OpenVPN 客户端，实现内网访问。

![](<images/01 配置OpenVPN访问内网/image-5.png>)

# OpenVPN下载与安装
OpenVPN官网下载 [OpenVPN GUI Community Downloads](https://openvpn.net/community-downloads/)

OpenVPN安装，安装的时候**选择自定义安装，勾选上 EasyRSA 工具**，用于生成证书。OpenVPN使用PKI (Public Key Infrastructure) 让服务端与客户端相互验证。需要生成一系列文件置于服务端或客户端，我们需要用 Easy-RSA 生成这些文件。

![](<images/01 配置OpenVPN访问内网/image.png>)

# 配置

## 证书生成

Windows 10 下使用 Easy-RSA 生成证书，在 OpenVPN 安装目录下 easy-rsa 目录**以管理员身份启动 EasyRSA-Start.bat** 进入 shell.

![](<images/01 配置OpenVPN访问内网/image-1.png>)

执行如下步骤的命令生成证书

1. 创建 PKI 和 CA 证书
- 创建PKI `easyrsa init-pki`
- 创建无密码的 CA `easyrsa build-ca nopass`

创建 CA 遇到如下提示直接按回车 Common Name (eg: your user, host, or server name) [Easy-RSA CA]: 回车

```
EasyRSA Shell
# easyrsa init-pki

Notice
------
'init-pki' complete; you may now create a CA or requests.

Your newly created PKI dir is:
* C:/Program Files/OpenVPN/easy-rsa/pki

Using Easy-RSA configuration:
* undefined

EasyRSA Shell
# easyrsa build-ca nopass
No Easy-RSA 'vars' configuration file exists!

Using SSL:
* openssl OpenSSL 3.2.0 23 Nov 2023 (Library: OpenSSL 3.2.0 23 Nov 2023)
..............+.........+....+..+...+++++++++++++++++++++++++++++++++++++++*....+.+..+....+++++++++++++++++++++++++++++++++++++++*...+......+...+..........+.....+......+....+.....+...+..........+...+..............+..........+..+......+..........+........+....+........+.......+......+......+........+...+....+...+............+........+...+..........+........+....+..++++++
.......+.+...........+..........+...+..+.+..+.......+...+...+...............+...+..+....+...+......+.........+........+...+.+.....+.+........+.........+.+...........+++++++++++++++++++++++++++++++++++++++*......+.+...+++++++++++++++++++++++++++++++++++++++*.+.+...+..+......+....+......+...+............+...+......+........+.+........................+..+....+......+.....+....+......+...+.................+.+.....+.......+.....+...+.......+..+..........+...+...............+.....................+.....+...............+.......+............+...+..+.+.........+..+...+.+..+...+.+.........+.....+.+...............+...........+.........+......+...+....+..+....+.....++++++
-----
You are about to be asked to enter information that will be incorporated
into your certificate request.
What you are about to enter is what is called a Distinguished Name or a DN.
There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter '.', the field will be left blank.
-----
Common Name (eg: your user, host, or server name) [Easy-RSA CA]: [回车]

Notice
------
CA creation complete. Your new CA certificate is at:
* C:/Program Files/OpenVPN/easy-rsa/pki/ca.crt


```

2. 创建服务端证书

- 创建服务端证书请求，名为 vpnserver.req `easyrsa gen-req vpnserver nopass`
- 签发服务端证书，`easyrsa sign server vpnserver`
- 生成 DH 文件，`easyrsa gen-dh`


```
EasyRSA Shell
# easyrsa gen-req vpnserver nopass
No Easy-RSA 'vars' configuration file exists!

Using SSL:
* openssl OpenSSL 3.2.0 23 Nov 2023 (Library: OpenSSL 3.2.0 23 Nov 2023)
...+...+........+...+.+.........+...........+...+.+..+....+...+++++++++++++++++++++++++++++++++++++++*.+...+........+++++++++++++++++++++++++++++++++++++++*..+....+..+....+...+.....................+..+...+......+.+..+...+.......+........+...+....+...........+.......+..+......+.......+........+......+.+..+...+.......+...+.....+.............+..+....+...+.....+.+..+.......+...+..+...+...+.+...+...........+.+......+........+......+......+....+...+.....................+.........+..+....+.....+.+......+..+.+...........+..........+...............+...........+...............+......................+......+..+...+....+......+.....+....+..+.++++++
....+...+..+++++++++++++++++++++++++++++++++++++++*......+..+.............+++++++++++++++++++++++++++++++++++++++*....+....+..+.........+......+...+............+.+...............+.....++++++
-----
You are about to be asked to enter information that will be incorporated
into your certificate request.
What you are about to enter is what is called a Distinguished Name or a DN.
There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter '.', the field will be left blank.
-----
Common Name (eg: your user, host, or server name) [vpnserver]:

Notice
------
Private-Key and Public-Certificate-Request files created.
Your files are:
* req: C:/Program Files/OpenVPN/easy-rsa/pki/reqs/vpnserver.req
* key: C:/Program Files/OpenVPN/easy-rsa/pki/private/vpnserver.key


EasyRSA Shell
# easyrsa sign server vpnserver
No Easy-RSA 'vars' configuration file exists!

Using SSL:
* openssl OpenSSL 3.2.0 23 Nov 2023 (Library: OpenSSL 3.2.0 23 Nov 2023)
You are about to sign the following certificate:
Please check over the details shown below for accuracy. Note that this request
has not been cryptographically verified. Please be sure it came from a trusted
source or that you have verified the request checksum with the sender.
Request subject, to be signed as a server certificate
for '825' days:

subject=
    commonName                = vpnserver

Type the word 'yes' to continue, or any other input to abort.
  Confirm request details: yes

Using configuration from C:/Program Files/OpenVPN/easy-rsa/pki/openssl-easyrsa.cnf
Check that the request matches the signature
Signature ok
The Subject's Distinguished Name is as follows
commonName            :ASN.1 12:'vpnserver'
Certificate is to be certified until May 29 16:34:30 2026 GMT (825 days)

Write out database with 1 new entries
Database updated

Notice
------
Certificate created at:
* C:/Program Files/OpenVPN/easy-rsa/pki/issued/vpnserver.crt

EasyRSA Shell
# easyrsa gen-dh
No Easy-RSA 'vars' configuration file exists!

Using SSL:
* openssl OpenSSL 3.2.0 23 Nov 2023 (Library: OpenSSL 3.2.0 23 Nov 2023)
Generating DH parameters, 2048 bit long safe prime
+...........................................................+......................+......................................................+............................+.............++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*++*
DH parameters appear to be ok.

Notice
------

DH parameters of size 2048 created at:
* C:/Program Files/OpenVPN/easy-rsa/pki/dh.pem


```

3. 创建客户端证书

- 创建客户证书请求，名为 vpnclient.req，`easyrsa gen-req vpnclient nopass`
- 签发客户端证书，`easyrsa sign client vpnclient`

```
EasyRSA Shell
# easyrsa gen-req vpnclient nopass
No Easy-RSA 'vars' configuration file exists!

Using SSL:
* openssl OpenSSL 3.2.0 23 Nov 2023 (Library: OpenSSL 3.2.0 23 Nov 2023)
..+..+.+.........+........+.+..+....+........+...+....+...+..+++++++++++++++++++++++++++++++++++++++*.+..+...+......+.+..............+.+........+...........................+.+..+...+..........+++++++++++++++++++++++++++++++++++++++*.......+......+..........+.....+.+........+...............+..........+.....+...+....+...+........+.......+...+...+..+....+...........+...+....+.....+.+......+.....+.+...+............+...............+..+..........+...+........+......+...+...+...............+....+....................+................+...+..+.......+..+...+......+............+...+....+......+.........+..+....+......+...+...+.....+...+....+...+........+.+......+..+..................+....+...+......+.....+............+....+..............+.+...+...+..+...+....+........+......+.......+.............................+......+...+......+.............+...........+.......+...+..+....+.....+.+...+...........+...+......+.+...+..+.+.........+......+........+.......+..+..........+........+....+...+............+.....+....+.....+......+.........+.+...........+...+.......+.....+..........+.....+............++++++
..+...+............+.....+++++++++++++++++++++++++++++++++++++++*....+...+++++++++++++++++++++++++++++++++++++++*.........+.+...+......+..+...+....+..+.............+.....+...+...+.+......+..+......+....+..+.+........+.........+..........+...+........+.+.....+....+..+..........+.......................+.+...+......+......+...+..+....+.....+.+.....+.+..+...+.......+...+.........+...+........+.......+...+.........+.........+.....+.........+......++++++
-----
You are about to be asked to enter information that will be incorporated
into your certificate request.
What you are about to enter is what is called a Distinguished Name or a DN.
There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter '.', the field will be left blank.
-----
Common Name (eg: your user, host, or server name) [vpnclient]:

Notice
------
Private-Key and Public-Certificate-Request files created.
Your files are:
* req: C:/Program Files/OpenVPN/easy-rsa/pki/reqs/vpnclient.req
* key: C:/Program Files/OpenVPN/easy-rsa/pki/private/vpnclient.key


EasyRSA Shell
# easyrsa sign client vpnclient
No Easy-RSA 'vars' configuration file exists!

Using SSL:
* openssl OpenSSL 3.2.0 23 Nov 2023 (Library: OpenSSL 3.2.0 23 Nov 2023)
You are about to sign the following certificate:
Please check over the details shown below for accuracy. Note that this request
has not been cryptographically verified. Please be sure it came from a trusted
source or that you have verified the request checksum with the sender.
Request subject, to be signed as a client certificate
for '825' days:

subject=
    commonName                = vpnclient

Type the word 'yes' to continue, or any other input to abort.
  Confirm request details: yes

Using configuration from C:/Program Files/OpenVPN/easy-rsa/pki/openssl-easyrsa.cnf
Check that the request matches the signature
Signature ok
The Subject's Distinguished Name is as follows
commonName            :ASN.1 12:'vpnclient'
Certificate is to be certified until May 29 16:43:49 2026 GMT (825 days)

Write out database with 1 new entries
Database updated

Notice
------
Certificate created at:
* C:/Program Files/OpenVPN/easy-rsa/pki/issued/vpnclient.crt


```


## 服务端配置

将证书生成步骤中的vpnserver.crt、vpnserver.key，ca.crt，dh.pem 放到和配置文件server.ovpn 放到同一个目录，且 server.ovpn 的配置如下

>模板文件位于 OpenVPN 安装目录下的 sample-config 文件夹，修改后的配置如下，已经把注释删除


```
# server.ovpn

local 0.0.0.0
port 1194
proto udp
dev tun
ca ca.crt
cert vpnserver.crt
key vpnserver.key  # This file should be kept secret
dh dh.pem
topology subnet
server 192.168.100.0 255.255.255.0
ifconfig-pool-persist ipp.txt
push "route 192.168.154.0 255.255.255.0"
keepalive 10 120
cipher AES-256-GCM
persist-key
persist-tun
status openvpn-status.log
verb 3
explicit-exit-notify 1


```

## 客户端配置

将证书生成步骤中的vpnclient.crt、vpnclient.key，ca.crt 放到和配置文件 client.ovpn 放到同一个目录，且 client.ovpn 的配置如下

```
# client.ovpn

client
dev tun
proto udp
remote 192.168.154.1 1194
resolv-retry infinite
nobind
persist-key
persist-tun
ca ca.crt
cert vpnclient.crt
key vpnclient.key
remote-cert-tls server
cipher AES-256-GCM
verb 3


```

## 配置路由转发

Windows 修改注册表项，允许网卡直接 IP 路由转发，**服务端和客户端都要修改**
> HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters 的 IPEnableRouter 改为 1

![](<images/01 配置OpenVPN访问内网/image-3.png>)

配置完成之后重启，可以在 cmd 看到已经启用 IP 路由功能

![alt text](<images/01 配置OpenVPN访问内网/image-4.png>)

# 参考

1. [基于EASY-RSA-3.0搭建VPN服务之OPENVPN](https://www.xionghaier.cn/archives/367.html)
2. [OpenVPN Server端配置文件详细说明](https://blog.51cto.com/u_14892047/5201768)
