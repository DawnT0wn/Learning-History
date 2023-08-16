# K8s基础

## 为什么需要Kubunetes

虽然Docker为容器化为多应用程序提供了开放标准，但是随着容器的增多，也出现了一系列问题：

- 单机不足以支持更多的Docker容器
- 分布式环境下的容器怎么相互通信
- 如何协调和调度这些容器
- 如何在升级应用程序时不会中断服务
- 如何监视应用程序的运行状态
- 如何批量重启容器里的程序

为了解决这一系列问题，Kubunetes应运而生

要了解一个东西，必须先去了解其架构，当谈论你kubernetes的时候，应该去了解其关键的组件：Master节点，Node节点，Pod

## Master节点

K8s集群的控制节点，负责整个集群的管理和控制，包含以下组件：

- API Server（API服务器）：API Server上Kubernentes集群的主要入口点，用于管理和操作整个集群。它用来接收来自用户和其他组件的API请求，并将其转发到适当的组件进行处理。可以理解为API Server根据用户的具体请求，去通知其他组件干活。
- Scheduler（调度器）：Scheduler负责根据预定义的策略将新创建的Pod分配到可用的Node节点上。它考虑到节点的资源使用情况，亲和性，互斥性等因素来进行调度决策。即当用户部署服务时，Scheduler会选择合适的Worker Node来部署。
- Controller Manager（控制器管理器）：Controller Manager上一个集中式控制器，负责处理集群级别的后台任务，如复制控制器（Replication Controller）、水平自动伸缩（Horizontal Pod Autoscaler）等。它监控集群状态，并确保系统达到所需的状态。Controller负责监控和调整在Worker Node上部署的服务的状态，比如用户要求A服务部署2个副本，那么当其中一个服务挂了的时候，Controller会马上调整，让Scheduler再选择一个Worker Node重新部署服务。
- etcd（分布式键值存储）：etcd是kubernetes集群中的一种高可用性的分布式键值存储系统。它用于存储集群的配置信息、状态信息以及持久化存储的数据。K8s钟仅API Server才具备读写权限，其他组件必须通过API Server的借口才能读写数据。在K8s中有两个服务需要用到etcd来协同和配置，分别如下
  - 网络插件 flannel、对于其它网络插件也需要用到 etcd 存储网络的配置信息
  - Kubernetes 本身，包括各种对象的状态和元信息配置
  - 注意：flannel 操作 etcd 使用的是 v2 的 API，而 Kubernetes 操作 etcd 使用的 v3 的 API，所以在下面我们执行 etcdctl 的时候需要设置 ETCDCTL_API 环境变量，该变量默认值为 2

## Node节点

Kubernetes的工作节点，用于运行应用程序和容器。每个Node节点运行着一下组件：

- Kubelet（节点代理）：kubelet是运行在每个Node上的节点代理，负责与Master通信，实现集群管理的基本功能，并管理Node上的容器。它从API Server（Master Node）接收Pod的对应容器的创建请求，并根据指令在Node上启动，停止或重新启动。
- Container Runtime（容器进行时）：Worker Node的运行环境，容器运行时负责在Node节点上创建和管理容器，即安装了容器化所需的软件环境确保容器化程序能够跑起来，如Docker Engine。可以理解为装好了Docker运行环境
- Kube-proxy（代理服务）：负责为Pod提供网络代理和负载均衡服务。它维护着集群中的网络规则，并将网络流量转发到适当的Pod上

## Pod

官方对于**Pod**的解释是：

> **Pod**是可以在 Kubernetes 中创建和管理的、最小的可部署的计算单元。

​	我们一般部署的是容器，但是在K8s中，Pod才是可部署的最小单元，它可以包含一个或多个相关的容器，共享相同的网络和存储资源。Pod作为K8s调度的基本单位，被部署到Node节点上，Pod拥有自己的IP地址，同一Pod里的几个Docker可以通过localhost互相访问（好像被部署在同一机器上的Docker一样），并且共用Pod里的资源（指Docker可以挂载Pod内的数据卷）

Pod可以由多个容器组成，这些容器在逻辑上共用同一个Pod，并共享同一个生命周期和资源。这些容器可以协同工作来完成一个应用程序的不同部分和功能

Pod具有以下特点

- 生命周期：Pod作为一个整体具有相同的生命周期。当Pod被创建时，其中所有的容器一起启动，并在同一时间停止或重新启动
- 共享资源：Pod内的容器共享相同的资源，包括网络和存储，他们之间可以通过localhost进行相互通信，并可以使用共享的存储卷来交换数据（挂载了宿主机的数据卷，资源时共享的）
- 调度和部署：Pod作为调度和部署的基本单位。K8s调度器（Scheduler）将整个Pod调度到Node节点上，确保Pod中的所有容器在同一节点上运行
- 扩展性：Pod可以水平扩展，即复制多个Pod实例以增加应用程序的容量和可用性。这种扩展可以通过副本控制器（ReplicaSet）或其他控制器来实现
- 健康检查：Kubernetes提供了对Pod健康状态的检查和监控机制。通过定义监控检查规则，可以确保Pod内的容器正常运行，并在发生故障时进行自动恢复



在T Wiki上扒了一份K8s的架构图

![image-20230518181337292](images/1.png)

以下是一个Pod的定义：

```text
apiVersion: v1  # 分组和版本
kind: Pod       # 资源类型
metadata:
  name: myWeb   # Pod名
  namespace: test	#	所属的namespace
  labels:
    app: myWeb # Pod的标签
spec:
  containers:
  - name: myWeb # 容器名
    image: kubeguide/tomcat-app:v1  # 容器使用的镜像
    ports:
    - containerPort: 8080 # 容器监听的端口
    env:  # 容器内环境变量
    - name: MYSQL_SERVICE_HOST
      value: 'mysql'
    - name: MYSQL_SERVICE_PORT
      value: '3306'
    resources:   # 容器资源配置
      requests:  # 资源下限，m表示cpu配额的最小单位，为1/1000核
        memory: "64Mi"
        cpu: "250m"
      limits:    # 资源上限
        memory: "128Mi"
        cpu: "500m"
```

```text
EndPoint : PodIP + containerPort，代表一个服务进程的对外通信地址。一个Pod也存在具有多个Endpoint的情况，比如当我们把Tomcat定义为一个Pod时，可以对外暴露管理端口与服务端口这两个Endpoint。
```

# 搭建K8s集群

在了解完K8s基础后，我们来搭建一个K8s集群环境

网上给了很多种搭建的方法

- metarget
- kind
- minikube
- kubeadm
- docker-desktop

我这里选择的是docker-desktop一键搭建

mac新版本的docker自带Kubernetes，Enable后就会自动开启下载，需要注意的是，下载的时候需要FQ，解决办法：

1. 代理；
2. 寻找国内镜像

