# 代理模式

代理模式是Java常用的一种结构型设计模式，给某一个对象提供一个代理，并由代理对象来控制对真实对象的访问。代理类主要负责为被代理类（真实对象）预处理消息、过滤消息，然后将消息传递给被代理类，之后还能对消息进行后置处理。代理类不实现具体服务，而是通过调用被代理类中的方法来完成服务，并将执行结果封装处理。通过代理对象访问目标对象可以在实现目标对象的基础上，又在不改变目标对象方法的情况下，对方法进行增强，即扩展目标对象的功能

简单的说就是，我们在访问实际对象时，是通过代理对象来访问的，代理模式就是在访问实际对象时引入一定程度的间接性，因为这种间接性，可以附加多种用途

根据字节码的创建时机来分类，可以分为静态代理和动态代理：

- **静态代理：** 在程序运行前就已经存在代理类的字节码文件，代理类与被代理类的关系在运行前就确定了。
- **动态代理：** 代理类是在程序运行期间由JVM根据反射等机制动态生成的，程序运行前并不存在代理类的字节码文件。

# 静态代理

先定义一个接口

```
package cn.DawnT0wn.proxy;

public interface PersonInterface {
    void Name(String param);
    void Age();
}
```

再定义一个这个接口的实现类,作为被代理类

```
package cn.DawnT0wn.proxy;

public class Person implements PersonInterface{

    public void Name(String param){
        System.out.println("I'm "+param);
    }

    public void Age(){
        System.out.println("I'm 20 years old!");
    }
}
```

接着再创建一个代理类,注意代理类和被代理类的接口要一样,而且代理类还可以在被代理类的基础上实现其他功能

```
package cn.DawnT0wn.proxy;

public class PersonProxy implements PersonInterface{

    //目标对象
    PersonInterface personInterface = new Person();
    @Override
    public void Name(String param) {
        personInterface.Name(param);
        System.out.println("可添加其他功能");
    }

    @Override
    public void Age() {
        personInterface.Age();
        System.out.println("可添加其他功能");
    }
}
```

测试代码

```
package cn.DawnT0wn.proxy;

public class StaticTest {

    public static void main(String[] args) {
        //代理对象
        PersonProxy personProxy = new PersonProxy();
        personProxy.Name("DawnT0wn");
        personProxy.Age();
    }
}
```

![image-20211213150150851](images/1.png)

可以看到我对代理类的操作,可以操作被代理类的函数和在代理类里面增加一些功能

静态代理的缺点：

1. 由于代理类需实现与目标对象相同的接口，当有多个需被代理的类时，只有两种方法：

   - 只创建一个代理类，这个代理类同时实现多个接口及其抽象方法，但是会导致代理类过于庞大；

   - 创建多个代理类，每个代理类对应一个被代理类，但是会长生过多代理类；

2. 当接口需要增加、删除、修改方法时，被代理类和代理类的代码都要修改，代码量过大，不易维护。

# JDK动态代理

JDK动态代理是JDK动态生成的,基于拦截器和反射

```
JDK代理是不需要第三方库支持的，只需要JDK环境就可以进行代理，使用条件：

1）必须实现InvocationHandler接口；

2）使用Proxy.newProxyInstance产生代理对象；

3）被代理的对象必须要实现接口；
```

先来看一个例子,接口和被代理类和之前一样

我们另外创一个ProxyHandler处理器实现InvocationHandler接口

```
package cn.DawnT0wn.proxy;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;

public class ProxyHandler implements InvocationHandler {
    private Object obj;     //被代理的对象
    public ProxyHandler(Object obj){
        this.obj = obj;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        Object inv = method.invoke(obj, args);  //通过反射调用并执行目标对象的方法
        System.out.println("invoke方法执行了");
        return inv;     //返回执行结果
    }
}
```

invoke的三个参数：

- proxy：被代理的对象
- method：调用的方法
- args：方法中的参数

然后写一个动态代理测试代码

```
package cn.DawnT0wn.proxy;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;

public class DynamicTest {
    public static void main(String[] args) {
        //创建目标对象
        PersonInterface per = new Person();
        //创建一个将传给代理类的调用请求处理器，处理所有代理对象上的方法调用
        InvocationHandler handler = new ProxyHandler(per);
        //返回一个接口的代理实例
        PersonInterface person = (PersonInterface) Proxy.newProxyInstance(
                per.getClass().getClassLoader(),    //获取被代理类的的类加载器
                per.getClass().getInterfaces(),     //获取被代理类实现的接口
                handler     //处理器
        );

        person.Name("DawnT0wn");
        person.Age();
    }
}
```

运行效果图

![image-20211213223055261](images/2.png)

