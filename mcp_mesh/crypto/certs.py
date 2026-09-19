"""In-memory TLS X.509 certificate generation with Ed25519 identity."""

import datetime
from typing import Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization
from mcp_mesh.crypto.identity import NodeIdentity

class CertificateAuthority:
    """Generates self-signed X.509 certificates bound to Ed25519 node identities."""

    @staticmethod
    def generate_self_signed_cert(identity: NodeIdentity) -> Tuple[bytes, bytes]:
        """Returns (cert_pem_bytes, private_key_pem_bytes)."""
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, identity.node_id),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "mcp-p2p-swarm-mesh"),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        san = x509.SubjectAlternativeName([
            x509.UniformResourceIdentifier(f"mcp-node:{identity.node_id}"),
            x509.DNSName("localhost"),
            x509.IPAddress(datetime.ip_address("127.0.0.1") if hasattr(datetime, "ip_address") else __import__("ipaddress").ip_address("127.0.0.1")),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(identity._public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5))
            .not_valid_after(now + datetime.timedelta(days=3))
            .add_extension(san, critical=False)
            .sign(identity._private_key, algorithm=None)
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = identity._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cert_pem, key_pem
