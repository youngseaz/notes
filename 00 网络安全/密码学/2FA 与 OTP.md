# 2FA (Two Factor Authentication)

![alt text](<images/2FA 与 OTP/image.png>)

![alt text](<images/2FA 与 OTP/image-2.png>)

![alt text](<images/2FA 与 OTP/image-1.png>)


# OTP (One-Time Password) 生成

**核心原理**
OTP 算法基于共享密钥（Secret Key）和动态因子（如时间或计数器）生成一次性密码。算法流程如下：
1. 首选计算 `HMAC = HMAC_SHA(Secret Key, Dynamic Factor)`

## HOTP (HMAC-Based One-Time Password)

TOTP (Time-Based One-Time Password Algorithm)



`HOTP(K,C) = Truncate(HMAC-SHA-1(K,C))`

```
Example of HOTP Computation for Digit = 6

   The following code example describes the extraction of a dynamic
   binary code given that hmac_result is a byte array with the HMAC-
   SHA-1 result:

        int offset   =  hmac_result[19] & 0xf ;
        int bin_code = (hmac_result[offset]  & 0x7f) << 24
           | (hmac_result[offset+1] & 0xff) << 16
           | (hmac_result[offset+2] & 0xff) <<  8
           | (hmac_result[offset+3] & 0xff) ;

   SHA-1 HMAC Bytes (Example)

   -------------------------------------------------------------
   | Byte Number                                               |
   -------------------------------------------------------------
   |00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|
   -------------------------------------------------------------
   | Byte Value                                                |
   -------------------------------------------------------------
   |1f|86|98|69|0e|02|ca|16|61|85|50|ef|7f|19|da|8e|94|5b|55|5a|
   -------------------------------***********----------------++|




M'Raihi, et al.              Informational                      [Page 7]

RFC 4226                     HOTP Algorithm                December 2005


   * The last byte (byte 19) has the hex value 0x5a.
   * The value of the lower 4 bits is 0xa (the offset value).
   * The offset value is byte 10 (0xa).
   * The value of the 4 bytes starting at byte 10 is 0x50ef7f19,
     which is the dynamic binary code DBC1.
   * The MSB of DBC1 is 0x50 so DBC2 = DBC1 = 0x50ef7f19 .
   * HOTP = DBC2 modulo 10^6 = 872921.

   We treat the dynamic binary code as a 31-bit, unsigned, big-endian
   integer; the first byte is masked with a 0x7f.

   We then take this number modulo 1,000,000 (10^6) to generate the 6-
   digit HOTP value 872921 decimal.
```

![HOTP](<images/2FA 与 OTP/image-3.png>)

图片来源：https://notes.mengxin.science/2017/05/30/hotp-totp-algorithm-analysis/

# TOTP (Time-Base One-Time Password)

TOTP 算法作为 HOTP 算法的拓展算法

![alt text](<images/2FA 与 OTP/image-4.png>)

图片来源：https://notes.mengxin.science/2017/05/30/hotp-totp-algorithm-analysis/



# OTP 校验

## HOTP 校验

同步 counter 步骤
1. 生成 OTP（客户端和服务器端的共同步骤）
客户端请求 OTP 时，使用当前 counter（开始时为 0 或其他初始化值）来生成 OTP。
客户端生成 OTP 后，将 counter 和 OTP 一起发送到服务器。
1. 服务器验证 OTP
服务器接收到 OTP 和 counter 后，检查其与预期的 OTP 是否匹配。
如果匹配，则验证成功，递增 counter 并处理该请求。
如果不匹配，服务器可以尝试通过增加或减少 counter 的值（例如，counter + 1, counter - 1）进行验证，以容忍可能的同步误差。
1. 误差窗口
服务器可能会有一个误差窗口（例如，counter = N, counter = N-1, counter = N+1 等），允许一定范围内的计数器误差。
通过验证多个可能的计数器值，系统可以容忍一些同步问题，确保 OTP 校验的准确性。
1. 客户端和服务器的同步
如果服务器校验失败，并且未能在误差窗口内找到有效的 OTP，客户端需要重新生成 OTP 或者请求新的 OTP。
确保客户端和服务器都更新并同步 counter，防止 OTP 重复使用。

## TOTP 校验
TOTP 的核心公式是将时间戳（秒级）通过除法离散化：

counter = current_time // time_step
* current_time 是从 Unix 纪元（1970-01-01 00:00:00 UTC）起的当前时间戳（以秒为单位）。
* time_step 是固定的时间间隔，通常为 30 秒。

假设时间戳为 1，时间步长为 30 秒：

在第 1 到 29 时间步内，客户端和服务器的计数器值都是 0 。


**问题1：时间不同步导致校验失败**

如果客户端和服务器的时间有偏差（例如 5 秒偏差），生成的 OTP 会基于不同的 counter，从而导致校验失败。
客户端在时间戳 29 时生成的 OTP，服务器在时间戳 34 校验时可能失败，因为它会只验证计数器 1，而不是计数器 0。

**问题2：严格绑定时间步导致用户体验差**
用户需要在单一时间步内使用 OTP。如果用户生成 OTP（如在时间戳 29）后，延迟输入到服务器（如在时间戳 31），OTP 校验就会失败。
这对于实际操作来说过于严格，容易让用户体验变差。


**解决方案1：引入时间窗口**
在 verify_totp 函数中，通过在校验时检查当前时间步的前后时间步（T-1, T, T+1），可以引入时间窗口容忍。这是 TOTP 标准推荐的做法。

**解决方案2：显式 counter 校验**
通过显式传递 counter 的方式，客户端和服务器可以协商如何处理时间步，例如允许客户端显式发送自己生成 OTP 时使用的计数器值，服务器据此判断是否接近当前时间步，从而进行更宽松的校验。


# OTP 安全问题

![alt text](<images/2FA 与 OTP/image-5.png>)

图片来源：https://notes.mengxin.science/2017/05/30/hotp-totp-algorithm-analysis/



# 示例

![alt text](<images/2FA 与 OTP/image-6.png>)

二维码识别内容：`otpauth://totp/JumpServer:admin?secret=LZEKNECB4XSNKUD4&issuer=JumpServer`

# 相关参考

1. [RFC4266 (HOTP: An HMAC-Based One-Time Password Algorithm)](https://datatracker.ietf.org/doc/html/rfc4226)
2. [RFC6238 (TOTP: Time-Based One-Time Password Algorithm)](https://datatracker.ietf.org/doc/html/rfc6238)