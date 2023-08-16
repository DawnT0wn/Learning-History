# 什么是RASP

RASP被称为运行时应用自我保护，在2014年的时候，Gartner引入了“Runtime application self-protection”一词，简称为RASP。它是一种新型应用安全保护技术，它将保护程序像疫苗一样注入到应用程序中，应用程序融为一体，能实时检测和阻断安全攻击，使应用程序具备自我保护能力，当应用程序遭受到实际攻击伤害，就可以自动对其进行防御，而不需要进行人工干预。

RASP的检测和保护功能是在应用程序运行的系统上运行的，它拦截从应用程序到系统的所有调用，确保它们是安全的，并直接在应用程序内验证数据请求

RASP不但能够对应用进行基础安全防护，由于一些攻击造成的应用程序调用栈调用栈具有相似性，还能够对0day进行一定的防护。

除此之外，利用 RASP 也能够对应用打虚拟补丁，修复官方未修复的漏洞。或者对应用的运行状态进行监控，进行日志采集。

# WAF与RASP对比

WAF是基于特征进行过滤的，主要是利用规则进行匹配，而RASP是基于上下文的，对攻击进行精确的识别和拦截，相比于WAF来说，RASP的误报率低

用一个sql注入的例子来论证

攻击者对url为`http://http.com/index.do?id=1`进行测试，一般情况下，扫描器或者人工测试sql注入都会进行一些sql语句的拼接，来验证是否有注入，会对该url进行大量的发包，发的包可能如下：

```
http://xxx.com/index.do?id=1' and 1=2--
```

但是应用程序本身已经在程序内做了完整的注入参数过滤以及编码或者其他去危险操作，实际上访问该链接以后在数据库中执行的sql语句为：

```
select id,name,age from home where id='1 \' and 1=2--'
```

这种情况下，是不会造成sql注入的，但是WAF是基于规则去进行拦截，这种payload肯定会被WAF拦截，所以会导致误报率大大地提高，但是对于RASP来说，RASP技术可以做到程序底层拼接SQL到数据库查询之前进行拦截，也即是在sql预编译的时候，RASP在发送之前将其拦截进行检测，如果没有危险操作，则放行，不会影响程序本身的功能。如果存在恶意攻击，则直接将恶意攻击的请求进行拦截或净化参数。

# RASP实现

市场上现在有很多rasp软件，比如说百度的openrasp（这个软件说开源的），还有之前的onerasp，以及灵蜥，还有奇安信的云锁

但是我们还是需要去了解RASP是怎么实现的，在JAVA，php，.net等不同的情况下，这次主要是来学习Rasp在java中的应用

java中实现rasp是通过java agent（Agent本质是java中的一个动态库，利用JVMTI暴露的一些接口实现的）

在之前，已经学习过了一点基础的agent编写， 包括静态和动态的agent探针植入，以阅读一个简单的开源项目来学习，接下来以OGNL表达式注入为例，来看看实现一个Java的rasp以防止OGNL注入，

项目地址在：https://github.com/xbeark/javaopenrasp

这是一个静态的agent

![image-20230717222526797](images/1.png)

主要实现的是premain方法，这个方法会在被注入agent的JVM的main方法之前执行，在此之前，首先会调用init函数，对config进行初始化

![image-20230717222648464](images/2.png)

readconfig函数如下

```
public static String readConfig(String filename) {

   BufferedReader reader = new BufferedReader(new InputStreamReader(Config.class.getResourceAsStream(filename)));
   StringBuilder sb = new StringBuilder();
   String line = null;
   try {
      while ((line = reader.readLine()) != null) {
         sb.append(line.trim());
      }
   } catch (IOException e) {
      e.printStackTrace();
   }
   Console.log(sb.toString());
   return sb.toString();

}
```

从main.config里面读取内容，这个文件放在resources资源目录下

![image-20230718191956999](images/3.png)

接下来是对数据的处理，将这个json转化成map对象数组，遍历数组，通过map.get获取对应的moduleName，loadClass等值放到一个临时的map中最后put到moduleMap，在moduleMap形成一个通过moduleName存储对应mdule的键值对

回到Agent类，接下来是通过ClassTransformer进行我们想要的操作

![image-20230717223514654](images/4.png)

其实就是通过className和config里面的moduleName进行对比，过滤出关注的类，通过asm对相关字节码进行修改，也可以用javassist。这里实现了多个类，采用了asm的方式，通过实现ClassVistor，重写visitMethod方法，实现对应的修改逻辑

```
public MethodVisitor visitMethod(int access, String name, String desc,
                                 String signature, String[] exceptions)
                                 
visitMethod 方法在 ASM 的类访问器（ClassVisitor）中被调用，用于访问和处理类中的每个方法。

当你使用 ASM 解析或修改一个类时，你需要创建一个自定义的 ClassVisitor 对象，并在其中重写 visitMethod 方法。然后，通过调用类的 accept 方法，并传入你的 ClassVisitor 对象，来触发对类的访问和处理。

在解析或修改类的过程中，当 ASM 遍历到每个方法时，会调用 visitMethod 方法。你可以在这个方法中执行相应的操作，例如获取方法的名称、描述符，访问和修改方法的字节码指令等。

一个最简单的使用实例
ClassReader classReader = new ClassReader("com.example.MyClass");
ClassWriter classWriter = new ClassWriter(ClassWriter.COMPUTE_MAXS);
ClassVisitor classVisitor = new MyClassVisitor(classWriter);
classReader.accept(classVisitor, ClassReader.SKIP_FRAMES);
byte[] modifiedClass = classWriter.toByteArray();
```

