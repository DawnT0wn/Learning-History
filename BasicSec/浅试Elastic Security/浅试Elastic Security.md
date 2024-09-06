# 前言

在上一篇已经成功搭建了一套日志采集平台，现在用之前安装的kibana和elastic搭建一套edr，Elastic 是唯一参加过ATT&CK官方的评估而且可以免费使用的。

# 配置Fleet

kibana和elastic这些已经安装完成了，就直接来配置Fleet了

![QQ_1725592139459](images/1.png)

在左侧菜单栏找到Fleet

![QQ_1725592175979](images/2.png)

添加Fleet服务器，填入名称和Fleet Server的URL，默认为8220端口

![QQ_1725592437405](images/3.png)

快速开始

![QQ_1725592485084](images/4.png)

这里用Ubuntu来安装，和ES是同一台机器，它是从ES服务器上去下载的Agent

![QQ_1725594077634](images/5.png)

在Agent policy中，点击Fleet Server Policy添加集成

![QQ_1725594683555](images/6.png)

这里我添加了Elastic Defend 和Network Packet Capture

![QQ_1725594646540](images/7.png)

在左侧项目栏中选择Security栏目，观察告警发现需要API集成密钥

![QQ_1725594724580](images/8.png)

在kaibana/bin目录下运行kibana-encryption-keys generate

![QQ_1725594809339](images/9.png)

将生成的key保存到kibana.yml重启服务

![QQ_1725594863548](images/10.png)

重启后

![QQ_1725594964211](images/11.png)

规则栏中添加规则

![QQ_1725595026515](images/12.png)

全部安装

![QQ_1725595081332](images/13.png)

安装完成

![QQ_1725595272546](images/14.png)

有一点不好就是里面的规则需要自己去开启

# 检测

MSF生成了一个木马

![QQ_1725602931495](images/15.png)

目录下并没有，发现被拦截了

![QQ_1725602905844](images/16.png)

点击左边的箭头可以查看详情

![QQ_1725603201976](images/17.png)

![QQ_1725603219483](images/18.png)

默认的检测是防御，发现后会直接删除，可以来更改一下检测模式

![QQ_1725603283284](images/19.png)

改为检测，重新生成一个msf木马，检测到了，但是不会删除

![QQ_1725603594689](images/20.png)

![QQ_1725603571295](images/21.png)

至于节点响应的操作，是付费功能

![QQ_1725604457693](images/22.png)





参考链接

https://www.elastic.co/cn/getting-started/security/secure-my-hosts-with-endpoint-security#working-with-elastic-security-for-endpoint

https://blog.csdn.net/csdn12368/article/details/136657190

https://www.secrss.com/articles/29598