# 前置知识

漏洞是出在SpringCloud Function的RoutingFunction功能上，其功能的目的本身就是为了微服务应运而生的，可以直接通过HTTP请求与单个的函数进行交互，同时为spring.cloud.function.definition参数提供您要调用的函数的名称。

![image-20230719112725977](images/1.png)

来实现一个反转字符串的函数，并用Component将其注册为Spring的组件，添加Bean注解，函数类型为Function

接下来通过spring.cloud.function.definition参数提供调用的函数的名称 

![image-20230719113345609](images/2.png)



![image-20230719113326867](images/3.png)

在RoutingFunction中进行了调用

![image-20230719113311971](images/4.png)

或者可以直接通过，这样的方式来调用

```
@Component
public class MyFunction implements Function<String, String> {
    @Override
    public String apply(String input) {
        // 在这里定义函数的逻辑
        return "Hello, " + input + "!";
    }
}
```

spring.cloud.function.definition如下

```
spring:
  cloud:
    function:
      definition: myFunction

```

然后调用myFunction的apply方法，Spring Cloud Function定义的函数（Function Bean）不是通过`spring.cloud.function.definition`属性来暴露的，因此无法通过这个属性来直接访问Spring Cloud Function中自定义的函数。

`spring.cloud.function.definition`属性是用于在Spring Cloud Function应用程序中指定要调用的函数的名称或Bean名称。它通常用于指定要调用的函数名称，并从函数目录（FunctionCatalog）中查找对应的函数，然后执行函数的调用。

自定义的函数应该是使用`@Bean`注解或通过`java.util.function`接口的实现类来定义的，而不是通过`spring.cloud.function.definition`属性暴露的。这样的函数可以在应用程序中直接使用，或者被`FunctionCatalog`扫描并注册为可用的函数。

如果你想要通过HTTP端点来访问自定义的函数，可以创建一个Controller，并在其中注入`FunctionCatalog`，然后通过调用`FunctionCatalog`的`lookup()`方法来获取函数并进行调用。

对于Spring Cloud Function，添加Bean注解后可以直接通过HTTP端点访问

![image-20230719115011170](images/5.png)

# 漏洞复现

访问functionRouter路由器，添加header

```
spring.cloud.function.routing-expression:T(java.lang.Runtime).getRuntime().exec("open -a Calculator")
```

![image-20230719104138252](images/6.png)

# 漏洞分析

补丁的commit在如下地址

https://github.com/spring-cloud/spring-cloud-function/commit/0e89ee27b2e76138c16bcba6f4bca906c4f3744f

![image-20230719104314473](images/7.png)

![image-20230719104417203](images/8.png)

对于Header传进来的参数采用headerEvalContext而不是StandardEvaluationContext来解析表达式

```
private final SimpleEvaluationContext headerEvalContext = SimpleEvaluationContext
			.forPropertyAccessors(DataBindingPropertyAccessor.forReadOnlyAccess()).build();
```

![image-20230719104544447](images/9.png)

可以断在RoutingFunction的functionFromExpression方法上，对于这个方法的调用

![image-20230719135204066](images/10.png)

全部都在RoutingFunction的route方法

![image-20230719135230983](images/11.png)

这个类是实现了Function接口的，可以通过Spring Cloud Function调用了其apply方法，然后调用route方法

接下来就是要去找到这个类绑定的Bean在哪个地方

![image-20230719140703778](images/12.png)

在RoutingFunction类中定义了Function_NAME为functionRouter

![image-20230719140742623](images/13.png)

在ContextFunctionCatalogAutoConfiguration找到了这个Bean注册的地方

我们可以通过HTTP端点来访问这个RoutingFunction的apply方法的调用，即访问`http://127.0.0.1:8080/functionRouter`

根据断点的堆栈情况可以看到其实对于请求的处理最开始在FunctionController的form方法

![image-20230719141010753](images/14.png)

FunctionController是Spring Cloud Function自己定义的一个处理器，对于所有的请求进行拦截，实现了多个Post方法的拦截，通过consumes设置不同的方法来进行处理

![image-20230719141152693](images/15.png)

即不同的Content-Type，对于设置了consumes的PostMapping优先级更高，否则调用默认的post方法

![image-20230719141238950](images/16.png)

在form方法中，如果请求是文件上传则会进入if判断，否则直接调用processRequest，传入request的wrapper，和post参数

`StandardMultipartHttpServletRequest`是Spring Framework中提供的一个类，用于处理`multipart/form-data`类型的HTTP请求。它继承自`AbstractMultipartHttpServletRequest`，是`MultipartHttpServletRequest`的实现之一。

当客户端使用`enctype="multipart/form-data"`提交表单时，通常用于上传文件等情况，服务端需要处理这样的请求，并从中获取表单字段和上传的文件数据。

![image-20230719141729313](images/17.png)

程序会判断当前请求是否为RoutingFunction，并将请求的内容和Header头编译成Message带入到FunctionInvocationWrapper.apply方法中

![image-20230719142428267](images/18.png)

调用doApply方法，传入数据

![image-20230719142622118](images/19.png)

functionRouter到目标target就是RoutingFunction，接下来调用RoutingFunction的apply方法

![image-20230719142758690](images/20.png)

调用route

![image-20230719142850598](images/21.png)

input是边缘撑Message传过来的，因为在方法中定义的function默认为null，进入if

![image-20230719142938598](images/22.png)

判断值来进入不同的分支，header头是可控的，而且functionFromExpression里面可以解析Spel表达式，解析这个heder的内容

![image-20230719143245915](images/23.png)

这里的evalContext是StandardContext，没有做任何处理，可以直接解析Spel表达式达到命令注入的目的

# 补丁分析

![image-20230719143814403](images/24.png)

1. 声明一个SimpleEvaluationContext，专用作来自header的SpEL的解析 ；
2. 新增一个布尔变量isViaHeader，用于标记当前Expression是否来自Header；
3. 如果是从Header中获取的spring.cloud.function.routing-expression表达式，isViaHeader为true ；
4. isViaHeader为true时，expression.getValue指定使用headerEvalContext

修复就是采用Spel直接提供的一个SimpleEvaluationContext替换StandardContext，SimpleEvaluationContext旨在仅支持SpEL语言语法的一个子集，不包括 Java类型引用、构造函数和bean引用；而StandardEvaluationContext是支持全部SpEL语法的



参考链接：

https://github.com/spring-cloud/spring-cloud-function/commit/0e89ee27b2e76138c16bcba6f4bca906c4f3744f#diff-01d5affef57305a3034bfb48185f34ae3d21f15e7f389851ac67035f7bd0dc7a

https://www.cnblogs.com/wh4am1/p/16062306.html

https://blog.csdn.net/weixin_44112065/article/details/123965187