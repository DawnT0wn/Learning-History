# 前言

最近想实现一套CICD的流程，看到了可以通过Jenkins+Gitlab+SonarQube来实现，所以跟着来搭建一下环境，记录一下。大致流程是通过Jenkins拉去GitLab上的项目，通过webhook检测Git提交代码进行自动化构建，用Sonar Scanner进行代码扫描，以及集成Dependency-Check SCA插件，在SonarQube上进行查看扫描结果，通过Jenkins进行消息推送，以及最后用Jenkins的Publish Over SSH插件进行CD流程

# SonarQube环境搭建

JDK版本：JDK17

在官网下载社区版启动，会自动去启动一个elasticsearch数据库

![QQ_1721876804996](images/1.png)

访问127.0.0.1:9000，初始密码admin/admin

安装插件

![QQ_1721876937278](images/2.png)

这里安装Chinese Pack 中文安装包和Findbugs 增加安全扫描的漏洞规则库

还可以安装Community Branch Plugin 管理分支信息

以及Dependency-Check这种SCA进行第三方组件扫描，可以直接再应用市场下，也可以在https://github.com/dependency-check/dependency-check-sonar-plugin/releases/tag/5.0.0下载后放到plugins目录后重启SonarQube

安装findbugs插件后，规则库的Java规则从600多到了1600多个

![QQ_1721877187757](images/3.png)

创建一个本地项目test

![QQ_1721877063125](images/4.png)

这里用maven构建分析，用到的是java-sec-code

```
mvn clean verify sonar:sonar -Dsonar.projectKey=test -Dsonar.projectName='test' -Dsonar.host.url=http://127.0.0.1:9000 -Dsonar.token=sqp_281d4cc79b380dfc37d60d63992ec176778060cb
```

![QQ_1721877232455](images/5.png)

分析完成后在SonarQube后台查看

![QQ_1721878478625](images/6.png)

至于漏洞的准确性，在搭建完成这套流程后再进行考量

# Jenkins环境搭建

直接用War包部署，war包下载地址：http://mirrors.jenkins-ci.org/war/

```
Java -jar jenkins.war --httpPort=8088
```

![QQ_1721889452611](images/7.png)

安装dependency-check https://owasp.org/www-project-dependency-check/

![QQ_1721901453638](images/8.png)

![QQ_1721901629529](images/9.png)

安装企业微信推送插件

![QQ_1721978487271](images/10.png)

也可以安装钉钉的插件

![QQ_1721978525994](images/11.png)

# Gitlab环境搭建

在官网下载ubuntu/focal的deb包，使用dpkg安装，然后修改/etc/gitlab/gitlab.rb

时区改为**Asia/Shanghai** 

![QQ_1721894911170](images/12.png)

external_url改为本机的ipv4

![QQ_1721894972738](images/13.png)

```
#gitlab配置文件修改
sudo vim /etc/gitlab/gitlab.rb
 
#停止gitlab
sudo gitlab-ctl stop ​
 
#重载gitlab配置文件
sudo gitlab-ctl reconfigure ​
 
#重启所有gitlab组件
sudo gitlab-ctl restart ​
 
#启动所有gitlab组件
sudo gitlab-ctl start
 
#查看运行状态
sudo gitlab-ctl status
 
#开机自启
sudo systemctl enable gitlab-runsvdir.service
```

![QQ_1721895331619](images/14.png)

查看root初始密码（密码24小时有效）：

```bash
cat /etc/gitlab/initial_root_password
```

![QQ_1721895455107](images/15.png)

账号root，登录后在perferences中修改为中文

![QQ_1721895596345](images/16.png)

修改root密码

![QQ_1721895677140](images/17.png)

取消注册限制，默认打开

![QQ_1721895877811](images/18.png)

# 环境集成

首先创建一个GitLab的个人用户，不要用管理员账号，管理员账号没有项目权限；需要账号在项目下

先创建一个项目，这里把java-sec-code弄过来了

![QQ_1721900000504](images/19.png)

创建一个个人令牌，这里叫sonarqube

![QQ_1721896528539](images/20.png)

![QQ_1721896676786](images/21.png)

这个令牌以后就看不到了

```
glpat-i5rVzH2cHXDMPcQy319a
```

登录sonar

![QQ_1721897107210](images/22.png)

创建配置，输入访问令牌

![QQ_1721897201309](images/23.png)

在Jenkins>Manage jenkins>Manage Plugins中搜索sonarqube，安装SonarQube Scanner for Jenkins插件；

在Manage jenkins>Global Tool Configuration中配置Sonarquebe Scanner

![QQ_1721898363026](images/24.png)

