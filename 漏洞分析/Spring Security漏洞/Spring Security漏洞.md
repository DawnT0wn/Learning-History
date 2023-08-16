# CVE-2022-31692 权限绕过

环境：https://github.com/SpindleSec/cve-2022-31692

Spring Security的受影响版本在

- 5.6.0 <= Spring Security <= 5.6.8
- 5.7.0 <= Spring Security <= 5.7.4

如果存在通过forward转发路由的时候，并且转发的路由存在权限验证，返回forward转发结果的路由不存在权限验证，则存在漏洞

## 漏洞复现

![image-20230807141510040](images/1.png)

直接访问admin

![image-20230807141540400](images/2.png)

访问forward，重定向到admin路由

<img src="/Users/DawnT0wn/Library/Application Support/typora-user-images/image-20230807141745341.png" alt="image-20230807141745341" style="zoom:50%;" />

返回adminpage模板（springboot的controller返回值可以直接与模板文件绑定）

![image-20230807142343393](images/3.png)

![image-20230807141614835](images/4.png)

## 漏洞分析

### admin路由验证流程

![image-20230807161306021](images/5.png)

security的权限认证在AuthorizationFilter的doFilterInternal方法中

![image-20230807155150673](images/6.png)

跟进check

![image-20230807160034640](images/7.png)

遍历config中添加的几个路径

![image-20230807160457354](images/8.png)

/admin的requestMatcher和request中的/admin匹配，退出循环，获取其中的entry（AuthorityAuthorizationManager），并调用相应的check方法

![image-20230807161434354](images/9.png)

![image-20230807161708112](images/10.png)

此时是anonymousUser

![image-20230807161801468](images/11.png)

此时grantedAuthority是ROLE_ANONYMOUS，而authority是ROLE_ADMIN，所以返回false

![image-20230807162450553](images/12.png)

返回的desion的granted是false，在`doFilterInternal`中抛出权限错误。

### forward路由验证流程

对AuthorizationFilter的doFilterInternal方法的调用在OncePerRequestFilter的doFilter方法

![image-20230807163600323](images/13.png)

在第一次访问/forward路由的时候，hasAlreadyFilterAttribute为false是，进入else分支，将hasAlreadyFilterAttribute设置为true，会去调用每一个filter的doFilterInternal，仍然会进入到AuthorizationFilter的doFilterInternal方法，因为设置的antMatchers("/forward").permitAll()，所以在check方法中匹配到/forward路由的时候直接跳转到permitAllAuthorzationManager会直接放行

![image-20230807164308127](images/14.png)

返回英国AuthorizationDecison，设置granted为true

![image-20230807164438237](images/15.png)

![image-20230807164500055](images/16.png)

通过权限验证，在Controller返回forward:/admin后，spring的解析来到了ApplicationDispatcher到processRequest方法

![image-20230807164539480](images/17.png)

![image-20230807164723483](images/18.png)

这次的请求又来到了OncePerRequestFilter的doFilter方法

![image-20230807164821905](images/19.png)

因为上次已经将hasAlreadyFilteredAttribute设置为true，所以调用filterChain的doFilter方法，而不会去调用doFilterInternal方法了

也就不会再去触发权限认证了，所以这次访问/admin路由就绕过了权限认证，最后返回adminpage渲染结果，即adminpage.html

## 漏洞修复

禁用`OncePerRequestFilter`功能或保证访问`/forward`跳转的目标网页所需的权限小于访问`/forward`的权限。

官方的修复方案是在`AuthorizationFilter.java`中新增了一个判断, 判断是否在**当前**`request`中使用过。

```
/*
* verify whether the filter has been set observeOncePerRequest = true and applied
*/
if (this.observeOncePerRequest && isApplied(request)) {
    chain.doFilter(request, response);
    return;
} 

if (skipDispatch(request)) {
    chain.doFilter(request, response);
    return;
}

String alreadyFilteredAttributeName = getAlreadyFilteredAttributeName();
request.setAttribute(alreadyFilteredAttributeName, Boolean.TRUE);
try {
    this.authorizationManager.verify(this::getAuthentication, request);
    chain.doFilter(request, response);
}
finally {
    request.removeAttribute(alreadyFilteredAttributeName);
	}
}
```

# CVE-2022-22978 认证绕过漏洞

https://github.com/XuCcc/VulEnv/tree/master/springboot/cve_2022_22978

vulhub也有这个环境

当Spring-security使用 RegexRequestMatcher 进行权限配置，由于RegexRequestMatcher正则表达式配置权限的特性，正则表达式中包含“.”时，未经身份验证攻击者可以通过构造恶意数据包绕过身份认证。

**影响版本**

Spring Security 5.5.x < 5.5.7

Spring Security 5.6.x < 5.6.4

## 漏洞复现

```http
GET /admin/1%0d%0a HTTP/1.1
Host: 127.0.0.1:8080
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9
Cookie: JSESSIONID=E8E29D0409C6C153D1C825E11A344082
Connection: close
```

![image-20230807180734754](images/20.png)

## 漏洞分析

![image-20230807180436852](images/21.png)

![image-20230807180427182](images/22.png)

对/admin路由下，任意路径进行匹配，在访问/admin/{name}接口时，需要认证才能访问

spring-security-web-5.6.3.jar包中，org.springframework.security.web.uti.matcher.RegexRequestMatcher#matchers中

![image-20230807180850900](images/23.png)

request.getServletPath()会对字符解码 并且会将;之后的字符到/字符删除，随后通过getServletPath获取URL，尝试提取？后的参数进行拼接，然后使用正则表达式匹配。

其中HTTPServletRequest中对URL路径的几种解析方法。

```
request.getRequestURL()：返回全路径；
request.getRequestURI()：返回除去Host（域名或IP）部分的路径；
request.getContextPath()：返回工程名部分，如果工程映射为/，则返回为空；
request.getServletPath()：返回除去Host和工程名部分的路径；
request.getPathInfo()：仅返回传递到Servlet的路径，如果没有传递额外的路径信息，则此返回Null；
```

对于正则表达式，在正则表达式中元字符“.”是匹配除换行符（\n、\r）之外的任何单个字符，在java中的正则默认情况下“.”也同样不会包含\n、\r字符，所以RegexRequestMatcher在进行正则匹配时不会处理\n、\r，所以对于匹配来说，可以用\r\n这种方式绕过

# CVE-2023-34034 路径匹配漏洞

补丁：https://github.com/spring-projects/spring-security/commit/7813a9ba26e53fe54e4d2ec6eb076126e8550780



# CVE-2023-34035 鉴权规则错误配置风险

补丁：https://github.com/spring-projects/spring-security/commit/df239b6448ccf138b0c95b5575a88f33ac35cd9a





参考链接：

https://www.freebuf.com/vuls/349347.html

https://www.freebuf.com/vuls/343980.html