# openrasp安装

项目地址

 https://github.com/baidu-security/openrasp-v8（v8引擎的cpp代码）

 https://github.com/baidu/openrasp

先安装数据库

![image-20231004115430113](images/1.png)

```
docker pull mongo:latest
docker run -itd --name mongo -p 27017:27017 mongo
```

![image-20231004115924935](images/2.png)

ElasticSearch没7.0以下没有arm的docker，所以直接去官网下载，然后启动bin目录下的elasticsearch的文件，访问9200

![image-20231004115829949](images/3.png)

即为安装成功

下载rasp-cloud，conf目录下的app.conf下修改配置文件

![image-20231004120223742](images/4.png)

默认端口上9200和27017，如果是正确的就下一步

输入命令 `./rasp-cloud -d` 来启动后台服务器，访问8086端口

![image-20231004120338621](images/5.png)

其中用户名固定为 **openrasp**，初始密码为 **admin@123**。如果不能访问，请检查防火墙设置，或者检查 `logs/api/agent-cloud.log` 下面的错误信息。

![image-20231004121251574](images/6.png)

添加主机，右上方添加主机有对应的命令，也可参考官方文档https://rasp.baidu.com/doc/install/manual/tomcat.html

![image-20231005083932892](images/7.png)

![image-20231005083950567](images/8.png)

用openrasp提供的官方环境来试用

![image-20231005084854794](images/9.png)

![image-20231005084901235](images/10.png)



![image-20231005085403126](images/11.png)

开始没有拦截，只是记录日志，将快速设置关掉会成功防护

![image-20231005085433496](images/12.png)

![image-20231005085351016](images/13.png)

另外用洞态IAST也检出了漏洞（可以要稍微等一会才有）

![image-20231005093822502](images/14.png)

openrasp效果

![image-20231005093839876](images/15.png)

Springboot安装

```
java -jar RaspInstall.jar -heartbeat 90 -appid d749f6c7384a793ba72ca2155f77ec3206ce48d5 -appsecret 9nBmc4D2gojBZh0M067zqx1LiY2ud4eTmfOkvD94tk0 -backendurl http://127.0.0.1:8086/ -install <spring_boot_folder>
```

这里的 `<spring_boot_folder>` 通常是 XXX.jar 包所在的目录。

这个主要是用来修改`openrasp.yml` 配置文件内容，如果运行不成功，可以直接将刚才tomcat生成的整个rasp目录拖过去，直接用，只要添加启动参数`-javaagent:/Users/DawnT0wn/IdeaProjects/Iast_Test_demo/rasp/rasp.jar`即可

![image-20231006161120315](images/16.png)

这样我用源码调试分析更方便

![image-20231006162031847](images/17.png)

# OpenRasp原理分析

## 启动流程分析

### 初始化

来把rasp安装过程中的Jar包添加到依赖分析

![image-20231005094250209](images/18.png)

从MANIFEST.MF中可以看到Premain-Class等定义

![image-20231005094946806](images/19.png)

首先是通过init初始化，调用addJarToBootStrap，顾名思义，就是将jar包添加到启动类加载器

![image-20231005095036611](images/20.png)

就是把当前jar包也就是`rasp.jar`加载至Bootstrap类加载器，因为这样通过双亲委派机制，运行过程中就可以加载到rasp.jar中的所有类了，可能自己写的一些rasp在运行的时候会出现找不到类的情况，其实可以通过这样去解决。

之前在看一些IAST的文章的时候也看到过关于agent的隔离加载

