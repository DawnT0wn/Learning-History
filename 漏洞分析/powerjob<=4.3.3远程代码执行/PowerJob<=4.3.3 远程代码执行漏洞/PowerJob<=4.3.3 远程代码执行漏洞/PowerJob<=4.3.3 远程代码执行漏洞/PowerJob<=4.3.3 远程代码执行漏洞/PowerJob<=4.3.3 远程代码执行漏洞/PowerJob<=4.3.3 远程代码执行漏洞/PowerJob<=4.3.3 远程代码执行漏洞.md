# 漏洞描述

PowerJob 是一款开源的分布式任务调度框架。

近日，微步漏洞团队监测到PowerJob存在一处远程代码执行漏洞，由于 PowerJob 未对网关进行鉴权，4.3.3 及之前版本中，未经授权的攻击者可向 /instance/detail 端点发送恶意构造的 instanceId 参数远程执行任意代码。

经过分析与研判，该漏洞利用难度低，能够造成远程命令执行，建议尽快修复。

**影响范围**：PowerJob <= 4.3.3

**漏洞编号：**CVE-2023-37754

# 环境搭建

Github 开源地址：https://github.com/PowerJob/PowerJob

修改application-daily.properties中的mysql连接信息

![image-20230731164457011](img/1.png)

直接启动可能会因为spring boot内带tomcat，tomcat中的websocket会有冲突出现问题，注释掉WebConfig的这个Bean

![image-20230731164547692](img/2.png)

![image-20230731164642882](img/3.png)

注册一个应用，将power-job-samples的application.properties中的powerjob.worker.app-name改为应用名称

![image-20230801102033840](img/4.png)

因为server中的任务需要交给job执行，所以再启动server注册应用后，将worker绑定应用，然后启动

在server中看到了加入的worker

![image-20230807110819654](img/5.png)

# 前置知识

在powerjob的官方文档中提到了提供的一些官方处理器，其中有一个shell处理器可以执行脚本

![image-20230801102548772](img/6.png)

但是powerjob3和powerjob4有一点区别

![image-20230801102716774](img/7.png)

并没有直接提供shell的配置，但是shell处理器的全限定类名 `tech.powerjob.official.processors.impl.script.ShellProcessor`，使用内建的方式，可以直接指定对应的processor

而在powerjob3中，用到的processType就不是内建，而是SHELL，内容也不是全限定类名，而是直接的shell脚本内容

![image-20230801103013198](img/8.png)

保存任务后，如果定时信息是cron也能自动运行，也可以直接点击任务运行

![image-20230801103102235](img/9.png)

![image-20230801103122361](img/95.png)

执行了对应的命令，这个都是PowerJob自己提供的

# 漏洞复现

复现环境：PowerJob 4.3.3，JDK8u66

由于powerjob本身接口是没有授权的，所以能够通过对应接口去进行对应任务的添加执行

![image-20230801104039183](img/10.png)

通过/job/list获取对应job的ID

```
{"appId":1,"index":0,"pageSize":10,"keyword":"CVE"}
```

![image-20230801104113723](img/11.png)

然后用/job/run去运行对应的job

```
http://127.0.0.1:7700/job/run?jobId=142&appId=1
```

![image-20230801104233650](img/12.png)

拿到对应的data，通过/instance/detail的instanceId参数传入data获取命令执行结果

```
http://127.0.0.1:7700/instance/detail?instanceId=566574017431994496
```

![image-20230801104411438](img/13.png)

# 漏洞分析

一方面是因为接口未授权，另一方面是powerjob本身都任务调度过程支持执行shell命令，在WorkerActor类中，定义了很多处理器，用来处理不同节点的请求，runjob处理器用来处理任务调度的请求，接下来主要分析任务调度的过程。

![image-20230801104914929](img/14.png)

而runjob节点则是通过taskTrackerActor.onReceiveServerScheduleJobReq(req)来处理；

