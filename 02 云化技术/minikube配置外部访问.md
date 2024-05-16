
执行 minikube dashboard 之后，服务只允许 localhost 访问
```
young@ubuntu:~$ minikube dashboard
* Enabling dashboard ...
  - Using image docker.io/kubernetesui/dashboard:v2.7.0
  - Using image docker.io/kubernetesui/metrics-scraper:v1.0.8
* Some dashboard features require the metrics-server addon. To enable all features please run:

        minikube addons enable metrics-server


* Verifying dashboard health ...
* Launching proxy ...
* Verifying proxy health ...
* Opening http://127.0.0.1:40565/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/ in your default browser...
  http://127.0.0.1:40565/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/


```

启用 k8s 代理，运行服务外部地址访问 `kubectl proxy --port=8000 --address='192.168.154.130' --accept-hosts='^*'`

```
young@ubuntu:~$ kubectl proxy --port=8000 --address='192.168.154.130' --accept-hosts='^*'
Starting to serve on 192.168.154.130:8000

```