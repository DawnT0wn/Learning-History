# 前言

最近才上手java就去接触了反序列化,但是在CC链中遇到了一些东西,就想回过头来总结一下

就像CC1中用到的annotation注解、

# Java注解

听到注解,第一反应就是注释,但是这两者是有本质上的区别的

Java 注解（Annotation）又称 Java 标注，是 JDK5.0 引入的一种注释机制。

注解和注释可不一样，注释是用文字描述、解释程序，是给程序员看的，为了让程序员更快速的了解程序功能；
而注解是一种代码级别的说明，用来说明程序，是给计算机看的，可理解为给程序贴上了一个标签

对于注解,百度是这样解释的:

- 从JDK5开始,Java增加对元数据的支持，也就是注解，注解与注释是有一定区别的，可以把注解理解为代码里的特殊标记，这些标记可以在编译，类加载，运行时被读取，并执行相应的处理。通过注解开发人员可以在不改变原有代码和逻辑的情况下在源代码中嵌入补充信息。

**使用格式：**`@注解名称[(属性值)]`

## 内置注解

### @Override 

**作用**:检查该方法是否是重写方法。如果发现其父类，或者是引用的接口中并没有该方法时，会报编译错误。

这个注解可以检测被该注解标注的方法是否是继承自父类（接口）的，可以确保子类确实重写了父类的方法，避免出现低级错误；

写一个toString()方法,再使用override注解,他就会去检验这个toString和Object类的toString是否相同

如果相同,说明他是重写了toString方法,不会报错

![image-20211206175612553](images/1.png)

如果不同,则会报错

![image-20211206175601767](images/2.png)

### @Deprecated

**作用**:标记过时方法。如果使用该方法，会报编译警告，不过仍然可以调用，只不过会出现删除线

我们自己写一个`T0WN1`方法,假定这个方法存在一定的缺陷,这时可以重新写一个`T0WN2`方法来代替`T0WN1`方法,将`T0WN1`用`@Deprecated`注解标注然后当我们调用方法的时候T0WN1就会有一条删除线,不过还是可以调用的

![image-20211207125730637](images/3.png)

至于为什么不删除之前的方法,是因为一些方法对低版本用户兼容的问题,只能使用之前的方法,但是在高版本的时候就不推荐使用之前的方法了

### @SuppressWarnings

**作用**: 指示编译器去忽略注解中声明的警告

就用刚才的代码来看,这里有很多警告

![image-20211207130229024](images/4.png)

而`@SuppressWarnings`就是消除这些警告的,@SuppressWarnings`注解带有一个value属性，所以使用时要给value传值，一般写all，消除所有警告；

![image-20211207130423272](images/5.png)

用`@SuppressWarnings`注解消除警告一般放在类前

![image-20211207130307962](images/6.png)

可以看到警告没有了

### @SafeVarargs

**作用**:Java 7 开始支持，忽略任何使用参数为泛型变量的方法或构造函数调用产生的警告，即堆污染警告

首先了解一下什么是堆污染

就是把不带泛型的对象赋给一个带泛型的对象，为什么不行？因为不带泛型的话，默认会给泛型设定为object，意思就是什么类型都可以往里面塞

泛型，就是广泛的数据类型，有多广泛，什么数据类型都行

下面这段代码，在类名后面声明泛型`T`，那么其中的成员变量、成员方法就可以使用泛型来定义，可以给这个变量传入各种类型的值

```
package cn.DawnT0wn.Annotation;

public class Person<T> {
    public T say;

    public T getSay(){
        return say;
    }

    public void setSay(T say){
        this.say=say;
    }

    public static void main(String[] args){
        Person per1 = new Person();
        per1.setSay("hacker");
        System.out.println(per1.getSay() instanceof String);

        Person per2 = new Person();
        per2.setSay(58451920);
        System.out.println(per2.getSay() instanceof Integer);

        Person per3 = new Person();
        per3.setSay(3.1415926535);
        System.out.println(per3.getSay() instanceof Double);

    }
}
```

![image-20211207135009184](images/7.png)

注意：可变参数更容易引发堆污染异常，因为java不允许创建泛型数组，可变参数恰恰是数组

```
package cn.DawnT0wn.Annotation;

import java.util.Set;
import java.util.TreeSet;

public class T0WN {

