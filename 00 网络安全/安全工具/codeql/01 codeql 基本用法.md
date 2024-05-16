# codeql 安装

codeql 安装部署、数据库编译等[见官方文档](https://docs.github.com/zh/code-security/codeql-cli)

# codeql 规则编写

codeql 文档 [Writing CodeQL Queries](https://codeql.github.com/docs/writing-codeql-queries/)

## 保留关键字


```
and
any
as
asc
avg
boolean
by
class
concat
count
date
desc
else
exists
extends
false
float
forall
forex
from
if
implies
import
in
instanceof
int
max
min
module
newtype
none
not
or
order
predicate
rank
result
select
strictconcat
strictcount
strictsum
string
sum
super
then
this
true
unique
where
```

## 运算符

```
<
<=
=
>
>=
_
-
,
;
!=
/
.
..
(
)
[
]
{
}
*
%
+
|
```

## 谓词

谓词用于描述组成QL程序的逻辑关系。严格来说，谓词用于计算一组元组，看下面的例子：

```
predicate isCountry(string country) {
  country = "Germany"
  or
  country = "Belgium"
  or
  country = "France"
}

predicate hasCapital(string country, string capital) {
  country = "Belgium" and capital = "Brussels"
  or
  country = "Germany" and capital = "Berlin"
  or
  country = "France" and capital = "Paris"
}
```
谓词 `isCountry` 是一元组集合 `{("Belgium"),("Germany"),("France")}`，谓词 `isCountry` 是二元组集合 ` {("Belgium","Brussels"),("Germany","Berlin"),("France","Paris")}`，通常来说，谓词的集合中的元组拥有相同数量的元组

## 查询语句

基本查询语句 `select xxx`, xxx 为变量，返回 xxx

codeql 典型查询结构如下
```
from /* ... variable declarations ... */
where /* ... logical formulas ... */
select /* ... expressions ... */
```

**当 where 的条件语句过长时，就可以使用谓词，用谓词函数把条件封装起来**