# 动态代理生成对象分析

上面看了例子或许多少有点明白了,接下来就去深入源码看看具体是怎么调用来实现动态代理的

**动态代理实现步骤：**

- 通过实现 InvocationHandler 接口创建自己的调用处理器；
- 通过为 Proxy 类指定 ClassLoader 对象和一组 interface 来创建动态代理类；
- 通过反射机制获得动态代理类的构造函数，其唯一参数类型是调用处理器接口类型；
- 通过构造函数创建动态代理类实例，构造时调用处理器对象作为参数被传入。

代理对象的生成使用了`java.lang.reflect.Proxy`类的`newProxyInstance`方法，看一下源码

```
public static Object newProxyInstance(ClassLoader loader,
                                      Class<?>[] interfaces,
                                      InvocationHandler h)
    throws IllegalArgumentException
{
    Objects.requireNonNull(h);//如果h为空则会抛出异常

    final Class<?>[] intfs = interfaces.clone();//拷贝 类实现的所有接口
    final SecurityManager sm = System.getSecurityManager();//获取当前系统的安全接口，此时为null,所以不进入if
    if (sm != null) {
        checkProxyAccess(Reflection.getCallerClass(), loader, intfs);
        // Reflection.getCallerClass返回调用该方法的方法的调用类;loader：接口的类加载器
	    // 进行包访问权限、类加载器权限等检查
    }

    /*
     * 查找或生成指定的代理类
     */
    Class<?> cl = getProxyClass0(loader, intfs);

    /*
     * 使用指定的调用处理程序调用其构造函数
     */
    try {
        if (sm != null) {
            checkNewProxyPermission(Reflection.getCallerClass(), cl);
        }

        final Constructor<?> cons = cl.getConstructor(constructorParams);
        //获取代理类的构造函数,这里的constructorParams是类定义的常量
        //private static final Class<?>[] constructorParams ={ InvocationHandler.class };
        final InvocationHandler ih = h;
        if (!Modifier.isPublic(cl.getModifiers())) {
            AccessController.doPrivileged(new PrivilegedAction<Void>() {
                public Void run() {
                    cons.setAccessible(true);
                    return null;
                }
            });
        }
        return cons.newInstance(new Object[]{h});
        //返回代理类的构造函数对象来创建需要返回的代理类对象
    } catch (IllegalAccessException|InstantiationException e) {
        throw new InternalError(e.toString(), e);
    } catch (InvocationTargetException e) {
        Throwable t = e.getCause();
        if (t instanceof RuntimeException) {
            throw (RuntimeException) t;
        } else {
            throw new InternalError(t.toString(), t);
        }
    } catch (NoSuchMethodException e) {
        throw new InternalError(e.toString(), e);
    }
}
```

所以在newProxyInstance的最后返回是代理类ProxyHandler的构造函数对象

![image-20211213231740678](images/3.png)

对`this.obj=obj`进行操作,即`this.obj=new Object[]{h}`

于是下列代码返回的就是一个代理实例

```
PersonInterface person = (PersonInterface) Proxy.newProxyInstance(
        per.getClass().getClassLoader(),    //获取被代理类的的类加载器
        per.getClass().getInterfaces(),     //获取被代理类实现的接口
        handler     //处理器
);
```

至于invoke方法

在动态代理中InvocationHandler是核心，每个代理实例都具有一个关联的调用处理程序(InvocationHandler)。

对代理实例调用方法时，将对方法调用进行编码并将其指派到它的调用处理程序(InvocationHandler)的invoke()方法。

所以对代理方法的调用都是通InvocationHadler的invoke来实现中，而invoke方法根据传入的代理对象，

方法和参数来决定调用代理的哪个方法

所以这里会我们调用代理实例的方法的时候触发invoke

![image-20211213232431207](images/4.png)

在代理类中重写了invoke方法

```
public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
    Object inv = method.invoke(obj, args);  //通过反射调用并执行目标对象的方法
    System.out.println("invoke方法执行了");
    return inv;     //返回执行结果
}
```

invoke的三个参数：

- proxy：被代理的对象
- method：调用的方法
- args：方法中的参数

这就是大致的调用过程了

会过头再看看newProxyInstance里面的关键方法

生成代理类的`getProxyClass0`

```
private static Class<?> getProxyClass0(ClassLoader loader,
                                       Class<?>... interfaces) {
    if (interfaces.length > 65535) {
        throw new IllegalArgumentException("interface limit exceeded");
    }

    // If the proxy class defined by the given loader implementing
    // the given interfaces exists, this will simply return the cached copy;
    // otherwise, it will create the proxy class via the ProxyClassFactory
    return proxyClassCache.get(loader, interfaces);
    //这里proxyClassCache = new WeakCache<>(new KeyFactory(), new ProxyClassFactory());
}
```