    public static void method(Set<Integer> objects){
    }
    public static void main(String[] args)
    {
        Set set = new TreeSet();

        set.add("abc");
        method(set);
    }
}
```

method方法接受的是一个泛型为Integer类型的Set集合，而main方法中，将一个没有泛型的set对象传给method方法时，则可能造成堆污染，出现警告

![image-20211207135325011](images/8.png)

抑制这个警告的方法有三个:

- @SafeVarargs修饰引发该警告的方法或构造器
- 使用@suppressWarnings("unchecked")
- 编译时使用-Xlint:varargs

![image-20211207135427012](images/9.png)

### @FunctionalInterface

**作用**:Java 8 开始支持，标识一个匿名函数或函数式接口,用于检查我们写的接口是否与函数式接口定义时的相符合

什么是函数式接口？
一个接口，这个接口里面只能有一个抽象方法

所以我们在一个接口里面分别定义一个抽象方法和两个抽象方法用`@FunctionalInterface`注解

![image-20211207135824495](images/10.png)

没有报错

![image-20211207135849908](images/11.png)

报错了

![image-20211207135902943](images/12.png)

## 元注解

### @Retention

元注解——作用在其他注解的注解，在`java.lang.annotation`包下

Retention 的英文意为保留期的意思。当 @Retention 应用到一个注解上的时候，它解释说明了这个注解的的存活时间

它的取值如下：

- RetentionPolicy.SOURCE 注解只在源码阶段保留，在编译器进行编译时它将被丢弃忽视。
- RetentionPolicy.CLASS 注解只被保留到编译进行的时候，它并不会被加载到 JVM 中。
- RetentionPolicy.RUNTIME 注解可以保留到程序运行的时候，它会被加载进入到 JVM 中，所以在程序运行时可以获取到它们

**使用格式**：`@Retention(RetentionPolicy.SOURCE)`

### @Documented

这个元注解和文档有关。它的作用是能够将注解中的元素包含到 Javadoc 中去

### @Target

Target 是目标的意思，@Target 指定了注解运用的地方。

你可以这样理解，当一个注解被 @Target 注解时，这个注解就被限定了运用的场景。

类比到标签，原本标签是你想张贴到哪个地方就到哪个地方，但是因为 @Target 的存在，它张贴的地方就非常具体了，比如只能张贴到方法上、类上、方法参数上等等。@Target 有下面的取值



`@Target`有一个属性，有以下几种取值，可选用多个值，用逗号隔开

- `ElementType.ANNOTATION_TYPE` 可以给一个注解进行注解
- `ElementType.CONSTRUCTOR` 可以给构造方法进行注解
- `ElementType.FIELD` 可以给属性进行注解
- `ElementType.LOCAL_VARIABLE` 可以给局部变量进行注解
- `ElementType.METHOD` 可以给方法进行注解
- `ElementType.PACKAGE` 可以给一个包进行注解
- `ElementType.PARAMETER` 可以给一个方法内的参数进行注解
- `ElementType.TYPE` 可以给一个类型进行注解，比如类、接口、枚举

**使用格式**：`@Target(ElementType.TYPE,ElementType.PACKAGE)`

### @Inherited

inherite英文意思是继承

如果一个A方法被`@Inherited`和其他一些注解所标注，B方法继承了A方法，且B方法没有被任何注解标注，那么B方法就自动继承标注A方法的所有注解

### @Repeatable

@Repeatable 是 Java 1.8 才引进的

```
package cn.DawnT0wn.Annotation;

import java.lang.annotation.Repeatable;

