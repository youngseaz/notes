
# 安装

`apt install rsync -y`

# 启用守护进程

`systemctl enable rsync`

# 配置rsync的配置文件

尝试启用并查看 rsync 的状态，可以看到 rsync 的默认配置文件位于 /etc/rsyncd.conf，如果不存在创建即可
```
root@ubuntu:~# systemctl status rsync
○ rsync.service - fast remote file copy program daemon
     Loaded: loaded (/lib/systemd/system/rsync.service; enabled; vendor preset: enabled)
     Active: inactive (dead)
  Condition: start condition failed at Sun 2024-01-07 15:27:15 UTC; 1s ago
             └─ ConditionPathExists=/etc/rsyncd.conf was not met
       Docs: man:rsync(1)
             man:rsyncd.conf(5)

Jan 07 15:27:15 ubuntu systemd[1]: Condition check resulted in fast remote file copy program daemon being skipped.
```

具体 rsync 配置文件如下：

```conf

```