> 因为我们现在需要实现具有一定复杂逻辑的agent，所以我们不可避免的需要引入一些其他jar包做功能实现，而如果我们的agent与正常应用引入了同一个jar包的不同版本，这将发生jar包冲突，对正常应用产生未知影响。
>
> 要解决这个问题，我们需要自定义类加载器来加载agent中的类，因为在java中通过不同的类加载器加载同一个类是不一样的，一个类只能引用同一类加载器加载的类及其父加载器加载的类，更多的细节大家也可以去详细了解一下Java的类加载机制，java的很多框架如spring都有实现自己的类加载器实现隔离加载来解决冲突的问题。
>
> 所以我们现在需要将这个agent分为两个jar包，一个是agent包，另一个core包。agent包实现一个premain()方法、Tranformer类等，并且使用自定义类加载器加载core包，而core包是我们编写的修改字节码的逻辑。但这样还会有一个问题，我们修改后的正常代码，需要调用core包中的方法，而core包是自定义类加载器加载的，正好代码的类一般是应用类加载器加载的，所以正常代码这时候无法调用core中的方法。所以，还需要将正常代码调用的方法单独拆分出一个jar包，该包使用BootstrapClassLoader加载，该类加载器是类加载器的顶层，其加载的类可以被所有的类加载器加载的类引用，我们将这个jar命名为spy。

接下来的readVersion就是读取一些版本信息相关的内容，我们来看ModuleLoader.load

在执行ModuleLoader的load这个静态方法前，会先执行静态代码块

![image-20231006131434839](images/21.png)

```
for(systemClassLoader = ClassLoader.getSystemClassLoader(); systemClassLoader.getParent() != null && !systemClassLoader.getClass().getName().equals("sun.misc.Launcher$ExtClassLoader"); systemClassLoader = systemClassLoader.getParent()) {
}
```

这里其实就是将moduleClassLoader设置为ExtClassLoader，接下来才是load方法

![image-20231006131159542](images/22.png)

load方法中回去实例化ModuleLoader，并携带上当前的mode和Instrumentation

![image-20231006131336078](images/23.png)

当模式为normal的时候会执行`setStartupOptionForJboss();`这里按照源码的解释应该是判断当前进程是否为jboss7 版本（通过classpath里面的jar包结尾进行判断的），并设置相关属性和预加载包

![image-20231006131626133](images/24.png)

接下来就是实例话ModuleContainer对象，传入的是rasp-engine.jar，调用start方法

![image-20231006131958325](images/25.png)

一共做了如下工作

1. 输出banner信息
2. Loader.load()：V8引擎的加载，用于解释执行JavaScript
3. loadConfig()：初始化配置
   - LogConfig.ConfigFileAppender()：初始化log4j
   - CloudUtils.checkCloudControlEnter()：检查云控配置信息
   - LogConfig.syslogManager()：读取配置信息，初始化syslog服务连接
4. Agent.readVersion();BuildRASPModel.initRaspInfo():缓存rasp的build信息
5. JS.Initialize()：初始化插件系统
   - 为V8配置java的logger以及栈堆信息Getter（用于在js中获取当前栈堆信息）
   - UpdatePlugin()：读取plugins目录下的js文件，过滤掉大于10MB的js文件，然后全部读入，最后加载到V8引擎中
   - 这里有一个commonLRUCache，主要是用于在hook点去执行js check的时候，进行一个并发幂等
   - InitFileWatcher()：初始化一个js plugin监视器（（JnotifyWatcher实现文件监控），在js文件有所变动的时候，重新去加载所有插件，**实现热更新的特性**。
6. CheckerManager.init()：初始化所有的checker，从枚举类com.baidu.openrasp.plugin.checker.CheckParameter.Type中读取所有的checker，包含三种类型的checker，一是js插件检测，意味着这个checker会调用js plugin进行攻击检测，二是java本地检测，意味着是调用本地java代码进行攻击检测，三是安全基线检测，是用于检测一些高风险类的安全性基线检测，检测其配置是否有安全隐患。
   下面要讲到的`doCheck()`方法中的type参数就是这里的Type。

### 引擎启动

首先是Loader.load方法

![image-20231006154539160](images/26.png)

这个方法主要用来加载v8引擎，用来解释执行JavaScript