@interface Persons {
    Person[]  value();
}
@Repeatable(Persons.class)
@interface Person{
    String role default "";
}
@Person(role="artist")
@Person(role="coder")
@Person(role="PM")
public class T0WN{
}
```

先定义一个注解Persons,然后用`@Repeatable`注解这个注解,`@Repeatable`括号里面相当于一个容器注解,什么是容器注解呢？就是用来存放其它注解的地方。它本身也是一个注解，这里即是Persons

然后再定义一个Person注解,然后用Person注解去标注T0WN,因为Person注解里面有一个属性role,可以给他赋值

T0WN在拥有Person注解属性的同时也拥有Persons的属性

## 注解的属性

注解的属性也叫做成员变量。注解只有成员变量，没有方法。注解的成员变量在注解的定义中以“无形参的方法”形式来声明，其方法名定义了该成员变量的名字，其返回值定义了该成员变量的类型

可以将它的属性理解为一种抽象方法

先定义一个注解

```
@Target(ElementType.TYPE)	//只能应用于类上
@Retention(RetentionPolicy.RUNTIME)		//保存到运行时
public @interface TestAnnotation {
    int age() default 11;
    String name() default "DawnT0wn";
}
```

这里我们定义了两个属性age和name,并赋予了默认值

在使用这个注解的时候就可以给他赋值,格式是`value=""`

```
@TestAnnotation(age=18,name="T0WN")
public class T0WN {
}
```

注意在注解中定义属性时它的类型必须是 8 种基本数据类型外加 类、接口、注解及它们的数组

如果有默认值在使用注解的时候就可以不用赋值了

如果当注解的属性只有一个的时候就可以不用`value=""`格式赋值了,可以直接输入值例如

当我上面定义的注解只有age属性的时候就可以这样使用

`@TestAnnotation(18)`

## 自定义注解

之前了解的都是java内置的注解,上面也看到了我们可以自己定义注解

注解通过 @interface 关键字进行定义

格式如下

```
//任意个元注解或内置注解
@...
@...
public @interface TestAnnotation{
    //任意个属性
}
```

可以简单理解为创建了一张名字为 TestAnnotation 的标签

注解本质上就是一个接口，默认继承`java.lang.annotation.Annotation`；
`Annotation`是所有注解类型扩展的公共接口，手动扩展这个接口不限定注解类型，且此接口本身不是注解类型

## 注解的使用

在明白了注解的写法和作用,接下来了解一下注解的使用

使用注解的目的是获取注解中定义的属性值，而注解是通过反射获取的

首先自定义一个注解

```
package cn.DawnT0wn.Annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target({ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
public @interface Anno1 {
    String className();
    String methodName();
}
```

然后写两个类分别定义两个不同的方法

```
package cn.DawnT0wn.Annotation;

public class Demo1 {
    public void show1(){
        System.out.println("Demo1-show1");
    }
}
```

```
package cn.DawnT0wn.Annotation;

public class Demo2 {

    public void show2(){
        System.out.println("Demo2-show2");
    }
}
```

再写一个ReflectTest.java

```
package cn.DawnT0wn.Annotation;

import java.lang.reflect.Method;

@Anno1(className = "cn.DawnT0wn.Annotation.Demo1", methodName = "show1")
public class ReflectTest {

    public static void main(String[] args) throws Exception {
        //1. 解析注解
        //获取该类的字节码文件对象
        Class<ReflectTest> reflectTestClass = ReflectTest.class;
        //获取上面@Anno1的注解对象
        Anno1 anno = reflectTestClass.getAnnotation(Anno1.class);

        //2.调用注解对象中定义的属性，获取返回值
        String className = anno.className();
        String methodName = anno.methodName();
        System.out.println(className);
        System.out.println(methodName);

        System.out.println("-------------------------------------------------");

        //3.加载该类进内存
        Class cls = Class.forName(className);

        //4.创建对象
        Object obj = cls.newInstance();

        //5.获取方法对象
        Method method = cls.getMethod(methodName);

        //执行方法
        method.invoke(obj);
    }
}
```

运行结果

![image-20211207225717012](images/13.png)

通过修改注解的值得到不同的运行结果

```
@Anno1(className = "cn.DawnT0wn.Annotation.Demo2", methodName = "show2")
```

![image-20211207230020947](images/14.png)

```
Anno1 anno = reflectTestClass.getAnnotation(Anno1.class);
```

上面这段代码意思就是在内存中生成了一个该注解(本质是接口)的子类实现对象，可以理解为下面代码

```
public class Anno1Impl implements Anno1{
    public String className(){
        return  "cn.DawnT0wn.Annotation.Demo1";
    }
 
    public String methodName(){
        return "show1";
    }
}
```

`Anno1Impl `实现了`Anno1`注解（接口），并且复写了`Anno1`中的两个方法，返回了使用`Anno1`注解时两个属性的值；
`anno.className()`调用的`className()`方法就相当于是调用的`Anno1Impl `中的`className()`方法；`anno.methodName()`同理

## 注解案例

参考下面的参考链接文章



参考链接

http://1.15.187.227/index.php/archives/516/

https://blog.csdn.net/qq1404510094/article/details/80577555

