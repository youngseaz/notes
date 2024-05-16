
visual studio 只支持 32 位程序的内联汇编，64 位程序汇编需要加扩展程序

32 位内联汇编可使用关键字 `__asm` 声明汇编代码，demo 如下：

```c
#include<stdio.h>

int main()
{
	char str[] = "abcdefghijk";
	char* b;
	__asm
	{
		lea edi, str
		add edi, 1
		mov b, edi
	}
	printf("%s", b);
}

// result is: bcdefghijk
```