注释给的很清楚

```
//如果实现给定接口的给定加载程序定义的代理类存在，这将简单地返回缓存副本；

//否则，它将通过ProxyClassFactory创建代理类
```

跟进proxyClassCache

```
/*
*一个工厂函数，根据类加载器和接口数组生成、定义并返回代理类。
*/
private static final class ProxyClassFactory
        implements BiFunction<ClassLoader, Class<?>[], Class<?>>
    {
        // 所有代理类名的前缀为“$Proxy”
        private static final String proxyClassNamePrefix = "$Proxy";
 
        // 用于生成唯一代理类名的下一个数字，如“$Proxy0”，“$Proxy1”
        private static final AtomicLong nextUniqueNumber = new AtomicLong();
 
        @Override
        public Class<?> apply(ClassLoader loader, Class<?>[] interfaces) {
 
            Map<Class<?>, Boolean> interfaceSet = new IdentityHashMap<>(interfaces.length);
            for (Class<?> intf : interfaces) {
                /*
                 * 验证类加载器是否将此接口的名称解析为同一类对象。 
                 */
                Class<?> interfaceClass = null;
                try {
                    interfaceClass = Class.forName(intf.getName(), false, loader);
                } catch (ClassNotFoundException e) {
                }
                if (interfaceClass != intf) {
                    throw new IllegalArgumentException(
                        intf + " is not visible from class loader");
                }
                /*
                 *验证Class对象是否实际表示接口。 
                 */
                if (!interfaceClass.isInterface()) {
                    throw new IllegalArgumentException(
                        interfaceClass.getName() + " is not an interface");
                }
                /*
                 * 验证此接口是否重复。
                 */
                if (interfaceSet.put(interfaceClass, Boolean.TRUE) != null) {
                    throw new IllegalArgumentException(
                        "repeated interface: " + interfaceClass.getName());
                }
            }
 
            String proxyPkg = null;     // package to define proxy class in
            int accessFlags = Modifier.PUBLIC | Modifier.FINAL;
 
            /*
             * 记录非公共代理接口的包，以便在同一个包中定义代理类。验证所有非公共代理接口是否在同一个包中。 
             */
            for (Class<?> intf : interfaces) {
                int flags = intf.getModifiers();
                if (!Modifier.isPublic(flags)) {
                    accessFlags = Modifier.FINAL;
                    String name = intf.getName();
                    int n = name.lastIndexOf('.');
                    String pkg = ((n == -1) ? "" : name.substring(0, n + 1));
                    if (proxyPkg == null) {
                        proxyPkg = pkg;
                    } else if (!pkg.equals(proxyPkg)) {
                        throw new IllegalArgumentException(
                            "non-public interfaces from different packages");
                    }
                }
            }
 
            if (proxyPkg == null) {
                //如果没有非公共代理接口，请使用com.sun.proxy包
                proxyPkg = ReflectUtil.PROXY_PACKAGE + ".";
            }
 
            /*
             * 选择要生成的代理类的名称。
             */
            long num = nextUniqueNumber.getAndIncrement();
            String proxyName = proxyPkg + proxyClassNamePrefix + num;
 
            /*
             * 生成指定的代理类的字节码文件。
             */
            byte[] proxyClassFile = ProxyGenerator.generateProxyClass(
                proxyName, interfaces, accessFlags);
            try {
                return defineClass0(loader, proxyName,
                                    proxyClassFile, 0, proxyClassFile.length);
            } catch (ClassFormatError e) {
                /*
                 * 这里的ClassFormatError意味着（除非代理类生成代码中存在bug），为代理类创建提供的参数中存在其他一些无效方面（例如超出了虚拟机限制）。
                 */
                throw new IllegalArgumentException(e.toString());
            }
        }
    }

```

在生成代理类的字节码文件的时候调用了`generateProxyClass`,跟进看看

```
public static byte[] generateProxyClass(final String var0, Class<?>[] var1, int var2) {
		ProxyGenerator var3 = new ProxyGenerator(var0, var1, var2);
        //使用generateClassFile()方法生成代理类的字节码文件
        final byte[] var4 = var3.generateClassFile();
        //保存代理类的字节码文件
        if (saveGeneratedFiles) {
            AccessController.doPrivileged(new PrivilegedAction<Void>() {
                public Void run() {
                    try {
                        int var1 = var0.lastIndexOf(46);
                        Path var2;
                        if (var1 > 0) {
                            Path var3 = Paths.get(var0.substring(0, var1).replace('.', File.separatorChar));
                            Files.createDirectories(var3);
                            var2 = var3.resolve(var0.substring(var1 + 1, var0.length()) + ".class");
                        } else {
                            var2 = Paths.get(var0 + ".class");
                        }
 
                        Files.write(var2, var4, new OpenOption[0]);
                        return null;
                    } catch (IOException var4x) {
                        throw new InternalError("I/O exception saving generated file: " + var4x);
                    }
                }
            });
        }
 
        return var4;
    }

```

