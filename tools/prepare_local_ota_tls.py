"""Create a private LAN OTA trust anchor; never print private keys or URL tokens."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import ipaddress,json,secrets
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'config/ota_tls.local';folder.mkdir(exist_ok=True)
configuration=ROOT/'config/ota-fr08.local.json'
existing=json.loads(configuration.read_text()) if configuration.exists() else {}
host=existing.get('host','192.168.1.6');port=existing.get('port',8873);now=datetime.now(timezone.utc)
if not (folder/'ca.pem').exists():
    ca_key=ec.generate_private_key(ec.SECP256R1());server_key=ec.generate_private_key(ec.SECP256R1())
    ca_name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'KU Watch Private LAN OTA CA')])
    ca=(x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=365)).add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True).add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=False,content_commitment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=None,decipher_only=None),critical=True).sign(ca_key,hashes.SHA256()))
    server=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,host)])).issuer_name(ca_name).public_key(server_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=90)).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(host)),x509.DNSName(host)]),critical=False).add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(ca_key,hashes.SHA256()))
    for name,obj in [('ca',ca),('server',server)]:
        (folder/(name+'.pem')).write_bytes(obj.public_bytes(serialization.Encoding.PEM))
    for name,key in [('ca',ca_key),('server',server_key)]:
        (folder/(name+'.key')).write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
if not configuration.exists():configuration.write_text(json.dumps({'capability':secrets.token_hex(32),'version':'2.0.10','host':host,'port':port}),'utf8')
server=x509.load_pem_x509_certificate((folder/'server.pem').read_bytes())
if host not in server.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName):
    ca=x509.load_pem_x509_certificate((folder/'ca.pem').read_bytes())
    ca_key=serialization.load_pem_private_key((folder/'ca.key').read_bytes(),None)
    server_key=serialization.load_pem_private_key((folder/'server.key').read_bytes(),None)
    server=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,host)])).issuer_name(ca.subject).public_key(server_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=90)).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(host)),x509.DNSName(host)]),critical=False).add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(ca_key,hashes.SHA256()))
    (folder/'server.pem').write_bytes(server.public_bytes(serialization.Encoding.PEM))
ca=(folder/'ca.pem').read_text()
header='#pragma once\n// Public trust anchor for the private LAN OTA service; no private key or URL token.\nnamespace LocalOta {\nconstexpr const char* PREFIX="https://'+host+':'+str(port)+'/";\nconstexpr const char* CA=R"KUOTA('+ca+')KUOTA";\n}\n'
(ROOT/'include/ota_local_ca.h').write_text(header,'utf8')
print(json.dumps({'private_lan_host':host,'port':port,'public_trust_header':'include/ota_local_ca.h','private_keys_logged':False,'private_token_logged':False}))