![image-20230801105802071](img/15.png)

![image-20230801105846960](img/16.png)

分轻量级和重量级调用不同的create，这里通过处理器的类型判断任务级别，单机、固定频率、固定延迟模式都属于轻量，其他则是重量

![image-20230801105910896](img/17.png)

这里调用LightTaskTracker的create方法

![image-20230801110243087](img/18.png)

会去实例化一个LightTaskTracker对象

![image-20230801110612978](img/19.png)

![image-20230801110544081](img/20.png)

先去对父类对参数进行一次初始化，然后调用constructTaskContext将各项参数封装到taskContext对象

![image-20230801110839721](img/21.png)

接下来就是去加载processor

![image-20230801110917824](img/22.png)

跟进load

![image-20230801112219399](img/23.png)

当前的processType是BUILT_IN，ProcessorFactoryList有四个Factory对象

而Optional.ofNullable(pf.supportTypes()).orElse(Collections.emptySet())会得到处理器参数

![image-20230801112350638](img/24.png)

这里选择的是内建的BUILT_IN，不同处理器会进入不同的factory的build方法

![image-20230801112503358](img/25.png)

根据注释看到，BUILT_IN的处理器工厂是BuiltInDefaultProcessorFactory这个类，在build方法中，会根据传进的ProcessorInfo信息来实例化对象

![image-20230801113034810](img/26.png)

在load方法结束后，得到的processorBean里面的processor其实就是ShellProcessor对象了，然后将任务提交到线程池中，调用processTask

![image-20230801113152439](img/27.png)

taskContext是前面已经封装好的context对象，包含了控制台传来的各项信息，这里的Processor是前面build方法设置的processor和classloader，强转成啦basicProcessor对象

![image-20230801113649405](img/28.png)

进入到CommonBasicProcessor的process方法，该类是一个通用处理器类

![image-20230801114953346](img/29.png)

在process方法中，将包含各种信息的TaskContext对象传到了process0方法中去，因为this是ShellProcess，所以调用的ShellProcess的process0，本身不存在这个方法，调用父类的process0，也即是AbstractScriptProcessor这个用来处理脚本的Processor

![image-20230801114343011](img/30.png)

process0方法属于AbstractScriptProcessor类，该类属于通用脚本处理器类，所有脚本插件都要继承该类。在process0方法中，会使用prepareScriptFile方法来根据控制台传来的jobParams内容生成脚本文件，文件名是shell_instanceId.sh

![image-20230801114829734](img/31.png)

调用getScriptName生成一个脚本文件路径，还是因为this为ShellProcess，所以调用ShellProcess的getScriptName

![image-20230801115159225](img/32.png)

返回的是`shell_instanceId.sh`，拼接上workdir，写入到对应的路径

接下来通过判断getRunCommand的值是否上CMD_SHELL，也即是检测是否为windows，然后传入对应的命令，通过ProcessBuilder.start()执行命令

![image-20230801115349583](img/33.png)

然后/instance/detail路由可以根据instanceId返回任务的执行后的结果![image-20230801115618253](img/34.png)





这个漏洞主要是PowerJob提供的任务调度的功能执行任务的时候，可以将jobParam的参数用ShellProcess处理器执行命令，这是它本身提供的功能，但是Powerjob对接口并没有做任何的授权，所以可以在授权的情况下造成命令执行

# 修复方案

**临时修补方案**：PowerJob是一款按内网系统去设计的分布式任务调度框架，在非必要条件下，不要将系统开放在公网上

官方尚未发布最新版本，对 api 端点进行鉴权或移除内置 shell 执行模块，若用户需要，可以根据自己的需求去编写对应的插件



# 参考链接

https://github.com/PowerJob/PowerJob/issues/675

https://novysodope.github.io/2023/07/02/100/#V4-X

https://www.yuque.com/powerjob/guidence/official_processor#Xql6t

https://www.oscs1024.com/hd/MPS-ycmw-pl41