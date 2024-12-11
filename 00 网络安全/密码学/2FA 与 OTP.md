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
   

![alt text](<images/2FA 与 OTP/image-5.png>)

图片来源：https://notes.mengxin.science/2017/05/30/hotp-totp-algorithm-analysis/


# OTP 校验

## HOTP 校验

## TOTP 校验


# OTP 安全问题



# 示例

![alt text](<images/2FA 与 OTP/image-6.png>)

二维码识别内容：`otpauth://totp/JumpServer:admin?secret=LZEKNECB4XSNKUD4&issuer=JumpServer`

# 相关参考

1. [RFC4266 (HOTP: An HMAC-Based One-Time Password Algorithm)](https://datatracker.ietf.org/doc/html/rfc4226)
2. [RFC6238 (TOTP: Time-Based One-Time Password Algorithm)](https://datatracker.ietf.org/doc/html/rfc6238)