# generateca

生成证书双向证书认证证书

# usage

# 实现

使用 pyOpenSSL 实现证书签发，更多参考 [pyOpenSSL 接口文档](https://www.pyopenssl.org/en/latest/api.html)


[PKey](https://www.pyopenssl.org/en/latest/api/crypto.html#pkey-objects) 生成 DSA 和 RSA 公钥或者密钥对


[X509](https://www.pyopenssl.org/en/latest/api/crypto.html#x509-objects) 生成 X.509 证书


