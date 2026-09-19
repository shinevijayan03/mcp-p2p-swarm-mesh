"""Node cryptographic identity using Ed25519 keypairs."""

import hashlib
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

class NodeIdentity:
    """Ed25519 node cryptographic identity."""

    def __init__(self, private_key_hex: Optional[str] = None):
        if private_key_hex is not None:
            raw_bytes = bytes.fromhex(private_key_hex)
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
        else:
            self._private_key = ed25519.Ed25519PrivateKey.generate()

        self._public_key = self._private_key.public_key()
        raw_pub = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self._pub_hex = raw_pub.hex()
        digest = hashlib.sha256(raw_pub).hexdigest()[:16]
        self._node_id = f"node_{digest}"

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def public_key_hex(self) -> str:
        return self._pub_hex

    @property
    def private_key_hex(self) -> str:
        raw_priv = self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return raw_priv.hex()

    def sign(self, message: bytes) -> bytes:
        """Sign bytes using Ed25519 private key."""
        return self._private_key.sign(message)

    def verify(self, message: bytes, signature: bytes, public_key_hex: Optional[str] = None) -> bool:
        """Verify signature using local or provided public key."""
        try:
            if public_key_hex:
                pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
            else:
                pub = self._public_key
            pub.verify(signature, message)
            return True
        except (InvalidSignature, Exception):
            return False
