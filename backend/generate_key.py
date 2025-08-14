from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate a new RSA private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Serialize the private key to PEM format
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Get the public key and serialize it
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Write private key to file
with open('keys/kt_private_key.pem', 'wb') as f:
    f.write(private_pem)

# Write public key to file
with open('keys/kt_public_key.pem', 'wb') as f:
    f.write(public_pem)

print("Private key generated successfully!")
print("Public key generated successfully!")
print("Files created:")
print("- keys/kt_private_key.pem")
print("- keys/kt_public_key.pem")