以下是 `visitMethod` 方法的参数说明：

- `access`：方法的访问修饰符和标志，表示方法的属性，例如 `ACC_PUBLIC`、`ACC_PRIVATE`、`ACC_STATIC` 等。
- `name`：方法的名称。
- `desc`：方法的描述符，描述方法的参数类型和返回类型。
- `signature`：方法的泛型签名（如果存在）。
- `exceptions`：方法可能抛出的异常类型数组。



Javassist更趋向于直接操作类和方法，相比之下，ASM采用基于访问者（Visitor）模式的编程模型，你需要实现访问者接口，并在访问者中处理不同的字节码指令。这种模型更灵活和强大，特别适合对字节码进行复杂的操作和转换。

实现中使用了使用了 Map 将关注的类进行保存，一旦命中我们关心的类，便利用反射生成 asm 的ClassVisitor ，重写visitMethod，使用 asm 操作字节码，进行探针织入，最终返回修改后的字节码。

接下来以OGNL为例

当命中了config中的ognl/Ognl这个moduleName的时候，对OgnlVisitor通过反射进行实例化

![image-20230717224528395](images/5.png)

接下来会触发visitMethod方法

我们可以判断当前访问的方法是否为目标方法（"parseExpression" 方法，并且方法描述符为 "(Ljava/lang/String;)Ljava/lang/Object;"），即参数是String，返回类型是Object。如果是目标方法，则创建一个自定义的 `MethodVisitor` 对象（在这里是 `OgnlVisitorAdapter`），用于访问和修改该方法的字节码指令。

![image-20230717230612129](images/6.png)

## 跟踪分析

主要来看Visitor这边的执行流程

![image-20230731230252427](images/7.png)

每一个类加载的时候都会毁掉ClassFileTransformer的transform方法，而moudleMap中根据类名设置键值，当加载的类是其中之一的时候，就会进入if内的语句进行执行。

这是ASM的标准写法，通过 `accept` 方法将 `ClassVisitor` 与 `ClassReader` 关联，从而启动字节码解析和访问过程，其中Visitor是通过反射创建的，因为是Ognl这个类，所以触发的是OgnlVisitor这个类，遍历解析到启动重写的visitMethod方法

遍历Ognl类将调用的方法

![image-20230731231020175](images/8.png)

当调用类parseExpression方法，并且传入的是String类型的参数，返回是Object类型的时候，触发if内语句，这里要知道的时候Ognl表达式解析流程

```
public static void main(String[] args) throws Exception{
    OgnlContext ognlContext = new OgnlContext();
    Ognl.getValue("@java.lang.Runtime@getRuntime().exec('open /System/Applications/Calculator.app')",ognlContext,ognlContext.getRoot());
}
```

虽然是通过getValue开始解析的

![image-20230731230911977](images/9.png)

但是最后还是会触发parseExpression方法去解析表达式

![image-20230731230949033](images/10.png)

接受的是一个String参数，返回的是Object参数，接下来就是OgnlVisitorAdapter类，这个继承自AdviceAdapter，AdviceAdapter类提供了一部分钩子函数，在某个时候就会调用，而实例化它的时候会遍历这些钩子函数

比如onMethodEnter，就是在才进入方法的时候进行调用，也就是我们会在parseExpression开头对着干方法进行修改

![image-20230731231139075](images/11.png)

这段ASM代码的意思就是，插入了一个if语句，这里我之前将修改过后的类进行写到了一个新的class，可以直接看到修改后的样子与原来的差别，当OgnlFilter的staticFilter方法返回false的时候，就会抛出异常

![image-20230731231416577](images/12.png)

接下来来看到staticFilter

![image-20230731231729621](images/13.png)

获取了mode，通过switch来选择需要进行的操作，这里是黑名单过滤，在config里面写好了的

![image-20230731231841040](images/14.png)

遍历黑名单的类，如果存在的话，在case black中会返回false

![image-20230731232235650](images/15.png)

其实如果不在这里阻止的话，其实也可以，因为当我们把命令执行的时候hook掉，或者说设置黑名单的话，其实OGNL最后执行命令的实质还是调用了exec，然后调用ProcessBilder，当实例化这个的时候又会去回掉transform，进行下一轮的过滤

![image-20230731232415306](images/16.png)

这种动态防御的技术通过agent的方式实现，根据上下文进行检测，会比waf更精确，但是也要考虑到，在多个请求发生的时候，这种方式的响应速度



最后，如果用动态注入agent的话，就用agentmain动态地注入到JVM中，在修改后，重新加载类，这种方式可以在spring和tomcat这种一直在运行的时候对程序进行保护，而不是premain那样只在main方法执行前执行一次

![image-20230731232734283](images/17.png)

但是这种方式，我发现，如果我提前加载类这个类的话，其实是没有修改成功的，所以更好的还是启动的时候注入agent，但是是用agentmian去实现，不是premain



参考链接：

https://www.freebuf.com/articles/web/197823.html

https://paper.seebug.org/330/