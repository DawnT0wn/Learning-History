# ǰ��

��java�У����Ǿ�������һЩObjectInputStream��FileInputStream��BufferrInputStream��InputStream�ȵȣ����˶�java io�Զ�������ͷ�Σ�����ѧϰ������Щ������һ������

# ���Ļ�������

�����ϵ����ݴ洢��Ϊ��棬�ڴ棬���档

Ӳ�̣�U�̵�������棬Ȼ��������ڴ����������ڴ棬�����ϴ���CPU�����

��ͬ�Ĵ洢����ȡ�ٶȿ϶�Ҳ����ͬ���������������ڴ棬�����ǻ���

�����ܽ������ȡ���ݵ��ڴ��Լ������ݴ��ڴ�д�������

���������������������⣺

- ��idea�Ķ���������ļ������������
- ���ļ��������뵽idea����Ϊ������

���ܸ��ݲο�ϵ��ͬ���������ⲻͬ�������Ҿ�����������������ideaΪ�ο�ϵ��

# ������

## ���ݴ������ݷ���

���ݴ������ݲ�ͬ����Ϊ�ֽ������ַ���

|        | �ֽ���       | �ַ��� |
| ------ | ------------ | ------ |
| ����� | OutputStream | Writer |
| ������ | InputStream  | Reader |

�����Ҳ�� Java IO���е��Ĵ���������Ĵ�������ǳ����࣬���������Ǽ̳������Ĵ�����ġ� 

1) �ֽ���������������С�����ݵ�Ԫ���ֽ� 

2) �ַ���������������С�����ݵ�Ԫ���ַ��� Java�е��ַ���Unicode���룬һ���ַ�ռ�������ֽڣ��������Ļ���Ӣ�Ķ��������ֽڣ�

## ���ݹ��ܷ���

���ݹ��ܷ�Ϊ�ڵ����Ͱ�װ��

- �ڵ��������Դӻ���һ���ض��ĵط�(�ڵ�)��д���ݣ�ֱ����������Դ������������ļ���FileReader�������������顢�ܵ����ַ������ؼ��ֱַ�ΪByteArray/CharArray��Piped��String��
- ����������װ����������ֱ����������Դ���Ƕ�һ���Ѵ��ڵ��������Ӻͷ�װ����һ�ֵ��͵�װ�������ģʽ��ʹ�ô�������Ҫ��Ϊ�˸������ִ�����������������PrintStream��������ܺ�ǿ������BufferedReader�ṩ������ƣ��Ƽ����ʱ��ʹ�ô�������װ��

һ�������󾭹��������Ķ�ΰ�װ����Ϊ�������ӡ�

ע�⣺һ��IO�����Լ��������������ֽ����ֻ�����������ʽ����������ͣ��ǲ���ͻ�ġ�����FileInputStream�������������������ֽ��������ļ��ڵ���

## һЩ�ر�ĵ�������

- ת������ת����ֻ���ֽ���ת��Ϊ�ַ�������Ϊ�ַ���ʹ�����������㣬����ֻ���������ʹ�õķ���ת�����磺InputStreamReader��OutputStreamWriter��
- ���������йؼ���Buffered��Ҳ��һ�ִ�������Ϊ���װ���������˻��湦�ܣ���������������Ч�ʣ����ӻ��幦�ܺ���Ҫʹ��flush()���ܽ�������������д�뵽ʵ�ʵ�����ڵ㡣���ǣ������ڰ汾��Java�У�ֻ��ǵùر������������close()���������ͻ��Զ�ִ���������flush()���������Ա�֤��������������д�롣
- ���������йؼ���Object����Ҫ���ڽ�Ŀ����󱣴浽�����л�������������ֱ�Ӵ������ʱʹ�ã��������л���

# �Լ���ʹ�õ�һЩ���

## ��һ

���˽������������������Ҫ��������ʹ�ã���java�У���������ִ�еĽ����û�л��Եģ������أ�����ִ�к󷵻ص���һ��Proccess�������ǿ��Ի�ȡ�����ֽ�����Ȼ��ͨ��������������ӡ

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

��������һ������Ĵ��룬�������ǻ�ȡ������ִ�е��ֽ���������������������ӡ��ʱ����Ҫ��ӡ�ַ���������������Ҫ�ٸ���ת�����ַ���������������������ӡ��ʱ����Ҫ�û�����������ִ��ûһ�еĽ����ӡ�����������ٰ��ַ��������Ž�������ȥ�����ͨ��whileѭ������Ȼ���ӡ��ֱ������

����֮�⣬Ҳ������StringBuffer

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
            InputStream fis = p.getInputStream();//ȡ���������������
            InputStreamReader isr = new InputStreamReader(fis);//��һ�����������ȥ��
            BufferedReader br = new BufferedReader(isr);//�û���������
            String line = null;
            StringBuffer buffer = new StringBuffer();
            while ((line = br.readLine())!=null){
                buffer.append(line).append("\n");
            }
//            throw new Exception(buffer.toString());
            System.out.println(buffer.toString());
//            while ((line = br.readLine()) != null) {//ֱ������Ϊֹ
//                System.out.println(line);
//            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

�����toStringת��һ��

## ����

�ڷ����л���ʱ�����Ǿ�������һ��ByteArrayInputStream

```
byte[] b = Base64.getDecoder().decode(data);
InputStream bis = new ByteArrayInputStream(b);
ObjectInputStream ois = new ObjectInputStream(bis);
ois.readObject();
```

����Base64.getDecoder().decode(data);���ص���һ���ֽ����飬�����ٰ�����ֽ�����ŵ�һ���ֽ�����������ȥ����Ϊ�����л����õĶ����������������ٰ�����ֽ����ŵ�����������ȥ��������readObject�Ϳ��Է����л�����base64���������

## ����

����ת�����ֽ�����

```
InputStream inputStream = new FileInputStream("/Users/DawnT0wn/IdeaProjects/Spring/src/main/java/ClassLoader/Sun.class");
ByteArrayOutputStream bos = new ByteArrayOutputStream();
int in = 0;
while ((in = inputStream.read()) !=-1 ){
    bos.write(in);
}
byte[] bytes = bos.toByteArray();
```

��һ��class�ļ�����Ϊ����������һ���ֽ���������ȥ������ʵ����һ���ֽ�������������������Ϊ�ջ���Ϊһ���ֽڴ�С

�����û�����ó�ʼֵ���������������������Ҫ������InputStream.read���Ŷ��ֽ���д��ByteArrayOutputStream��������ȥ������write������

�����Ȼ����д������ֽڣ����Ƕ�������������������ByteArrayOutputStream�������������ת��Ϊ�ֽ�������Ҫ����һ��toByteArray

# �ܽ�

��ʵ�ܵ���˵������I/O���͵Ķ�����������Ҫ��Ҫ��������������������������������Ƿ������ֽ��������ַ��������Ǿ�����Ҫʲô�����ַ��Ļ�����Reader.readline�����ֽڵĻ�����InputStream.read�����⻹��Ҫ��������IO������Ҫ�Ĳ������ͣ���Щ���޲ε�



�ο�����

https://www.cnblogs.com/furaywww/p/8849850.html