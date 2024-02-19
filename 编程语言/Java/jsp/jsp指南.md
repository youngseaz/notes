
# 什么是jsp

1. Java Server Pages(JSP) is a technology that helps software developers create dynamically generated web pages based on HTML. Released in 1999 by Sun Microsystems.
2. JSP 是由Java Servlets发展而来。JSP文件经过程序的处 理（称之为“JSP解析器”或者“JSP引擎”，其实就是一些Java程 序），最终会被翻译成为Java Servlet代码，然后再编译执行。
3. 目前支持JSP的引擎有很多，牛B的人自己都可以写一套出来，最 常见的Tomcat、WebLogic、WebSphere、Resin等。JSP技术非 常成熟，而且使用广泛。目前JSP规范已经发展到了2.1版本。
4. 与JSP类似的还有ASP、PHP，但是JSP算是后起之秀，几乎拥有 Java的一切优点，使用方便，性能良好。

**优势** 
 
JSP是HTML和Java Servlets的结合体。它可以动态地生成网 页，而且可以使用原生Java语法，可以和HTML混合编程

# jsp调测环境部署

1、下载 [jdk1.8](https://www.oracle.com/java/technologies/javase/javase8-archive-downloads.html)，建议下载免安装版本

2、下载 [ tomcat](https://tomcat.apache.org/)，建议下载免安装版本，window执行bin目录下的 startup.bat 启动 tomcat

# jsp知识

## jsp基本语法

JSP的内置对象

对象|描述
-|-
request|HttpServletRequest类的实例
response|HttpServletResponse类的实例
out|PrintWriter类的实例，用于把结果输出至网页上
session|HttpSession类的实例
application|ServletContext类的实例，与应用上下午有关
config|ServletConfig类的实例
pageContext|PageContext类的实例，提供对JSP页面所有对象以及命名空间的访问
page|类似于Java类中的this关键字
exception|Exception类的对象，代表发生错误的JSP页面中对应的异常对象