![image-20231006154556525](images/27.png)

接下来将就执行到了loadConfig方法

![image-20231006162358764](images/28.png)

因为这里不是云控的，所以就直接打印RaspId返会true了，首先是初始化log4j，如果不是云控的话

- CloudUtils.checkCloudControlEnter()：检查云控配置信息
- LogConfig.syslogManager()：读取配置信息，初始化syslog服务连接

![image-20231006164257634](images/29.png)

接下来会缓存rasp的build信息，然后调用`JS.Initialize()`进行JS初始化

![image-20231006164331153](images/30.png)

首先是设置V8的log和堆栈信息，如果不是有管理后台的话还会进入UpdatePlugin和InitFileWatcher方法

![image-20231006165027563](images/31.png)

会遍历rasp/plugins目录下的js文件，过滤掉大于10MB的js文件，然后全部读入scripts变量，最后加载到V8引擎中，然后将scripts传入UpdatePlugin方法

![image-20231006165254436](images/32.png)

V8对应方法的代码

![image-20231006170052802](images/33.png)



具体怎么实现的也没有怎么去了解了，需要了解可以去看看Y4的文章[OpenRasp分析 | Y4tacker's Blog](https://y4tacker.github.io/2022/05/28/year/2022/5/OpenRasp分析/#JS初始化)

反正主要是用来更新插件的

接下来就是InitFileWatcher这个方法

![image-20231006170328559](images/34.png)

看起来像是一系列监听的功能，当有新的插件创建，修改，删除等改变的时候，重新调用UpdatePlugin加载插件，实现热加载

然后会到start方法，就是`CheckerManager.init()`

![image-20231006172002198](images/35.png)

从枚举类com.baidu.openrasp.plugin.checker.CheckParameter.Type中读取所有的checker

![image-20231006172145990](images/36.png)

将这个枚举类的checker以及对应的检测函数添加到checkers这个EnumMap，大多数是V8AttackChecker#checkParam

![image-20231015105154509](images/37.png)

![image-20231015105124943](images/38.png)

根据类型去执行一些额外操作，可以看到写文件就需要找到参数（`Config.commonLRUCache.isContainsKey(hashData)`），最后是通过V8.Check来执行的，猜测这里应该就是和JS插件联动的地方了，最后得到的结果如果不为null说明是攻击就进行log，这里的 commonLRUCache用于缓存已经执行过的，这样可以节约内存资源

![image-20231015105443500](images/39.png)

## 执行流程分析

![image-20231006172727920](images/40.png)

接下来调用initTransformer

![image-20231006172753074](images/41.png)

调用CustomClassTransformer的retransform方法，在CustomClassTransformer这个类中可以看到他实现了ClassFileTransformer接口，并且重写了transform方法，当类加载的时候，会进入我们自己的 `Transformer` 中，执行 `transform`函数进行拦截

![image-20231006173402247](images/42.png)

在平常，我们自己实现的一些agent，可能就是重写了一个transform方法，通过ASM去修改类，抛出异常这样来进行一个hook，但是openrasp的transform方法在执行之前，就已经添加了hook类，接着过程的流程继续分析

在实例化CustomClassTransformer的时候，addTransformer这个是agent中常见的代码，不过还会调用addAnnotationHook方法

![image-20231006173630462](images/43.png)

跟进addAnnotationHook

![image-20231006173853423](images/44.png)

这里逻辑也比较简单，获取到所有被HookAnnotation注解的类，通过反射进行实例化，当其实现了AbstractClassHook时，调用addHook方法，将实例和类名传递进去

![image-20231006175539448](images/45.png)

这里把非ignore的类添加到hooks这个HashSet里面，这个hooks用来提供在后续类加载通过`com.baidu.openrasp.transformer.CustomClassTransformer#transform`的时候，对其进行匹配，判断是否需要hook，将hook的getType添加到necessaryHookType这个ConcurrentSkipListSet里面，这些被HookAnnotation注解的类均来自`open.baidu.openrasp.hook`文件夹下的类

![image-20231006180152787](images/46.png)

接下来调用retransform方法

![image-20231006175932523](images/47.png)

其实这里就只是对一些已经加载了的类重新加载，因为一些hook的类可能是已经加载到JVM里面的类了，在重新加载的时候会毁掉transform方法，接下来就是transform方法

![image-20231006181037817](images/48.png)

通过遍历hooks来看className是否和需要hook的类，但是个人觉得没有必要这样去遍历hooks，不知道把hooks变成hashMap通过键值对去寻找会不会更方便，不然每一个加载的类就要去遍历100多次来寻找，但是不知道hashMap的containsKey这种方法寻找的时候是不是也是这个逻辑了，回归正题，当类是需要hook的类的时候，真正的hook开始了

具体实现没有通过ASM，而是通过Javassist去实现字节码的修改，首先是通过transfrom接受的类文件的字节数组classfileBuffer来创建了一个ctClass，调用hook类的transformClass传入这个ctClass

![image-20231006181556399](images/49.png)

然后调用其hookMethod方法，最后通过toBytecode转换为类文件

![image-20231006181652219](images/50.png)

这里以DNSHook为例，当类名为java/net/InetAddress时，会调用到DNSHook到hookMethod，这个方法主要实现的就是在`java.net.InetAddress#getAllByname`方法（接受字符串，返回InetAddress数组）前传入一段字符串，这个语句时调用DNSHook的checkDNSLookup方法

![image-20231006182309305](images/51.png)

当触发getAllByname方法的时候，如果host不为空，会调用`HookHandler.doCheckWithoutRequest(Type.DNS, params);`来进行判断，主要是白名单判断

然后会调用doRealCheckWithoutRequest来进行处理

![image-20231006182619796](images/52.png)

![image-20231015110338552](images/53.png)

![image-20231015110405860](images/54.png)

先通过checkParam（在CheckManager.init设置的CheckParameter）的checkParam方法，获取check结果，然后返回插件中设置的是否为block

![image-20231015141333832](images/55.png)

```
1.com.baidu.openrasp.HookHandler#doCheckWithoutRequest
在这里，做了一些云控注册成功判断和白名单的处理

2.com.baidu.openrasp.HookHandler#doRealCheckWithoutRequest
在这里，做了一些参数的封装，以及失败日志、耗时日志等输出，并且在检测到攻击时（下一层返回），抛出异常

3.com.baidu.openrasp.plugin.checker.CheckerManager#check

4.com.baidu.openrasp.plugin.checker.AbstractChecker#check
在这里，对js或者其他类型的安全检测之后的结果，进行事件处理并返回结果

5.com.baidu.openrasp.plugin.checker.v8.V8Checker#checkParam

6.com.baidu.openrasp.plugin.js.JS#
在这里，做了一些commonLRUCache的并发幂等处理
```

具体关于记录和判断的地方就没有去看了，关于云控的直接修改配置的暂时还没有去了解

对于一些规则配置在plugins目录下的official.js

![image-20231006185904334](images/56.png)

安装后有一个openrasp.yaml里面也会有一些配置，比如说跳转之类的，但是如果用了云控，都可以直接在云控设置

![image-20231006190034781](images/57.png)

包括报错返回的状态码，内容，请求头也可以删除

![image-20231006190057887](images/58.png)

# openrasp-iast扫描器安装

请先确保安装:

1. [OpenRASP 管理后台](https://rasp.baidu.com/doc/install/panel.html) 版本 >= **1.2.0**，并至少有**一台在线主机**
2. [Python 3.6](https://www.python.org/downloads/) 或者更高版本
3. [MySQL 5.5.3](https://dev.mysql.com/downloads/mysql/)， 或者更高版本

使用 pip3 安装 openrasp-iast，以及依赖的库:

```bash
pip3 install --upgrade git+https://github.com/baidu-security/openrasp-iast
```

如果pyyaml有问题，可以下载下来修改requirement.txt里面的版本为6.0.1

![image-20231006193514800](images/59.png)

也可以直接下载 PyInstaller 打包的二进制版本，我们每隔2小时自动更新一次:

```bash
wget https://packages.baidu.com/app/openrasp/openrasp-iast-latest -O /usr/local/bin/openrasp-iast
```

配置 MySQL 数据库，建立名为 `openrasp` 的数据库，并为 `rasp@%` 授权，密码为 `rasp123`（建议使用强度更高的密码，这里只是举例）。请用 root 账号连接 mysql 并执行如下语句:

```mysql
# 如果是 MySQL 8.X 以及更高版本
DROP DATABASE IF EXISTS openrasp;
CREATE DATABASE openrasp default charset utf8mb4 COLLATE utf8mb4_general_ci;
CREATE user 'rasp'@'%' identified with mysql_native_password by 'rasp123';
grant all privileges on openrasp.* to 'rasp'@'%' with grant option;
grant all privileges on openrasp.* to 'rasp'@'localhost' with grant option;

# 如果是低版本 MySQL
DROP DATABASE IF EXISTS openrasp;
CREATE DATABASE openrasp default charset utf8mb4 COLLATE utf8mb4_general_ci;
grant all privileges on openrasp.* to 'rasp'@'%' identified by 'rasp123';
grant all privileges on openrasp.* to 'rasp'@'localhost' identified by 'rasp123';
```

![image-20231006193549412](images/60.png)

如果管理后台是 v1.3.0 之前的版本，你可以使用这个命令安装老版本的 openrasp-iast:

```bash
pip3 install --upgrade git+https://github.com/baidu-security/openrasp-iast@v1.2
```

## 配置管理后台

```
openrasp-iast config -a d749f6c7384a793ba72ca2155f77ec3206ce48d5 -b 9nBmc4D2gojBZh0M067zqx1LiY2ud4eTmfOkvD94tk0 -c http://127.0.0.1:8086/ -m mysql://rasp:rasp123@127.0.0.1:3306/openrasp
```

![image-20231006193807350](images/61.png)

启动 Fuzz 工具

```
openrasp-iast start -f
```

-或者后台启动-

```
openrasp-iast start
```

# 加载了解

官方给的防护插件是official.js

![image-20231015103205935](images/62.png)

首先定义了一个algorithmConfig

![image-20231015103257094](images/63.png)

首先注意如果meta.all_log开启的话，所有算法都被变为log模式，只记录日志（具体判断的话在后面有相应实现代码判断全局修改），如果是云控的话可以在后台修改，但是单机运行的话不修改就会没有什么防护作用，其次里面定了不同的算法，里面有action模式（共三种，block，log，ignore）以及相应的黑名单

![image-20231015103735319](images/64.png)

如果是日志记录模式则会打印日志，内容类似于

![image-20231015103756861](images/65.png)

只不过我是通过云控安装的，挑一个简单的来看看

![image-20231015104349466](images/66.png)

最后判断的时候具体实现在

![image-20231015104408352](images/67.png)

默认是log，不为ignore就进入具体的实现

![image-20231015104836938](images/68.png)

主要调用RegExp进行正则匹配，来判断是否是黑名单

初次之外，在插件加载的时候，前面提到了EngineBoot的start方法会调用loadConfig加载一些配置

![image-20231015142105149](images/69.png)

其中存在对log4j初始化的操作，跟进ConfigFileAppender

![image-20231015142132914](images/70.png)

跟进initLog4jLogger

![image-20231015142435921](images/71.png)

在这个方法最后会setLogMaxBackup

![image-20231015142459111](images/72.png)

会调Config的getConfig方法，Config方法存在一个静态代码块

![image-20231015142701486](images/73.png)

调用方法init方法

![image-20231015142744553](images/74.png)

首先会加载配置文件openrasp.yml，如果不是云控的话会调用FileScanMonitor.addMonitor方法

![image-20231015143208113](images/75.png)

这个方法默认为scan，会使用FileAlterationMonitor对文件进行监控，这里监控的是conf目录，也就是存放openrasp.yml的目录

当有对文件目录进行删除创建才会重新加载配置文件

# 绕过

openrasp虽然可以进行一些简单的防护，但是还是存在一定的绕过风险

## 黑名单绕过

以command_common为例

```javascript
command_common: {
    name:    '算法3 - 识别常用渗透命令（探针）',
    action:  'log',
    pattern: 'cat.{1,5}/etc/passwd|nc.{1,30}-e.{1,100}/bin/(?:ba)?sh|bash\\s-.{0,4}i.{1,20}/dev/tcp/|subprocess.call\\(.{0,6}/bin/(?:ba)?sh|fsockopen\\(.{1,50}/bin/(?:ba)?sh|perl.{1,80}socket.{1,120}open.{1,80}exec\\(.{1,5}/bin/(?:ba)?sh'
},
```

这个算法是命令执行的算法的第三个

![image-20231015145911088](images/76.png)

其中采用的过滤方式是黑名单方式，但是也会存在过滤不全的情况，比如说cat /etc/passwd

![image-20231015150010592](images/77.png)

![image-20231015150002358](images/78.png)

当我直接执行的时候已经被拦截了

![image-20231015150035206](images/79.png)

但是cat函数支持同时读多个文件`cat /abc/def /etc/passwd`，这样进行绕过

![image-20231015150125770](images/80.png)

或者多加一些目录穿越符`cat ../../../../../..//etc/passwd`

命令执行参数绕过，对于命令执行算法2，可能会匹配一些命令注入，像`/bin/bash -c`这种就会被过滤

![image-20231015150926455](images/81.png)

可以参数一些命令执行的参数来进行绕过

![image-20231015150914259](images/82.png)

## dnslog绕过

dnslog不仅仅判断了一些请求的命令例如curl，ping，还判断了一些常见的域名

![image-20231015151211484](images/83.png)

可以采用句号绕过，但是这个不同的系统可能不太一样，我macos的系统没有成功，但是服务器debian却可以成功

![image-20231015151650905](images/84.png)

![image-20231015151656412](images/85.png)



## 修改属性绕过

通过前面的分析，我们知道了其实最后hook的地方会通过doCheckWithoutRequest和doRealCheckWithoutRequest判断

![image-20231015153127333](images/86.png)

![image-20231015153116434](images/87.png)

其中提到了几点，

- 当服务器的cpu使用率超过90%，禁用全部hook点
- 当云控注册成功之前，不进入任何hook点
- 当enableHook为false的时候，直接会return

这三点就是修改属性绕过的关键点

### 通过表达式执行修改

openrasp虽然对ognl表达式进行了检测，但是对于一些EL表达式，spel表达式，还有通过用js引擎进行命令执行的方式没有检测

![image-20231015153403408](images/88.png)

虽然这些要执行命令最后的本质还是ProcessBuilder，但是这些东西能执行的就不仅仅只是这个了

他们可以去执行相应的代码对openrasp配置进行修改，其中就包括了对enableHook修改

```
@RequestMapping("/eval")
@ResponseBody
public String eval(String code) throws Exception{
    new ScriptEngineManager().getEngineByName("js").eval(code);
    return "OK";
}
```

![image-20231015154619803](images/89.png)



可以看到最后还是通过命令执行来记录的日志

![image-20231015154648252](images/90.png)

当我把所有命令执行全部设置为block

```
code=com.baidu.openrasp.HookHandler.enableHook.getAndSet(false);
```

![image-20231015155108399](images/91.png)

命令执行依然成功了，这个是全局的block全部关闭了，enableHook是AtomicBoolean类

> AtomicBoolean类 getAndSet 方法和 compareAndSet方法的区别，这两个方法的区别在java的文档中记录的很明确了
>
> compareAndSet：如果当前值 == 预期值，则以原子方式将该值设置为给定的更新值。这里需要注意的是这个方法的返回值实际上是是否成功修改，而与之前的值无关。
>
> getAndSet ：以原子方式设置为给定值，并返回以前的值。

![image-20231015155425248](images/92.png)

这里关闭enableHook后，即使是云控也会失效，当我重新设置，即使是过了云控的心跳周期，仍然没有办法拦截，需要重启openrasp应用，如果可以用spel和el表达式同理这样去关闭配置

### 通过反序列化修改

当存在反序列化漏洞可以通过TemplatesImpl加载字节码的时候，可以自己执行恶意内中的代码，可以通过反射区修改对应的属性

```
try {
  Class<?> clz = Thread.currentThread().getContextClassLoader().loadClass("com.baidu.openrasp.config.Config");
  java.lang.reflect.Method getConfig = clz.getDeclaredMethod("getConfig");
  java.lang.reflect.Field disableHooks = clz.getDeclaredField("disableHooks");
  disableHooks.setAccessible(true);
  Object ins = getConfig.invoke(null);

  disableHooks.set(ins,true);
} catch (Exception e) {}
```

将disableHooks返回true，导致在doCheckWithoutRequest直接返回，另外也可以去操作getCloudSwitch和getHookWhiteAll返回值

![image-20231015155849764](images/93.png)

当然在openrasp中这么危险的地方在反序列化中也是默认禁用的

![image-20231015160027726](images/94.png)

不过可以发现bcel和在cc链中的一个InstantiateFactory类没有被过滤

bcel可以配合fastjson加载bcel字节码然后用这种反射的方式修改属性

除此之外，可以通过CC链的InstantiateFactory和FactoryTransformer进行实例化结合ClassPathXmlApplicationContext去远程加载xml关闭相应属性

![image-20231015160555178](images/95.png)

## 文件上传绕过

这个不是bypass文件上传，而是通过文件上传区覆盖插件关闭openrasp检测，当在一定情况下，可以上传js或者yml文件的时候，可以去覆盖配置文件或者js插件进行绕过

在一般的文件上传检测中不会去禁止js上传，并且openrasp默认对于文件上传`js`默认是关闭逻辑检测的开关

前面的分析可以知道，在openrasp中，对于js插件或者conf下的openrasp.yml做出修改的时候，因为热加载机制会重新对其进行加载，如果可以将文件上传到对应目录下就可以绕过openrasp的防护了

对于官方插件official.js，我们可以修改all_log将所有算法均设置为记录日志，或者将需要的改成log或者ignore

![image-20231015161131479](images/96.png)

不过这种修改插件的方式如果是云控的话，不知道会不会不一样，因为单机模式才会去监控plugins目录下的js文件

对于openrasp.yml，可以修改白名单

![image-20231015161252662](images/97.png)

将ip加白，注意没有前面的`http://或者https://`



写在最后：

对于openrasp启动流程和原理以及绕过方式有了一定的了解，但是对于V8引擎来配合js插件的那里还是有点没看懂，已经一些关于云控的心跳机制，以及算法配置的地方没有去了解了。



参考链接：

https://rasp.baidu.com/doc/install/panel.html

https://xz.aliyun.com/t/11803#toc-6

https://y4tacker.github.io/2022/05/28/year/2022/5/OpenRasp%E5%88%86%E6%9E%90/#Hook

https://threedr3am.github.io/2019/12/31/OpenRASP%E6%A0%B8%E5%BF%83%E6%BA%90%E7%A0%81%E6%B5%85%E6%9E%90/

代码审计星球——OpenRASP分析与绕过