参考https://github.com/AliyunContainerService/k8s-for-docker-desktop

先调整一下分配的内存

![image-20230518183206269](images/2.png)

从阿里云镜像服务下载 Kubernetes 所需要的镜像

在 Mac 上执行如下脚本

```
./load_images.sh
```

在Windows上，使用 PowerShell

```
 .\load_images.ps1
```

这是因为k8s的镜像来自Chrome，拉取很慢，我们给它拉取到本地打上标记

接下来将Kubernetes Enable勾选上，会自动搭建k8s环境

![image-20230518183359330](images/3.png)

整个过程可能会等一会

**配置 Kubernetes**

可选操作: 切换Kubernetes运行上下文至 docker-desktop (之前版本的 context 为 docker-for-desktop)

```
kubectl config use-context docker-desktop
```

验证 Kubernetes 集群状态

```
kubectl cluster-info
kubectl get cs
kubectl get nodes
```

![image-20230518183651268](images/4.png)

配置kubernetes控制台

```
kubectl apply -f kubernetes-dashboard.yaml
```

检查 kubernetes-dashboard 应用状态

```
kubectl get pod -n kubernetes-dashboard
```

开启 API Server 访问代理

```
kubectl proxy 	# 不仅仅是dashboard，通过这个可以访问集群内的东西，docker-desktop搭建的本机属于集群外部
```

通过如下 URL 访问 Kubernetes dashboard

http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/

![image-20230518183900171](images/5.png)

**配置控制台访问令牌**

授权`kube-system`默认服务账号

```
kubectl apply -f kube-system-default.yaml
```

对于Mac环境

```
TOKEN=$(kubectl -n kube-system describe secret default| awk '$1=="token:"{print $2}')
kubectl config set-credentials docker-desktop --token="${TOKEN}"
echo $TOKEN
```

对于Windows环境

```
$TOKEN=((kubectl -n kube-system describe secret default | Select-String "token:") -split " +")[1]
kubectl config set-credentials docker-desktop --token="${TOKEN}"
echo $TOKEN
```

![image-20230518184019325](images/6.png)

**登录dashboard的时候**

可以用上面生成的token登陆，也可以用一个config文件登陆

选择 **Kubeconfig** 文件,路径如下：

```
Mac: $HOME/.kube/config
Win: %UserProfile%\.kube\config
```

点击登陆，进入Kubernetes Dashboard

![image-20230518184136914](images/7.png)

其实这也就是将Pod等信息做了一个可视化界面而已

# Kubectl

在安装好K8s集群后，有一个kubectl命令

`kubectl` 在 `$HOME/.kube` 目录中查找一个名为 `config` 的配置文件。 你可以通过设置 `KUBECONFIG` 环境变量或设置 `--kubeconfig`

这个命令是用来管理K8s集群的，操作的手册

```
kubectl controls the Kubernetes cluster manager.

 Find more information at: https://kubernetes.io/docs/reference/kubectl/

Basic Commands (Beginner):
  create          Create a resource from a file or from stdin
  expose          Take a replication controller, service, deployment or pod and
expose it as a new Kubernetes service
  run             在集群上运行特定镜像
  set             为对象设置指定特性

Basic Commands (Intermediate):
  explain         Get documentation for a resource
  get             显示一个或多个资源
  edit            编辑服务器上的资源
  delete          Delete resources by file names, stdin, resources and names, or
by resources and label selector

Deploy Commands:
  rollout         Manage the rollout of a resource
  scale           Set a new size for a deployment, replica set, or replication
controller
  autoscale       Auto-scale a deployment, replica set, stateful set, or
replication controller

Cluster Management Commands:
  certificate     修改证书资源。
  cluster-info    Display cluster information
  top             Display resource (CPU/memory) usage
  cordon          标记节点为不可调度
  uncordon        标记节点为可调度
  drain           清空节点以准备维护
  taint           更新一个或者多个节点上的污点

Troubleshooting and Debugging Commands:
  describe        显示特定资源或资源组的详细信息
  logs            打印 Pod 中容器的日志
  attach          挂接到一个运行中的容器
  exec            在某个容器中执行一个命令
  port-forward    将一个或多个本地端口转发到某个 Pod
  proxy           运行一个指向 Kubernetes API 服务器的代理
  cp              Copy files and directories to and from containers
  auth            Inspect authorization
  debug           Create debugging sessions for troubleshooting workloads and
nodes

Advanced Commands:
  diff            Diff the live version against a would-be applied version
  apply           Apply a configuration to a resource by file name or stdin
  patch           Update fields of a resource
  replace         Replace a resource by file name or stdin
  wait            Experimental: Wait for a specific condition on one or many
resources
  kustomize       Build a kustomization target from a directory or URL.

Settings Commands:
  label           更新某资源上的标签
  annotate        更新一个资源的注解
  completion      Output shell completion code for the specified shell (bash,
zsh, fish, or powershell)

Other Commands:
  alpha           Commands for features in alpha
  api-resources   Print the supported API resources on the server
  api-versions    Print the supported API versions on the server, in the form of
"group/version"
  config          修改 kubeconfig 文件
  plugin          Provides utilities for interacting with plugins
  version         输出客户端和服务端的版本信息

Usage:
  kubectl [flags] [options]

Use "kubectl <command> --help" for more information about a given command.
Use "kubectl options" for a list of global command-line options (applies to all
commands).
```

使用以下语法从终端窗口运行 `kubectl` 命令：

```shell
kubectl [command] [TYPE] [NAME] [flags]
```

其中 `command`、`TYPE`、`NAME` 和 `flags` 分别是：

- `command`：指定要对一个或多个资源执行的操作，例如 `create`、`get`、`describe`、`delete`。

