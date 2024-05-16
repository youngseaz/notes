 
# 官方文档

官方文档见 [CodeQL library for Java/Kotlin](https://codeql.github.com/codeql-standard-libraries/java/index.html)，文档描述了全量 codeql 使用的 Java/Kotlin API 

# 规则编写

## 查询规则

基本查询语句 `select xxx`, xxx 为变量，返回 xxx

codeql 典型查询结构如下
```
from /* ... variable declarations ... */
where /* ... logical formulas ... */
select /* ... expressions ... */
```

demo 如下，首先 from 语句声明类型为 Method 的变量 m ，where 语句判断方法 m 是否被名为 GetMapping 的注解标记，select 语句返回

```
import java

from Method m
where m.getAnAnnotation().getType().hasName("GetMapping")
select m
```

常用的查询 API 

类名|方法及功能
:-|:-
Call|get 

- call
  - s 



