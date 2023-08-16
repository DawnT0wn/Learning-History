# php序列化函数闭包详解

最近YII爆出了几条新链子,最后一个链子在CTF中见到几次了,但是对于那个POC最后有一个include还有有点疑惑,最近看到原作者给出了一个解释

## 函数的定义

自定义函数可以分为普通的函数和匿名函数,而匿名函数又称作为闭包函数

回调函数的方式可以用call_user_func

不过匿名函数可以这么定义

```
$a=function ()
{
    phpinfo();
};
```

![image-20210926205754797](images/1.png)

但是普通的函数就不行了,会出现报错

![image-20210926205740145](images/2.png)

有人会想到,那直接去定义一个函数,但是在序列化中`$this->source->generate`这种调用方式是不能直接调用自函数的,他针对的操作是变量,那么我们第一种定义的匿名函数就可以使用了

在`call_user_func($this->source->generate, $length);`第二个参数不可控的情况下,如果存在\Opis\Closure依赖的话,就可以来调用如下匿名函数,他是通过Closure类来实现的,从而实现RCE(在序列化中)

```
$a=function ()
{
    phpinfo();
};
```

当然，有一种构造函数的方式，`create_function`， 这在php7.2 后就被摒弃了

```
$a = create_function('', 'echo 1;');
```

用如下代码来做一个区分

```
<?php
$a = function () {
    echo 123;
};
var_dump($a);
$b = create_function('', 'echo 1;');
var_dump($b);

```

![image-20210926210508131](images/3.png)

当我们把定义的闭包函数赋给一个变量的时候，php会将其自动转化为内置类Closure的实例。

而`create_function创建的是一个 lambda类型的匿名函数，`

![image-20210926210733706](images/4.png)

他的返回值如下定义，

![image-20210926210748789](images/5.png)

不过这里不研究 `create_function`。

## Closure的序列化

从上图可以看出,当把定义的匿名函数赋值给一个变量的时候,php会将其转化为内置类Closure的实例

既然是一个类,那就可以序列化和反序列化了,不过当我们直接利用serialize的时候会报错

```
如下代码运行时会报错
<?php
$a = function () {
    phpinfo();
};
echo serialize($a);
```

![image-20210927180508236](images/6.png)

这是因为PHP并没有提供序列化闭包的操作,不过`opis/closure` 帮助我们实现了闭包的序列化。

可以在github上面下载,也可以用composer直接安装

```
composer require opis/closure
```

![image-20210928234815501](images/7.png)

不过我yii这个文件下已经有了closure

虽然这样也可以调用匿名函数

```
$a = function () {
    echo 123;
};

call_user_func($a);
```

但是在序列化中`call_user_func($this->source->generate, $length);`不能直接控制`$this->source->generate=$a`,因为这样在序列化时得不到我们匿名函数中的代码

因为在php中,对闭包的序列化需要通过\Opis\Closure这个的Closure类来实现,不然的话在序列化后的值就是空值

这是利用了Closure类序列化得到的结果

![image-20210926232430636](images/8.png)

这是没有利用Closure类得到的结果,发现defaultValue的值是空值

![image-20210926232514740](images/9.png)

这就是我们为什么在利用的时候要这么去写exp的原因

![image-20210926232640952](images/10.png)

至于为什么要用autoload.php,而不是直接去include('functions.php')

直接include('functions.php')

![image-20210927180837648](images/11.png)

会找不到SerializeableClosure类

而autoload.php如下

![image-20210927162539210](images/12.png)

听名字就知道autoload.php可以自动加载一些东西

原因在于这个`spl_autoload_register`

这个函数和`__autoload`函数有异曲同工之妙

当我们实例化一个未定义的类时，就会触发此函数

来看看这两个函数

**一、__autoload**

这是一个自动加载函数，在PHP5中，当我们实例化一个未定义的类时，就会触发此函数。看下面例子：

printit.class.php：

```
<?php
class PRINTIT {
 function doPrint() {
 echo 'hello world';
 }
}
?>
```

index.php

```
<?
function __autoload( $class ) {
 $file = $class . '.class.php';
 if ( is_file($file) ) {
 require_once($file);
 }
}
$obj = new PRINTIT();
$obj->doPrint();?>
```

运行index.php后正常输出hello world。在index.php中，由于没有包含printit.class.php，在实例化printit时，自动调用__autoload函数，参数$class的值即为类名printit，此时printit.class.php就被引进来了。

在面向对象中这种方法经常使用，可以避免书写过多的引用文件，同时也使整个系统更加灵活。

**二、spl_autoload_register()**

再看spl_autoload_register()，这个函数与__autoload有与曲同工之妙，看个简单的例子：

```
<?
function loadprint( $class ) {
 $file = $class . '.class.php';
 if (is_file($file)) {
 require_once($file);
 }
}
spl_autoload_register( 'loadprint' );
$obj = new PRINTIT();
$obj->doPrint();?>
```

将autoload换成loadprint函数。但是loadprint不会像autoload自动触发，这时spl_autoload_register()就起作用了，它告诉PHP碰到没有定义的类就执行loadprint()。

这里我们需要autoload这个文件下的spl_autoload_register()

了解了这些,回到正题,我们利用了\Opis\Closure\serialize的Closure类来实现了对闭包的序列化,那为什么当反序列化的时候可以直接利用serialize函数呢

来观察一下闭包序列化后的内容

```
<?php
include("closure/autoload.php");
$a=function ()
{
    system('dir');
};
$b = \Opis\Closure\serialize($a);
echo $b;
```

![image-20210927163824215](images/13.png)

平常我们接触到的序列化开头都是`O:`,但是这里却是`C`:

这后面的内容可以在https://www.yuque.com/docs/share/3f64fe8a-3c54-4469-9d90-2e51ec990fe9?#找到,师傅打着断点一路讲的很清楚



参考链接:

https://www.jb51.net/article/88816.htm

https://www.yuque.com/docs/share/3f64fe8a-3c54-4469-9d90-2e51ec990fe9?#