- `TYPE`：指定[资源类型](https://kubernetes.io/zh-cn/docs/reference/kubectl/#resource-types)。资源类型不区分大小写， 可以指定单数、复数或缩写形式。例如，以下命令输出相同的结果：

  ```shell
  kubectl get pod pod1
  kubectl get pods pod1
  kubectl get po pod1
  ```

- `NAME`：指定资源的名称。名称区分大小写。 如果省略名称，则显示所有资源的详细信息。例如：`kubectl get pods`。

  在对多个资源执行操作时，你可以按类型和名称指定每个资源，或指定一个或多个文件：

- 要按类型和名称指定资源：
- 要对所有类型相同的资源进行分组，请执行以下操作：`TYPE1 name1 name2 name<#>`。
  例子：`kubectl get pod example-pod1 example-pod2`
- 分别指定多个资源类型：`TYPE1/name1 TYPE1/name2 TYPE2/name3 TYPE<#>/name<#>`。
  例子：`kubectl get pod/example-pod1 replicationcontroller/example-rc1`
- 用一个或多个文件指定资源：`-f file1 -f file2 -f file<#>`
- [使用 YAML 而不是 JSON](https://kubernetes.io/zh-cn/docs/concepts/configuration/overview/#general-configuration-tips)， 因为 YAML 对用户更友好, 特别是对于配置文件。
  例子：`kubectl get -f ./pod.yaml`

- `flags`： 指定可选的参数。例如，可以使用 `-s` 或 `--server` 参数指定 Kubernetes API 服务器的地址和端口。

## 常用操作

**查看集群状态**

```
kubectl cluster-info
kubectl get cs
kubectl get nodes
```

![image-20230519093227399](images/8.png)

**查看（kubectl get）**，需要查看什么资源类型就跟什么，可以列出一个或多个资源

```
kubectl get namespace
kubectl get ns
kubectl get node
# 以纯文本输出格式列出所有 Pod。
kubectl get pods

# 以纯文本输出格式列出所有 Pod，并包含附加信息(如节点名)。
kubectl get pods -o wide

# 以纯文本输出格式列出具有指定名称的副本控制器。提示：你可以使用别名 'rc' 缩短和替换 'replicationcontroller' 资源类型。
kubectl get replicationcontroller <rc-name>

# 以纯文本输出格式列出所有副本控制器和服务。
kubectl get rc,services

# 以纯文本输出格式列出所有守护程序集，包括未初始化的守护程序集。
kubectl get ds --include-uninitialized

# 列出在节点 server01 上运行的所有 Pod
kubectl get pods --field-selector=spec.nodeName=server01

# 以纯文本格式输出pod中所有的container的名字
kubectl get pods <pod-name> -o jsonpath='{.spec.containers[*].name}'
```

![image-20230519094255296](images/9.png)

![image-20230521143159163](images/10.png)

![image-20230519095612126](images/11.png)

加上wide还能显示ip地址

| 输出格式                            | 描述                                                         |
| ----------------------------------- | ------------------------------------------------------------ |
| `-o custom-columns=<spec>`          | 使用逗号分隔的[自定义列](https://kubernetes.io/zh-cn/docs/reference/kubectl/#custom-columns)列表打印表。 |
| `-o custom-columns-file=<filename>` | 使用 `<filename>` 文件中的[自定义列](https://kubernetes.io/zh-cn/docs/reference/kubectl/#custom-columns)模板打印表。 |
| `-o json`                           | 输出 JSON 格式的 API 对象                                    |
| `-o jsonpath=<template>`            | 打印 [jsonpath](https://kubernetes.io/zh-cn/docs/reference/kubectl/jsonpath/) 表达式定义的字段 |
| `-o jsonpath-file=<filename>`       | 打印 `<filename>` 文件中 [jsonpath](https://kubernetes.io/zh-cn/docs/reference/kubectl/jsonpath/) 表达式定义的字段。 |
| `-o name`                           | 仅打印资源名称而不打印任何其他内容。                         |
| `-o wide`                           | 以纯文本格式输出，包含所有附加信息。对于 Pod 包含节点名。    |
| `-o yaml`                           | 输出 YAML 格式的 API 对象。                                  |

我们也可以将一个pod输出到一个yaml中

![image-20230521133909148](images/12.png)

获取pod的时候默认获取的是default这个namespace，他们可以通过-n或者--namespace指定

```
kubectl get pods -n kube-system
```

![image-20230519094338971](images/13.png)





**创建namespace**

```
kubectl create namespace test
```

![image-20230519100037923](images/14.png)

也可以通过文件清单的方式创建

**通过文件形式更新或创建资源**

```
kubectl apply -f 以文件（YAML或yml或json）创建或更新资源

# 使用 example-service.yaml 中的定义创建服务。
kubectl apply -f example-service.yaml

# 使用 example-controller.yaml 中的定义创建 replication controller。
kubectl apply -f example-controller.yaml

# 使用 <directory> 路径下的任意 .yaml、.yml 或 .json 文件 创建对象。
kubectl apply -f <directory>
```

后面我们都将使用这种资源清单的方式来创建各种资源类型

创建namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: testspace
```

name这里只能小写

![image-20230519101652340](images/15.png)

我们以yaml格式来创建一个新的Pod

首先创建一个yaml文件，用这个yaml文件创建一个nginx

```
apiVersion: v1
kind: Pod
metadata:
  name: podtest
  namespace: test
spec:
  containers:
  - name: nginx-pod
    image: nginx:latest
    ports:
    - name: nginxport
      containerPort: 80 # 容器暴露端口
```

如果多几个spec.container.name的话，可以用一个Pod创建多个容器

- `apiVersion`记录K8S的API Server版本，现在看到的都是`v1`，用户不用管。

- `kind`记录该yaml的对象，比如这是一份Pod的yaml配置文件，那么值内容就是`Pod`。

- `metadata`记录了Pod自身的元数据，比如这个Pod的名字、这个Pod属于哪个namespace（命名空间的概念，后文会详述，暂时理解为“同一个命名空间内的对象互相可见”）。

- `spec`记录了Pod内部所有的资源的详细信息，看懂这个很重要：

- - `containers`记录了Pod内的容器信息，`containers`包括了：`name`容器名，`image`容器的镜像地址
  - `resources`容器需要的CPU、内存、GPU等资源，`command`容器的入口命令，`args`容器的入口参数
  - `volumeMounts`容器要挂载的Pod数据卷等。可以看到，**上述这些信息都是启动容器的必要和必需的信息**。
  - `volumes`记录了Pod内的数据卷信息，后文会详细介绍Pod的数据卷。

- 这里我用的是docker desktop搭建的Pod，只能从K8s集群内部访问到这个ip，无法直接从本机访问，如果用虚拟机搭建的环境，在k8s集群内部的话，就可以访问到，但是我们平常不直接访问Pod，而是通过service，在下面会介绍到

- 一部分东西在上面的yaml中没有体现

- ```
  apiVersion: v1
  kind: Pod
  metadata:
    name: memory-demo
    namespace: mem-example
  spec:
    containers:
    - name: memory-demo-ctr
      image: polinux/stress
      resources:
        limits:
          memory: "200Mi"
        requests:
          memory: "100Mi"
      command: ["stress"]
      args: ["--vm", "1", "--vm-bytes", "150M", "--vm-hang", "1"]
      volumeMounts:
      - name: redis-storage
        mountPath: /data/redis
    volumes:
    - name: redis-storage
      emptyDir: {}
  ```

- 可以参考这个

```
kubectl apply -f test-pod.yaml
```

![image-20230519101333469](images/16.png)

`kubectl describe` - 显示一个或多个资源的详细状态，默认情况下包括未初始化的资源。

```shell
# 显示名为 <pod-name> 的 node 的详细信息。
kubectl describe nodes <node-name>

# 显示名为 <pod-name> 的 Pod 的详细信息。
kubectl describe pods/<pod-name>

# 显示由名为 <rc-name> 的副本控制器管理的所有 Pod 的详细信息。
# 记住：副本控制器创建的任何 Pod 都以副本控制器的名称为前缀。
kubectl describe pods <rc-name>

# 描述所有的 Pod
kubectl describe pods
```

还是要选择namespace，不然默认为default

```
kubectl describe pods/podtest -n test
```

![image-20230519112720891](images/17.png)

`kubectl delete`删除资源

```
# 使用 pod.yaml 文件中指定的类型和名称删除 Pod。
kubectl delete -f pod.yaml

# 删除所有带有 '<label-key>=<label-value>' 标签的 Pod 和服务。
kubectl delete pods,services -l <label-key>=<label-value>

# 删除所有 Pod，包括未初始化的 Pod。
kubectl delete pods --all

# 通过名字删除
kubectl delete namespace test
```

当删除了namespace后，里面所有的Pod均会被删除

![image-20230519102133560](images/18.png)

通过文件删除，其实和apply一样，通过什么文件创建就通过什么文件删除，用资源清单的方式管理的话，在大规模的时候，会便于管理一点

![image-20230519102304575](images/19.png)

`kubectl exec` - 对 Pod 中的容器执行命令。

```shell
# 从 Pod <pod-name> 中获取运行 'date' 的输出。默认情况下，输出来自第一个容器。namespace默认default
kubectl exec <pod-name> -n <namespace-name> -- date

# 运行输出 'date' 获取在 Pod <pod-name> 中容器 <container-name> 的输出。（多个容器）
kubectl exec <pod-name> -c <container-name> -- date

# 获取一个交互 TTY 并在 Pod  <pod-name> 中运行 /bin/bash。默认情况下，输出来自第一个容器。
kubectl exec -ti <pod-name> -- /bin/bash
```

注意这里的container-name不是docker ps看到的，而是yaml写那个，可以用kubectl describe看到

![image-20230519112403070](images/20.png)

我们把namespace和pod重新拉起来

![image-20230519102430013](images/21.png)

执行命令

```
kubectl exec podtest -n test -- ls
```

![image-20230519110153022](images/22.png)

交互式shell

```
kubectl exec -it podtest -n test -- /bin/bash
```

![image-20230519110253307](images/23.png)

其实和docker的exec命令差不多，只是要是通过Pod

`kubectl logs` - 打印 Pod 中容器的日志。

```shell
# 返回 Pod <pod-name> 的日志快照。
kubectl logs <pod-name>

# 从 Pod <pod-name> 开始流式传输日志。这类似于 'tail -f' Linux 命令。
kubectl logs -f <pod-name>
```

![image-20230519110848413](images/24.png)

`kubectl diff` - 查看集群建议更新的差异。

```shell
# “pod.json”中包含的差异资源。
kubectl diff -f pod.json

# 从标准输入读取的差异文件。
cat service.yaml | kubectl diff -f -
```

# label

用来标识和组织资源对象的键值对。可以用于Pod，Service，Deployment，以便资源的分类、选择和过滤

一个资源对象可以定义任意数量的label，同一个label也可以被添加到任意数量的资源对象上。

我们可以为一个pod打上label标签

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: podtest
  namespace: test
  labels:
    app: nginx
    environment: production
spec:
  containers:
  - name: nginx-pod
    image: nginx:latest
    ports:
    - name: nginxport
      containerPort: 80
```

这里设置了两个label标签： "app: nginx" 和 "environment: production"，这个标签可以用来选择和标识该pod，以及与其他具有相同标签的资源对象进行关联。

然后在另外一个service的spec的selector中选择这个标签，就指明了这个pod

```text
apiVersion: v1  
kind: Service       
metadata:
  name: mynginx   
spec:
  selector:
    app: nginx
  ports:
  - port: 80
```

# Replication Controller

之前我们提到了在master节点中有Controller manager处理集群级别的后台任务，其中有复制控制器Replication Controller

复制控制器Replication Controller是k8s中的一种资源对象，用于确保在集群中运行指定数量的Pod，是K8s最早引入的一种控制器，现在已经被Deployment对象取代

主要目标是维护Pod副本的数量，并确保运行的Pod副本数始终与用户定义的副本数匹配，如果有Pod因任何原因终止或失败，Replication Controller会自动创建新的Pod，保持制定的Pod数目

以下是一些Replication Controller的特性和工作原理：

1. 副本数目控制：用户可以在Replication Controller中指定期望的Pod副本数目，控制器将根据该设置来维护副本数量。
2. 自愈能力：如果某个Pod副本终止或失败，Replication Controller会自动创建新的Pod副本，确保副本数目保持恒定。
3. 标识选择器：Replication Controller使用标识选择器来确定属于自己管理范围的Pod副本。它使用标签（Labels）来匹配和选择Pod。
4. 无状态：Replication Controller本身是无状态的，它不会保存副本的状态信息。它仅关心Pod副本的数量，而不考虑具体的副本是哪些。

```text
目前，RC已升级为新概念——Replica Set(RS)，两者当前唯一区别是，RS支持了基于集合的Label Selector，而RC只支持基于等式的Label Selector。RS很少单独使用，更多是被Deployment这个更高层的资源对象所使用，所以可以视作RS+Deployment将逐渐取代RC的作用。
```

一个简单的RC

```yaml
apiVersion: v1
kind: ReplicationController
metadata:
  name: testcontroller
  namespace: test
spec:
  replicas: 3  # Pod副本数量
  selector:
    app: nginx
  template:	# Pod模板
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx-pod
        image: nginx:latest
        ports:
        - containerPort: 80
```

可以看到，它自动创建了三个Pod

![image-20230519145657858](images/25.png)

pod的命名是testcontroller加上5个随机的后缀

我们现在来删除其中一个Pod看看效果

![image-20230519150025438](images/26.png)

可以发现，删除后，又自动创建了一个新的Pod

当提交这个RC在集群中后，Controller Manager会定期巡检，确保目标Pod实例的数量等于RC的预期值，过多的数量会被停掉，少了则会创建补充。通过`kubectl scale`可以动态指定RC的预期副本数量。

```
kubectl scale replicationcontroller/testcontroller -n test --replicas=4 
```

![image-20230519150303720](images/27.png)

# Deployment

Deployment是常见的Controller中的一种

![image-20230519145120358](images/28.png)

我们一般不直接创建ReplicaSet控制器，Deployment里面包含了ReplicaSet，除非自定义升级功能或者根本不需要升级Pod，否则还是建议使用Deployment而不直接使用ReplicaSet

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: test
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: podtest
        image: nginx:latest
        ports:
        - containerPort: 80
```

Deployment控制器模板包含以下部分：

1. `spec.replicas`：指定要创建的Pod副本数量为3个。
2. `spec.selector`：指定选择器用于标识与Deployment关联的Pod。在上述示例中，使用`app: nginx`标签来选择相关的Pod。
3. `spec.template.metadata`：定义Pod模板的元数据，包括标签。
4. `spec.template.spec`：定义要创建的Pod的规范。其中，`spec.template.spec.containers`部分定义了要在Pod中运行的容器的配置。在上述示例中，容器名称为`podtest`，使用`nginx:latest`镜像，暴露容器端口80

![image-20230519154523438](images/29.png)

已经创建好了，和RC一样，我们来删除一个Pod看看会不会重新拉取

![image-20230519154800260](images/30.png)

可以看到，deployment也相当于监视器一样，监视着pod资源，在没有达到指定数量pod时，重新拉取pod

通过kubectl scale动态调整pod数量

```
kubectl scale deployment/nginx-deployment -n test --replicas=5 
```

![image-20230519155217178](images/31.png)

# Service

在前面的介绍中，我们发现了虽然可以人工的创建Pod，多少要保证环境的稳定的话，我们基本上会用到Deployment这种控制器，当出现问题的时候，会自动拉起新的Pod，这时候Pod的状态就不是人为可用的了，当变化Pod的时候，IP就会随即改变，所以，在大规模的分布式网络中，我们用Pod的IP地址访问Pod的话，是不可行的，这是就引入一个新的概念service

Service提供一种稳定的网络终点，以便其他应用程序或用户可以通过该终点访问被服务的Pod，简而言之，就是我们可以通过Service的IP访问的被这个service服务的Pod，这样就提供了一种稳定的网络访问

service并不是实体服务（即没有自己的守护进程，没有配置文件等），我们可以将其理解为iptables或者ipvs的路由转发规则

**service作用：**

- 为Pod客户端提供访问Pod方法，即客户端访问Pod入口
- 通过Pod标签与Pod相关联

**Service有几种类型，包括：**

- ClusterIP：默认类型，将创建一个在集群内部可访问的虚拟IP。其他Pod或Service可以通过ClusterIP和Service名称进行通信，但该Service不会从集群外部暴露。
- NodePort：创建一个将外部流量转发到Service的固定端口。除了在集群内部使用ClusterIP进行访问外，还可以通过任何节点的IP地址和NodePort进行访问。
- LoadBalancer：根据云服务提供商的支持，将创建一个外部负载均衡器，并将流量路由到Service。这个类型需要云服务提供商支持，并且通常需要配置负载均衡器。
- ExternalName：将Service映射到集群外部的任意DNS名称。它通过返回指定的外部DNS名称的CNAME记录来解析Service。

默认创建的service是clusterIP类型

Service与其后端的Pod副本集群之间通过Label Selector来实现无缝对接

![image-20230521113254401](images/32.png)

## Cluster类型

接下来我们一样用资源清单的方式来创建一个Service

在这个yaml文件中，我们直接把deployment和service一起拉起来

```
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-apps
  namespace: test
  labels:
    app: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginxapps
        image: nginx:latest
        ports:
        - containerPort: 80

---
apiVersion: v1
kind: Service
metadata:
  name: nginx-apps-svc
  namespace: test
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
  - protocol: TCP
    port: 80	# svc暴露端口
    targetPort: 80  # Pod暴露的端口
```

![image-20230521131211310](images/33.png)

Docker Desktop创建的Service默认使用的是Kubernetes内部的ClusterIP类型，这种类型的Service只在Kubernetes集群内部可用，无法直接从本机访问。

如果你想要从本机访问通过ClusterIP暴露的Service，你可以使用端口转发（port forwarding）来实现

```
kubectl port-forward service/<service-name> -n <namespace-name> <local-port>:<service-port>
即
kubectl port-forward service/nginx-apps-svc -n test 8888:80
```

![image-20230521132958697](images/34.png)

![image-20230521132949124](images/35.png)

请注意，端口转发只在你运行端口转发命令的终端或命令提示符窗口处于打开状态时有效。如果你关闭了该窗口，端口转发也会被终止。

另外，还有一种方式是将Service的类型设置为NodePort或LoadBalancer，这样Service将会分配一个宿主机上的端口或通过负载均衡器公开访问。这样你就可以直接使用宿主机的IP地址和相应的端口来访问Service，而无需进行端口转发

## NodePort类型

因为我是用docker-desktop搭建的K8s集群，我本机并不在kubunetes集群内部，因为集群肯定会提供外网的访问，但是可以不会一直是这种端口转发，所以我们使用到NodePort这种类型

注意分配的端口范围（30000-32767）

创建和刚才一样，只是把类型改了一下

```
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-apps
  namespace: test
  labels:
    app: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginxapps
        image: nginx:latest
        ports:
        - containerPort: 80

---
apiVersion: v1
kind: Service
metadata:
  name: nginx-apps-svc-nodeport
  namespace: test
spec:
  type: NodePort
  selector:
    app: nginx
  ports:
  - protocol: TCP
    port: 80	# svc暴露端口
    targetPort: 80  # Pod暴露的端口
```

![image-20230521140256439](images/36.png)

根据你选择的类型（NodePort或LoadBalancer），Service将会分配一个宿主机上的端口或通过负载均衡器公开访问。你可以使用宿主机的IP地址和相应的端口来直接从本机访问Service。

![image-20230521140336912](images/37.png)

目前是随机分配到端口，我们也可以指定端口，用nodePort

```
ports:
  - protocol: TCP
    port: 80	# svc暴露端口
    targetPort: 80  # Pod暴露的端口
    nodePort: 30001 # 转发到宿主机的端口
```

请注意，如果你使用LoadBalancer类型，你的Kubernetes集群所在的环境必须支持负载均衡器服务，否则LoadBalancer将无法正常工作。

这里就只演示了两种类型

## 负载均衡

service除了给我们提供一个稳定访问Pod的方式，还可以提供负载均衡

在 Kubernetes 集群中，每个 Node 上会运行着 kube-proxy 组件，这其实就是一个负载均衡器，负责把对 Service 的请求转发到后端的某个 Pod 实例上，并在内部实现服务的负载均衡和绘画保持机制。其主要的实现就是每个 Service 在集群中都被分配了一个全局唯一的 Cluster IP，因此我们对 Service 的网络通信根据内部的负载均衡算法和会话机制，便能与 Pod 副本集群通信

![image-20230521140916015](images/38.png)

目前我们是启动了两个Pod的，我们来修改一下其index.html文件，看看负载均衡访问的效果

![image-20230521141123857](images/39.png)

![image-20230521141245814](images/40.png)

然后我们来访问service看看

![image-20230521141340332](images/41.png)

可以看到是可以实现负载均衡功能的，但是没有一定的规定

# Volume

volume是Pod中能被多个容器访问的共享目录，可被定义在 Pod 上，然后被 一个Pod里的多个容器挂载到具体的文件目录下；其次，Kubernetes 中的 Volume 与 Pod 的生命周期相同，但与容器的生命周期不相关，当容器终止或者重启时，Volume 中的数据也不会丢失

以下是一些关键概念和常见类型的Kubernetes Volume：

1. EmptyDir：EmptyDir是一种空目录的Volume，它在Pod创建时被创建，并与Pod的生命周期绑定。它提供了在容器之间共享数据的简单方式，但在Pod重新调度或重启时，数据将丢失。
2. HostPath：HostPath允许将宿主机上的文件或目录挂载到Pod中的Volume中。这种Volume类型适用于需要访问宿主机上文件系统的场景，但它不具备跨节点的可移植性。
3. PersistentVolumeClaim（PVC）：PersistentVolumeClaim是一种声明式的方式来请求持久化存储。PVC是由应用程序开发者创建，然后由Kubernetes根据存储类（StorageClass）和持久化存储后端提供动态分配的持久化存储Volume。
4. ConfigMap和Secret：ConfigMap和Secret是用于存储配置文件和敏感信息的Volume类型。ConfigMap用于存储非敏感的配置数据，而Secret用于存储敏感的密钥、密码等数据。这些数据可以被挂载到Pod中的容器中作为文件或环境变量。
5. NFS、AWS EBS、Azure Disk等：Kubernetes还支持多种外部持久化存储后端，如NFS、AWS EBS、Azure Disk等。这些存储后端可以通过持久化卷（PersistentVolume）和持久化卷声明（PersistentVolumeClaim）来使用。

Volume是Pod级别的资源，意味着Pod中的所有容器都可以访问和共享Volume中的数据。这使得在同一Pod中的多个容器之间共享数据变得更加容易和高效，很多用法，就演示几个吧

## emptyDir

我们先来创建一个emptyDir类型的

```
apiVersion: v1
kind: Pod
metadata:
  name: podtest
  namespace: test
  labels:
    app: nginx
spec:
  volumes:
  - name: datavol
    emptyDir: {}
  containers:
  - name: nginx-pod
    image: nginx:latest
    ports:
    - name: nginxport
      containerPort: 80
    volumeMounts:
    - mountPath: /mydata-data
      name: datavol
```

![image-20230521154107763](images/42.png)

因为我们说的volume是提供Pod内容器资源共享的，所以我们重新起一个Pod，里面起两个容器

```
apiVersion: v1
kind: Pod
metadata:
  name: pod-volume
  namespace: test
spec:
  containers:
  - name: container1
    image: nginx:latest
    volumeMounts:
    - name: data-volume
      mountPath: /data-test
  - name: container2
    image: ubuntu:latest
    command: [ "/bin/bash", "-ce", "tail -f /dev/null" ]	#	解决 Back-off restarting failed container报错
    volumeMounts:
    - name: data-volume
      mountPath: /data-test
  volumes:
  - name: data-volume
    emptyDir: {}
```

![image-20230521160338461](images/43.png)

我们在container1中的data-test目录写入一个volume.txt

然后进入container2的交互式shell，可以看到这个目录是两个container共享的

![image-20230521160426566](images/44.png)

在这个示例中，我们定义了一个名为`data-volume`的EmptyDir类型的Volume，并将其挂载到了两个容器中的`/data-test`路径。第一个容器使用`nginx:latest`镜像，第二个容器使用`ubuntu:latest`镜像。

EmptyDir类型的Volume在Pod创建时被创建，并且在Pod的整个生命周期内持久存在。它为Pod中的容器提供了一个可共享的临时存储区域。当Pod被删除时，EmptyDir中的数据也会被删除。

您可以根据需要在Pod配置文件中添加更多容器，并将它们的`volumeMounts`指定为同一个EmptyDir Volume的挂载路径（不同container可以挂载到不同的路径）

使用EmptyDir类型的Volume时，需要注意以下几点：

- EmptyDir Volume只在Pod的单个节点上存在，它不提供跨节点的数据共享。
- 当Pod重新调度或重启时，EmptyDir中的数据将会丢失。
- 多个容器可以同时访问和共享EmptyDir Volume中的数据。

通过在Pod的配置文件中定义EmptyDir类型的Volume，并将其挂载到所需的容器中，您可以在Kubernetes中创建临时的共享存储区域。



在EmptyDir类型的Volume的定义中，`{}`内可以是空的，也可以包含其他配置项。

如果希望使用EmptyDir的默认配置，您可以将其定义为一个空的对象，即`emptyDir: {}`，这将使用默认的EmptyDir配置。

如果需要自定义EmptyDir的某些属性，可以在`{}`内添加其他配置项。以下是一些可用的配置选项：

- `medium`：指定EmptyDir的介质类型，可选值为`""`（默认）或`Memory`。如果设置为`Memory`，则EmptyDir将使用内存而不是磁盘进行存储。

示例：

```
volumes:
  - name: data-volume
    emptyDir:
      medium: Memory
```

在这个示例中，EmptyDir的介质类型被设置为`Memory`，这意味着EmptyDir将使用内存进行存储。

请注意，不同的Kubernetes发行版和版本可能对EmptyDir支持的配置项略有不同，具体取决于使用的Kubernetes版本和集群的配置。可以参考相应的文档或发行版的文档以了解支持的配置选项。

如果不需要自定义EmptyDir的属性，可以将`emptyDir`保持为空对象，即`emptyDir: {}`。这将使用默认的EmptyDir配置，并创建一个在Pod的整个生命周期内持久存在的临时存储区域。

## PersistentVolumeClaim (PVC)

### PV和PVC

PersistentVolumeClaim (PVC) 是 Kubernetes 中用于请求持久化存储的资源声明。PVC 允许应用程序开发者申请并使用持久化存储资源，而无需关心底层存储的具体细节。

我们再来了解一下PV和PVC的区别

PersistentVolume (PV) 和 PersistentVolumeClaim (PVC) 是 Kubernetes 中的两个不同概念，它们分别用于表示持久化存储的实际资源和对存储资源的请求和使用声明。

- PersistentVolume (PV)：PV 是 Kubernetes 中的实际存储资源。它是集群管理员配置和管理的，可以看作是集群中的存储池。PV 可以连接到物理存储设备、云提供商的存储服务或其他外部存储系统。PV 有自己的生命周期，并独立于应用程序的生命周期。它可以被多个 PVC 绑定和共享。
- PersistentVolumeClaim (PVC)：PVC 是应用程序开发者在 Kubernetes 中用于请求持久化存储的声明。PVC 定义了应用程序对存储资源的需求，例如所需的存储大小、访问模式等。PVC 是与 Pod 相关联的，它将请求发送给集群中的 PV。根据 PVC 的需求，Kubernetes 会找到并绑定一个合适的 PV，并将其提供给应用程序使用。PVC 的生命周期与关联的 Pod 相关。

PV 是集群中的存储资源，而 PVC 是应用程序对存储资源的请求和使用声明。PVC 用于将应用程序与底层的 PV 进行绑定，使应用程序能够使用持久化存储。

PV 和 PVC 的使用使得存储与应用程序解耦，应用程序开发者无需关心底层存储的具体细节，而能够通过声明式的方式来请求和使用持久化存储资源

可以发现，真正的存储实际上是在PV，PVC只是一个声明，至于数据的持久性，要看底层的PV是如何定义

如果底层的 PV（PersistentVolume）是基于持久性存储的类型（如网络存储、云存储等），并且在 PVC 的声明中指定了适当的存储策略（例如保留数据、回收策略等），则数据可以在 Pod 重启后得到保留。

但是，如果底层的 PV 是基于临时性存储（例如 EmptyDir 类型的 PV），或者在 PVC 的声明中没有指定适当的存储策略，那么在 Pod 重启后，数据将会丢失

### 创建通过PV存储的Pod

前面提到了，实际的存储是PV，但是声明是PVC，我们在Pod里面用到的是PVC，所以我们还需要把PVC绑定到对应的PV

首先我们可以创建一个存储类（ StorageClass）

这是一个存储类的示例，我们可以自定义存储类，也可以使用K8s默认的存储类（standard）

```
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: test-storage-class
provisioner: kubernetes.io/nfs
parameters:
  nfsServer: nfs-server.example.com
  nfsPath: /exports/data
```

请将`provisioner`是为你所使用的存储提供商的Provisioner名称，并根据需要提供特定的参数（如果适用）

![image-20230522145323406](images/45.png)

**创建PV**

```
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-pv
  namespace: test
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: test-storage-class
  nfs: 
    server: nfs-server.example.com
    path: /exports/data
    
不绑定存储类
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  nfs:
    server: nfs-server.example.com
    path: /exports/data

```

storageClassName: test-storage-class指定存储类，也可以为空，表示不绑定到存储类，而是使用`nfs`字段指定了NFS服务器的地址和共享路径，k8s中应该是有默认的存储类，我这里叫做hostpath

`persistentVolumeReclaimPolicy: Retain` 表示在 PVC 解除绑定后，保留对 PV 资源的保留策略。具体而言，当 PVC 不再使用 PV 时，PV 不会被自动删除，而是保留在集群中。这意味着即使 PVC 不再使用 PV，PV 中仍然保留着先前存储的数据

除了 `Retain`，还有其他的 `persistentVolumeReclaimPolicy` 可选值可供选择，包括：

- `Delete`：在 PVC 解除绑定后，自动删除 PV 资源及其数据。
- `Recycle`：在 PVC 解除绑定后，自动清除 PV 中的数据，以供其他 PVC 重用。但这个回收策略在最新的 Kubernetes 版本中已被废弃，不再推荐使用。

一般情况下，默认的 `persistentVolumeReclaimPolicy` 是 `Delete`。这意味着当 PVC 解除绑定后，PV 资源将自动被删除，并且与之关联的底层存储资源也将被释放。

```text
accessModes，有几种类型

1. ReadWriteOnce:读写权限，并且只能被单个Node挂载。 
2. ReadOnlyMany:只读权限，允许被多个Node挂载。 
3. ReadWriteMany:读写权限，允许被多个Node挂载。
```

![image-20230522150339997](images/46.png)

- PV 只能是网络存储，不属于任何 Node，但可以在每个 Node 上访问。
- PV 并不是被定义在 Pod 上的，而是独立于 Pod 之外定义的。

PV有以下几种状态：

- Available：空闲
- Bound：已绑定到PVC
- Released：对应PVC被删除，但PV还没被回收
- Faild： PV自动回收失败

**创建PVC**

Pod要申请某种类型的PV，就要先定义一个PVC对象

```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
  namespace: test
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: test-storage-class
```

确保在`storageClassName`字段中指定与上述持久卷（PV）配置中相同的存储类名称

![image-20230522150746884](images/47.png)

**创建pod绑定pvc**

```
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod-test
  namespace: test
  labels:
    app: nginx
spec:
  volumes:
  - name: nginx-data
    persistentVolumeClaim:
      claimName: my-pvc
  containers:
  - name: container1
    image: nginx:latest
    volumeMounts:
    - name: nginx-data
      mountPath: /data-test
    ports:
    - containerPort: 80
  - name: container2
    image: ubuntu:latest
    command: [ "/bin/bash", "-ce", "tail -f /dev/null"]
    volumeMounts:
    - name: nginx-data
      mountPath: /data-test
```

![image-20230522152640843](images/48.png)

记得在创建后查看status是否绑定

最后启动容器的时候，nfs挂载报错了，也没有去管了，大概的思路是这样的

## ConfigMap

这个挂载方式相当于对把configmap配置的某些内容映射到容器中

### 创建configmap

```
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  key1: |-
    "文件内容"
```

我用我桌面上的aaa.txt创建的configmap（/Users/DawnT0wn/Desktop）

从文件导入

```
kubectl create configmap my-config --from-file=path/to/file1.txt --from-file=path/to/file2.txt
```

直接写内容

```
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  aaa.txt: |
    "Config Test2"
```

![image-20230522154539281](images/49.png)

### 通过configmap创建Pod

```
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: test
spec:
  containers:
    - name: my-container
      image: nginx:latest
      volumeMounts:
        - name: config-volume
          mountPath: /data-test
  volumes:
    - name: config-volume
      configMap:
        name: my-config
```

![image-20230522154740304](images/50.png)

![image-20230522155345197](images/51.png)

可以看到，用yaml的话不能用file协议，只能直接写内容，用命令行创建可以从文件导入

# 排查

这一部分只简单的看了一点，就直接扒下来了，主要还是用`kubectl log和kubectl describe`

## K8S上部署服务失败了怎么排查

请一定记住这个命令：`kubectl describe ${RESOURCE} ${NAME}`。比如刚刚的Pod服务memory-demo，我们来看：

![img](https://pic3.zhimg.com/80/v2-a7cdcbb9b367de69f361751e956d6636_1440w.webp)

```
kubectl describe ${RESOURCE} ${NAME}
```

拉到最后看到`Events`部分，会显示出K8S在部署这个服务过程的关键日志。这里我们可以看到是拉取镜像失败了，好吧，大家可以换一个可用的镜像再试试。

一般来说，通过`kubectl describe pod ${POD_NAME}`已经能定位绝大部分部署失败的问题了，当然，具体问题还是得具体分析。

## K8S上部署的服务不正常怎么排查

如果服务部署成功了，且状态为`running`，那么就需要进入Pod内部的容器去查看自己的服务日志了：

- 查看Pod内部某个container打印的日志：`kubectl log ${POD_NAME} -c ${CONTAINER_NAME}`。
- 进入Pod内部某个container：`kubectl exec -it [options] ${POD_NAME} -c ${CONTAINER_NAME} [args]`，嗯，这个命令的作用是通过kubectl执行了`docker exec xxx`进入到容器实例内部。之后，就是用户检查自己服务的日志来定位问题。

# 一些思考

下面是学完以后，关于一些情况下使用的思考，得到了ChatGpt的回答

## 为什么要把多个容器写到Pod里面呢

将多个容器放在同一个Pod中有以下几个主要原因：

1. 共享网络命名空间和存储：Pod中的所有容器共享相同的网络命名空间和存储卷。这使得它们可以直接通过`localhost`或Pod内部的网络地址进行快速、高效的通信。共享存储卷可以方便地在容器之间共享文件和数据。
2. 紧密耦合的容器：有时候，多个容器之间有紧密的耦合关系，它们需要协同工作以完成某个特定的任务。例如，一个Web应用程序容器可能需要与一个代理容器配合工作，用于处理静态文件、负载均衡或安全认证等功能。将这些容器放在同一个Pod中可以简化它们之间的通信和协调。
3. 简化管理和部署：将相关的容器放在同一个Pod中可以简化管理和部署的复杂性。Pod是Kubernetes调度和管理的最小单元，因此将多个相关容器打包在一起可以更方便地进行部署、扩展和管理。通过Pod控制器（如Deployment）可以轻松地对整个Pod进行扩展或更新。
4. 故障隔离和弹性：将多个容器放在同一个Pod中可以提供更好的故障隔离和弹性。如果一个容器发生故障或需要重新启动，其他容器仍然可以继续运行。此外，Kubernetes可以自动重新创建整个Pod，以确保多个容器的正常运行。

虽然通过Service访问的是Pod，但Service可以将请求根据标签选择器路由到Pod中的特定容器。这样，即使Pod中有多个容器，通过Service访问时仍然可以精确地将请求路由到目标容器。Service提供了透明的负载均衡，将请求分发到Pod中的所有容器中的一个或多个。

总结起来，将多个容器放在同一个Pod中可以提供更紧密的耦合、共享的网络和存储，简化管理和部署，并提供故障隔离和弹性。这使得Pod成为多容器应用程序的理想单位，并可以通过Service来访问这些容器。

## 那为什么要通过deployment部署多个一样的Pod呢

通过Deployment部署多个相同的Pod有以下几个主要原因：

1. 高可用性和负载均衡：通过部署多个相同的Pod，可以实现应用程序的高可用性和负载均衡。Deployment控制器可以根据所配置的副本数，在集群中创建多个Pod副本。这些Pod副本可以分布在不同的节点上，当一个节点或Pod发生故障时，其他副本仍然可以继续提供服务。同时，Deployment通过负载均衡机制将请求分发到多个Pod副本，实现请求的均衡分配，提高应用程序的可扩展性和性能。
2. 滚动更新和回滚：通过Deployment可以方便地进行滚动更新和回滚操作。当应用程序需要更新时，可以通过修改Deployment的配置来指定新的镜像版本或其他更新内容。Deployment控制器会逐步创建新的Pod副本，并在确保新的Pod正常运行后，逐步停止旧的Pod副本。这样就可以实现无缝的应用程序更新，避免中断服务。如果更新出现问题，可以快速回滚到之前的稳定版本，保证应用程序的可靠性和稳定性。
3. 集群资源管理和扩展：通过Deployment部署多个相同的Pod，可以更好地管理和利用集群的资源。Deployment控制器可以根据配置的副本数和资源需求，动态地调度和调整Pod副本的数量。这使得应用程序的扩展变得更加灵活和自动化，可以根据负载情况进行自动缩放，提高资源利用率和性能。
4. 简化管理和维护：通过Deployment部署多个相同的Pod，可以简化管理和维护的工作。通过统一的Deployment配置，可以方便地管理和监控整个应用程序的生命周期。可以通过Kubernetes提供的工具和命令，轻松地批量操作和管理多个Pod副本，减少了手动管理的工作量。

综上所述，通过Deployment部署多个相同的Pod可以提供高可用性、负载均衡、滚动更新和回滚、集群资源管理和扩展等优势。这使得应用程序的部署、管理和维护更加方便、可靠和可扩展。

## 在Pod初始化容器的时候，如何像Dockerfile一样执行多条命令

在Kubernetes中，Pod的初始化容器并不像Dockerfile那样支持多个命令的连续执行，而是执行单个命令或脚本。这意味着无法直接在初始化容器的配置中像Dockerfile那样编写多个命令。

但是，您可以通过编写一个自定义的启动脚本，并在初始化容器中执行该脚本来达到执行多个命令的目的。这个启动脚本可以包含您需要执行的多个命令，并按顺序执行它们。

以下是一个示例的初始化容器配置，演示如何使用自定义的启动脚本来执行多个命令：

```
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
    - name: main-container
      image: nginx:latest
      # 主容器的配置...
    initContainers:
    - name: init-container
      image: nginx:latest
      command: ["sh", "-c", "chmod +x /path/to/script.sh && /path/to/script.sh"]
      volumeMounts:
        - name: script-volume
          mountPath: /path/to/script.sh
          subPath: script.sh
  volumes:
    - name: script-volume
      configMap:
        name: script-configmap
```

在这个示例中，我们使用了一个名为`init-container`的初始化容器，并将一个启动脚本`script.sh`放置在一个ConfigMap中。初始化容器首先将脚本文件复制到Pod中的`/path/to/script.sh`路径，然后通过`chmod +x`命令赋予脚本执行权限，并执行脚本。

启动脚本`script.sh`可以包含您想要执行的多个命令，例如：

```
bashCopy code
#!/bin/sh
echo "Step 1: Do something..."
command1
echo "Step 2: Do something else..."
command2
echo "Step 3: Do another thing..."
command3
```

您可以根据需求编写自定义的启动脚本，并在初始化容器中进行执行。请确保脚本文件在Pod中可用，并通过适当的命令执行它。





参考链接：

https://chat.openai.com/

https://zhuanlan.zhihu.com/p/292081941

https://zone.huoxian.cn/d/1153-k8s

https://security.tencent.com/index.php/blog/msg/183

https://mp.weixin.qq.com/s/WJ14yyrLptQnRovFoGYv8A

https://wiki.teamssix.com/CloudNative/Kubernetes/

[kubernetes极速入门_k8s集群NameSpace(命名空间)_NameSpace创建_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV1W7411J7jh?p=29&spm_id_from=pageDriver&vd_source=5ddaf0a13575e9d0512f1c316baf5a0e)

https://blog.csdn.net/LW1314QS/article/details/126039193

https://github.com/AliyunContainerService/k8s-for-docker-desktop

https://zhuanlan.zhihu.com/p/437623321

https://kubernetes.io/zh-cn/docs/reference/kubectl/

https://zhuanlan.zhihu.com/p/308477039

https://zhuanlan.zhihu.com/p/365137154