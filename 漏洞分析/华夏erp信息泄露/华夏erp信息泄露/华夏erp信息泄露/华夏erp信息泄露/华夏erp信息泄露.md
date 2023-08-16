# 漏洞分析

华夏erp cms写了一个全局的filter用于身份验证

![image-20230616120529811](images/1.png)

![image-20230616120541153](images/2.png)

对于所有的url进行的判断是通过contains来实现的，如果包含doc.html，register.html，login.html等页面，不拦截，

![image-20230616120938587](images/3.png)

而verify函数也是通过pattern.match匹配的字符串

这也就成了绕过的关键，在spring中，我们用分号分割URL后，仍然可以进入到对应的controller

![image-20230616133921098](images/4.png)

这样就能访问到对应的/user/hahaha路由，因此，就可以对erp中的路由进行身份绕过

# 漏洞复现

![image-20230616134011993](images/5.png)

payload：

```
/user/getAllList;.js
```

分割符后面只要说ignoredUrl里面运行的后缀均可