在sonarqube页面中，点击用户头像，点击我的账号；在新页面中，点击“安全”table，输入令牌名称，点击生成，生成令牌文件；此令牌文件用于Jenkins和sonarqube通信的安全验证，且此令牌内容只显示一次

![QQ_1721898769739](images/25.png)

```
squ_1b0a799e1e4ddf90c33e3c06e1e78cbce8176aaf
```

在Jenkins中配置sonarqube server

Manage jenkins>Configure system，新增sonarqube server服务;

添加的token选择secret text类型的

![QQ_1721899039298](images/26.png)

![QQ_1721899123978](images/27.png)

接下来创建一个freestyle project

![QQ_1721899150340](images/28.png)

配置Git仓库，分支修改一下

![QQ_1721976595784](images/29.png)

构建步骤这里要选三个，按顺序来，首先是maven编译，因为dependency-check需要编译后的Jar包

![QQ_1721976832783](images/30.png)

先执行dependency-check，再执行sonarQube Scanner，因为sonar插件不会进行依赖扫描，需要通过dependency-check扫描完成后，读取配置文件，然后在页面展示的

![QQ_1721977333286](images/31.png)

sonar scanner运行的参数

```
sonar.projectKey=java-sec-code
sonar.projectName=java-sec-code
sonar.projectVersion=1.0-SNAPSHOT
sonar.sourceEncoding=UTF-8
sonar.language=java
sonar.sources=./
sonar.java.binaries=./
sonar.dependencyCheck.htmlReportPath=./dependency-check-report.html
sonar.dependencyCheck.summarize=true
sonar.dependencyCheck.securityHotspot=true
```

点击build now，构建完成后点击SonarQube跳转

![QQ_1721977587124](images/32.png)

此时SonarQube上出现新检查的项目

![QQ_1721977636039](images/33.png)

点击更多查看dependency-check的结果

![QQ_1721977662236](images/34.png)

# 自动化构建

上面就是基本的环境集成，将Gitlab、SonarQube，Jenkins集成在一起，通过Jenkins拉取Gitlab项目代码进行构建，然后使用sonar scanner进行扫描最后将结果推送了SonarQube里面，但是在CICD的流程中，不可能去手动构建，我们需要的是在push代码到Gitlab的时候进行自动化构建，这个就需要webhook

在Jenkins中安装Gitlab插件

![QQ_1721979493614](images/35.png)

接下来在项目的构建触发器中就会有当提交代码或打开/更新合并请求时触发Jenkins中的构建。它还可以将构建状态发送回GitLab

![QQ_1721979521651](images/36.png)

创建GitLab凭证，将凭证填充到 `Manage Jenkins->System->enable authentication for '/project' end-point`

![QQ_1721979757328](images/37.png)

然后回到项目配置中

![QQ_1721980034945](images/38.png)

点击高级，点击generate生成新的token

![QQ_1721980076565](images/39.png)

```
6863719056ffe8ce26edeaa3ed53eb5e
```

后续Gitlab的WebHooks会用，接下来配置Gitlab的webhook

![QQ_1721980301161](images/40.png)

这里127改一下，因为gitlab在Ubuntu上，需要改成Jenkins的webhook地址

接下来点击测试，推送事件

![QQ_1721980747733](images/41.png)

出现200的状态码即为成功

![QQ_1721980734310](images/42.png)

然后目前Jenkins已经在构建项目了

![QQ_1721980785877](images/43.png)

后续推送到钉钉或者企业微信可以参考https://blog.csdn.net/m0_46090675/article/details/120961787

通过爬取SonarQube的接口设置环境变量，将具体的信息推送

```
/api/issues/search?resolved=false&facets=severities%2Ctypes&componentKeys=java-sec-code
```

![QQ_1721981646757](images/44.png)

前面是CI流程，那要通过Jenkins实现CD的话就需要再安装一个插件——Publish Over SSH

![QQ_1721981870414](images/45.png)

接下来就可以去配置SSH服务端然后再项目配置中的构建后操作进行ssh登录部署

![QQ_1721981961437](images/46.png)

具体可参考https://blog.csdn.net/qq_28806349/article/details/120639729



参考链接：

https://github.com/JoyChou93/java-sec-code/tree/master

https://blog.csdn.net/weixin_57025326/article/details/136048507

https://xz.aliyun.com/t/6625

https://blog.csdn.net/m0_46090675/article/details/120961787

https://blog.csdn.net/weixin_45623111/article/details/117918554

https://www.freebuf.com/sectool/382714.html

https://blog.csdn.net/weixin_48190891/article/details/133082137

https://blog.csdn.net/weixin_44825912/article/details/132392326

https://blog.csdn.net/qq_28806349/article/details/120639729