生成代理类字节码文件的generateClassFile方法

```
private byte[] generateClassFile() {
        //将接口中的方法和Object中的方法添加到代理方法中(proxyMethod)
        this.addProxyMethod(hashCodeMethod, Object.class);
        this.addProxyMethod(equalsMethod, Object.class);
        this.addProxyMethod(toStringMethod, Object.class);
        Class[] var1 = this.interfaces;
        int var2 = var1.length;
 
        int var3;
        Class var4;
        //获取接口中所有方法并添加到代理方法中
        for(var3 = 0; var3 < var2; ++var3) {
            var4 = var1[var3];
            Method[] var5 = var4.getMethods();
            int var6 = var5.length;
 
            for(int var7 = 0; var7 < var6; ++var7) {
                Method var8 = var5[var7];
                this.addProxyMethod(var8, var4);
            }
        }
 
        Iterator var11 = this.proxyMethods.values().iterator();
 
        List var12;
        while(var11.hasNext()) {
            var12 = (List)var11.next();
            checkReturnTypes(var12);
        }
 
        Iterator var15;
        try {
            //生成代理类的构造函数
            this.methods.add(this.generateConstructor());
            var11 = this.proxyMethods.values().iterator();
 
            while(var11.hasNext()) {
                var12 = (List)var11.next();
                var15 = var12.iterator();
 
                while(var15.hasNext()) {
                    ProxyGenerator.ProxyMethod var16 = (ProxyGenerator.ProxyMethod)var15.next();
                    this.fields.add(new ProxyGenerator.FieldInfo(var16.methodFieldName, "Ljava/lang/reflect/Method;", 10));
                    this.methods.add(var16.generateMethod());
                }
            }
 
            this.methods.add(this.generateStaticInitializer());
        } catch (IOException var10) {
            throw new InternalError("unexpected I/O Exception", var10);
        }
 
        if (this.methods.size() > 65535) {
            throw new IllegalArgumentException("method limit exceeded");
        } else if (this.fields.size() > 65535) {
            throw new IllegalArgumentException("field limit exceeded");
        } else {
            this.cp.getClass(dotToSlash(this.className));
            this.cp.getClass("java/lang/reflect/Proxy");
            var1 = this.interfaces;
            var2 = var1.length;
 
            for(var3 = 0; var3 < var2; ++var3) {
                var4 = var1[var3];
                this.cp.getClass(dotToSlash(var4.getName()));
            }
 
            this.cp.setReadOnly();
            ByteArrayOutputStream var13 = new ByteArrayOutputStream();
            DataOutputStream var14 = new DataOutputStream(var13);
 
            try {
                var14.writeInt(-889275714);
                var14.writeShort(0);
                var14.writeShort(49);
                this.cp.write(var14);
                var14.writeShort(this.accessFlags);
                var14.writeShort(this.cp.getClass(dotToSlash(this.className)));
                var14.writeShort(this.cp.getClass("java/lang/reflect/Proxy"));
                var14.writeShort(this.interfaces.length);
                Class[] var17 = this.interfaces;
                int var18 = var17.length;
 
                for(int var19 = 0; var19 < var18; ++var19) {
                    Class var22 = var17[var19];
                    var14.writeShort(this.cp.getClass(dotToSlash(var22.getName())));
                }
 
                var14.writeShort(this.fields.size());
                var15 = this.fields.iterator();
 
                while(var15.hasNext()) {
                    ProxyGenerator.FieldInfo var20 = (ProxyGenerator.FieldInfo)var15.next();
                    var20.write(var14);
                }
 
                var14.writeShort(this.methods.size());
                var15 = this.methods.iterator();
 
                while(var15.hasNext()) {
                    ProxyGenerator.MethodInfo var21 = (ProxyGenerator.MethodInfo)var15.next();
                    var21.write(var14);
                }
 
                var14.writeShort(0);
                return var13.toByteArray();
            } catch (IOException var9) {
                throw new InternalError("unexpected I/O Exception", var9);
            }
        }
    }

```

字节码生成后，调用defineClass0来解析字节码，生成了Proxy的Class对象



参考链接:

http://1.15.187.227/index.php/archives/457/

https://www.jianshu.com/p/9bcac608c714

https://blog.csdn.net/yhl_jxy/article/details/80586785
