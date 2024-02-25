import os
import ssl
from OpenSSL import crypto, SSL


cwd = os.path.dirname(__file__)

ORGANIZATION = "youngseaz.com"
COMMON_NAME  = "localhost:8090"
COUNTRY		 = "CN"
DURATION	 = 365 * 24 * 60 * 60 * 10
KEYFILE		 = os.path.join(cwd, "privatekey.pem")
CERTFILE	 = os.path.join(cwd, "cert.pem")

def generate_certificate():
	pkey = crypto.PKey()
	pkey.generate_key(crypto.TYPE_RSA, 4096)

	cert = crypto.X509()
	cert.get_subject().C = COUNTRY
	cert.get_subject().O = ORGANIZATION
	cert.get_subject().CN = COMMON_NAME
	cert.gmtime_adj_notBefore(0)
	cert.gmtime_adj_notAfter(DURATION)
	cert.set_issuer(cert.get_subject())
	cert.set_pubkey(pkey)
	cert.sign(pkey, 'sha512')

	with open(KEYFILE, "w+") as keyfile:
		keyfile.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey).decode("utf-8"))
	with open(CERTFILE, "w+") as certfile:
		certfile.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"))
		

def generate_csr():
	req = crypto.X509Req()
	



def generateca():
	key_file = "server.key"
	csr_file = "server.csr"
	ssl_context = ssl.create_default_context()
	ssl_context.load_cert_chain(certfile=key_file, keyfile=key_file)
	ssl_context.load_verify_locations(cafile='ca.crt')
	with open(csr_file, 'wb') as f:
		f.write(ssl_context.get_cpe_request())


if __name__ == '__main__':
	generate_certificate()
	#generateca()
