

# 挂载本地磁盘

临时挂载 `mount -t ntfs /dev/sda1 /mnt/data1`

开机自动挂载，修改/etc/fstab

> 如下操作环境为 Ubuntu Server 22.04

```
root@ubuntu:~# cat /etc/fstab
# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#


# <file system> <mount point>   <type>  <options>       <dump>  <pass>

# mount my disk

/dev/disk/by-uuid/28FC2CD7FC2CA0D4 /nas/hdd01/disk01 ntfs defaults,uid=0,gid=0,dmask=022,fmask=177 0 2
/dev/disk/by-uuid/F8F007CDF0079154 /nas/hdd01/disk02 ntfs defaults,uid=0,gid=0,dmask=022,fmask=177 0 2
/dev/disk/by-uuid/AC6CBFC36CBF869C /nas/hdd01/disk03 ntfs defaults,uid=0,gid=0,dmask=022,fmask=177 0 2
/dev/disk/by-uuid/0EB8D024B8D00BD9 /nas/hdd01/disk04 ntfs defaults,uid=0,gid=0,dmask=022,fmask=177 0 2
```

获取分区UUID
```
root@ubuntu:~# blkid
/dev/sda4: LABEL="datas04" BLOCK_SIZE="512" UUID="0EB8D024B8D00BD9" TYPE="ntfs" PARTLABEL="Basic data partition" PARTUUID="b0e460f9-6707-4225-95a8-99fbf4fb8454"
/dev/sda2: LABEL="datas02" BLOCK_SIZE="512" UUID="F8F007CDF0079154" TYPE="ntfs" PARTLABEL="Basic data partition" PARTUUID="17a76c62-aed7-4458-a1b8-d04373f15f2b"
/dev/sda3: LABEL="datas03" BLOCK_SIZE="512" UUID="AC6CBFC36CBF869C" TYPE="ntfs" PARTLABEL="Basic data partition" PARTUUID="7d648237-8f78-49ce-9fc8-90e79d3104e1"
/dev/sda1: LABEL="datas01" BLOCK_SIZE="512" UUID="28FC2CD7FC2CA0D4" TYPE="ntfs" PARTLABEL="Basic data partition" PARTUUID="b0b5742c-3752-467f-9586-c6ced99ef395"

```

关于 fstab 的描述，linux 执行 man fstab 查看






# 挂载网络磁盘

挂载 cifs 