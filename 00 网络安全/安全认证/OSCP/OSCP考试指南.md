
# 考试规则

官方考试指南 [OSCP Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

主要关键信息：
- 不可以使用商用安全工具，如 
- msfvenom 使用次数不受限制，可以使用任意次生成 payload
- msfconsole 只能对单个靶机环境使用，考试只能指定其中一个靶机环境，不能用于包含多台靶机的环境


# 考试常用命令

## web目录爆破

dirsearch 工具
- -t 指定线程数量
- -w 指定目录字典，
- -u 指定url

`dirsearch -u  http://192.168.56.105 -t 16 -w /usr/share/dirb/wordlists/big.txt`

常用的字典集合：
- /usr/share/dirb/wordlists/big.txt

## wordpress网站专用扫描工具

wpscan

