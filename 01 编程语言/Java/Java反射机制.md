
# 什么是 Java 反射

反射就是把 Java 类中的各种属性、方法映射成对应的 Java 对象。Java反射机制是在运行状态中，对于任意一个类，都能够知道这个类的所有属性和方法；对于任意一个对象，都能够调用它的任意一个方法和属性；这种动态获取的信息以及动态调用对象的方法的功能称为java语言的反射机制。


如一个类有： 

```java
import java.lang.reflect.*;

 
   public class DumpMethods {
      public static void main(String args[])
      {
         try {
            Class c = Class.forName(args[0]);
            Method m[] = c.getDeclaredMethods();
            for (int i = 0; i < m.length; i++)
            System.out.println(m[i].toString());
         }
         catch (Throwable e) {
            System.err.println(e);
         }
      }
   }
```

输出结果如下
```
E:\programes_demo>java Reflect java.util.Stack
public boolean java.util.Stack.empty()
public synchronized java.lang.Object java.util.Stack.peek()
public synchronized int java.util.Stack.search(java.lang.Object)
public java.lang.Object java.util.Stack.push(java.lang.Object)
public synchronized java.lang.Object java.util.Stack.pop()
```

# Java 反射原理

>[Class (java.lang.Class) 类](https://docs.oracle.com/javase/8/docs/api/java/lang/Class.html)实例表示Java运行程序的类和接口，Java 基础数据类型：boolean、byte、char、short、int、long、float、double 以及保留关键字 void 都用 Class 对象表示。

[运行时类型信息（Runtime type information，RTTI）](https://zh.wikipedia.org/wiki/%E5%9F%B7%E8%A1%8C%E6%9C%9F%E5%9E%8B%E6%85%8B%E8%A8%8A%E6%81%AF)：在程序执行时保存其对象的类型信息的行为。在 Java 程序设计中，Claas 类用来保存 RTTI。

关于 Class 类，有如下特性：
- Class 类的实例内容就是你创建出来的类的类型信息，如你创建了一个 AClass 的类，那么 Java 就会生成一个关于 AClass 的 Class 实例
- Class 类不能像普通类那样，用关键字 new 来创建实例对象，它只能又 JVM 创建

通过前面的了解，Class 类可以帮助我们在程序运行时分析类，获取类的属性、方法、装饰器、构造器、类名等 




# Java 反射的应用

## 用于免杀恶意程序

 

# 参考

1. [Using Java Reflection](https://www.oracle.com/technical-resources/articles/java/javareflection.html)

 

