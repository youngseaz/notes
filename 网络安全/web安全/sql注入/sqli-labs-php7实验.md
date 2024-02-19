
# 实验环境搭建

1. **环境依赖如下**
   1. Nginx/1.10.3
   2. PHP 7.0.33-0 ubuntu0.16.04.16 (cli) ( NTS )
   3. [sqli-labs-php7](https://github.com/skyblueee/sqli-labs-php7)

2. **环境安装部署**

`apt update -y && apt -y install nginx php php7.0-dev php7.0-mysql`

3. 下载 sqli-labs-php7 并放到 nginx 工作目录

```bash
git clone https://github.com/skyblueee/sqli-labs-php7.git
cp -r sqli-labs-php7 /var/www/html/
```

4. **nginx配置**

编辑配置文件 /etc/nginx/sites-enabled/default
```conf
# 添加 index.php
# Add index.php to the list if you are using PHP
index index.html index.htm index.nginx-debian.html index.php;

# 取消 php 相关注释，如下
location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        # With php7.0-cgi alone:
        #fastcgi_pass 127.0.0.1:9000;
        # With php7.0-fpm:
        fastcgi_pass unix:/run/php/php7.0-fpm.sock;  
}

```
5. **重启 nginx**

`systemctl restart nginx`

6. 访问页面，初始化数据库

![Alt text](images/sqli-labs-php7%E5%AE%9E%E9%AA%8C/image-1.png)

![Alt text](images/sqli-labs-php7%E5%AE%9E%E9%AA%8C/image.png)


# Less-1

关键代码片段如下，传入的ID参数直接构造sql语句，存在注入。

```php
<?php
$sql="SELECT * FROM users WHERE id='$id' LIMIT 0,1";
// $sql="SELECT * FROM users WHERE id='0' union select 1,2,3 -- ' LIMIT 0,1";
// $sql="SELECT * FROM users WHERE id='0' union select 1,2,3 # ' LIMIT 0,1";
$result=mysqli_query($con1, $sql);
$row = mysqli_fetch_array($result, MYSQLI_BOTH);

?>
```




# Less-2
# Less-3
# Less-4
# Less-5
# Less-6
# Less-7


```php

<?php
$sql="SELECT * FROM users WHERE id=(('$id')) LIMIT 0,1";
$result=mysqli_query($con1, $sql);
$row = mysqli_fetch_array($result, MYSQLI_BOTH);
?>
```
# Less-8
# Less-9
# Less-10
# Less-11
# Less-12
# Less-13
# Less-14
# Less-15
# Less-16
# Less-17
# Less-18
# Less-19
# Less-20
# Less-21
# Less-22
# Less-23
# Less-24
# Less-25
# Less-26
# Less-27
# Less-28
# Less-29
# Less-30
# Less-31
# Less-32
# Less-33
# Less-34
# Less-35
# Less-36
# Less-37
# Less-38
# Less-39
# Less-40
# Less-41
# Less-42
# Less-43
# Less-44
# Less-45
# Less-46
# Less-47
# Less-48
# Less-49
# Less-50
# Less-51
# Less-52
# Less-53
# Less-54
# Less-55
# Less-56
# Less-57
# Less-58
# Less-59
# Less-60
# Less-61
# Less-62
# Less-63
# Less-64
# Less-65
# Less-66
# Less-67
# Less-68
# Less-69
# Less-70
# Less-71
# Less-72
# Less-73
# Less-74
# Less-75

