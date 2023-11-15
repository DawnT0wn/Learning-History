# 前言

在java中，我们经常看到一些ObjectInputStream，FileInputStream，BufferrInputStream，InputStream等等，让人对java io对东西整的头晕，特来学习，把这些东西做一个区分

# 流的基本概念

电脑上的数据存储分为外存，内存，缓存。

硬盘，U盘等属于外存，然后电脑有内存条，属于内存，缓存上存在CPU里面的

不同的存储，读取速度肯定也不相同，外存最慢，其次内存，最快的是缓存

这里总结从外存读取数据到内存以及将数据从内存写到外存中

对于输出流和输入流的理解：

- 将idea的东西输出到文件，叫做输出流
- 将文件内容输入到idea，称为输入流

可能根据参考系不同，对这个理解不同，但是我觉得这个输入输出是以idea为参考系的

# 流分类

## 根据传输数据分类

根据传输数据不同，分为字节流和字符流

|        | 字节流       | 字符流 |
| ------ | ------------ | ------ |
| 输出流 | OutputStream | Writer |
| 输入流 | InputStream  | Reader |

上面的也是 Java IO流中的四大基流。这四大基流都是抽象类，其他流都是继承于这四大基流的。 

1) 字节流：数据流中最小的数据单元是字节 

2) 字符流：数据流中最小的数据单元是字符， Java中的字符是Unicode编码，一个字符占用两个字节（无论中文还是英文都是两个字节）

## 根据功能分类

根据功能分为节点流和包装流

- 节点流：可以从或向一个特定的地方(节点)读写数据，直接连接数据源。如最常见的是文件的FileReader，还可以是数组、管道、字符串，关键字分别为ByteArray/CharArray，Piped，String。
- 处理流（包装流）：并不直接连接数据源，是对一个已存在的流的连接和封装，是一种典型的装饰器设计模式，使用处理流主要是为了更方便的执行输入输出工作，如PrintStream，输出功能很强大，又如BufferedReader提供缓存机制，推荐输出时都使用处理流包装。

一个流对象经过其他流的多次包装，称为流的链接。

注意：一个IO流可以即是输入流又是字节流又或是以其他方式分类的流类型，是不冲突的。比如FileInputStream，它既是输入流又是字节流还是文件节点流

## 一些特别的的流类型

- 转换流：转换流只有字节流转换为字符流，因为字符流使用起来更方便，我们只会向更方便使用的方向转化。如：InputStreamReader与OutputStreamWriter。
- 缓冲流：有关键字Buffered，也是一种处理流，为其包装的流增加了缓存功能，提高了输入输出的效率，增加缓冲功能后需要使用flush()才能将缓冲区中内容写入到实际的物理节点。但是，在现在版本的Java中，只需记得关闭输出流（调用close()方法），就会自动执行输出流的flush()方法，可以保证将缓冲区中内容写入。
- 对象流：有关键字Object，主要用于将目标对象保存到磁盘中或允许在网络中直接传输对象时使用（对象序列化）

# 自己对使用的一些理解

## 例一

在了解了上面的流后，我们主要是掌握其使用，在java中，我们命令执行的结果是没有回显的，但是呢，命令执行后返回的是一个Proccess对象，我们可以获取他的字节流，然后通过缓冲流挨个打印

```
package test;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;

public class io {
    public static void main(String[] args) throws Exception{
        Process process = Runtime.getRuntime().exec("ls");
        InputStream inputStream = process.getInputStream();
        InputStreamReader inputStreamReader = new InputStreamReader(inputStream);
        BufferedReader bufferedReader = new BufferedReader(inputStreamReader);
        String line;
        while ((line = bufferedReader.readLine())!=null){
            System.out.println(line);
        }
    }
}
```

先来解释一下上面的代码，首先我们获取了命令执行的字节输入流，但是我们最后打印的时候需要打印字符串，所以我们需要再给它转化成字符输入流，但是我们最后打印的时候需要用缓冲流把命令执行没一行的结果打印出来，所以再把字符输入流放进缓冲流去，最后通过while循环读，然后打印，直到结束

除此之外，也可以用StringBuffer

```
package test;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;

public class T0WN {
    public static void main(String[] args) throws Exception{
        Process p;
        String cmd = "ls";

        try {
            p = Runtime.getRuntime().exec(cmd);
            InputStream fis = p.getInputStream();//取得命令结果的输出流
            InputStreamReader isr = new InputStreamReader(fis);//用一个读输出流类去读
            BufferedReader br = new BufferedReader(isr);//用缓冲器读行
            String line = null;
            StringBuffer buffer = new StringBuffer();
            while ((line = br.readLine())!=null){
                buffer.append(line).append("\n");
            }
//            throw new Exception(buffer.toString());
            System.out.println(buffer.toString());
//            while ((line = br.readLine()) != null) {//直到读完为止
//                System.out.println(line);
//            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

最后再toString转换一下

## 例二

在反序列化的时候，我们经常看到一个ByteArrayInputStream

```
byte[] b = Base64.getDecoder().decode(data);
InputStream bis = new ByteArrayInputStream(b);
ObjectInputStream ois = new ObjectInputStream(bis);
ois.readObject();
```

首先Base64.getDecoder().decode(data);返回的是一个字节数组，我们再把这个字节数组放到一个字节输入流里面去，因为反序列化是用的对象输入流，所以再把这个字节流放到对象流里面去，最后调用readObject就可以反序列化我们base64编码的类了

## 例三

将类转换成字节数组

```
InputStream inputStream = new FileInputStream("/Users/DawnT0wn/IdeaProjects/Spring/src/main/java/ClassLoader/Sun.class");
ByteArrayOutputStream bos = new ByteArrayOutputStream();
int in = 0;
while ((in = inputStream.read()) !=-1 ){
    bos.write(in);
}
byte[] bytes = bos.toByteArray();
```

读一个class文件，因为最后是输出到一个字节数组里面去，所以实例化一个字节输出流对象，这个构造器为空或者为一个字节大小

这里就没有设置初始值，对里面输出流对内容需要我们用InputStream.read挨着读字节流写入ByteArrayOutputStream对象里面去（利用write方法）

最后，虽然我们写入的是字节，但是对于这个输出流，对象还是ByteArrayOutputStream，所以最后我们转化为字节数组需要调用一次toByteArray

# 总结

其实总的来说，对于I/O类型的东西，我们主要是要分清是输出流还是输入流，接下来就是分清是字节流还是字符流，我们究竟需要什么，是字符的话就用Reader.readline，是字节的话就用InputStream.read，另外还需要看看各个IO对象需要的参数类型，有些是无参的



参考链接

https://www.cnblogs.com/furaywww/p/8849850.html