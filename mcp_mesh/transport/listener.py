"""TLS Listener for incoming peer connections."""

import asyncio
import os
import ssl
import tempfile
from typing import Any, Callable, Optional
from mcp_mesh.crypto.identity import NodeIdentity
from mcp_mesh.crypto.certs import CertificateAuthority

class MeshListener:
    """Async TLS server accepting incoming peer connections."""

    def __init__(
        self,
        host: str,
        port: int,
        identity: NodeIdentity,
        connection_handler: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Any],
    ):
        self.host = host
        self.port = port
        self.identity = identity
        self.connection_handler = connection_handler
        self._server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        """Starts the TLS TCP server."""
        cert_pem, key_pem = CertificateAuthority.generate_self_signed_cert(self.identity)
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as cf, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".key") as kf:
            cf.write(cert_pem)
            cf.flush()
            kf.write(key_pem)
            kf.flush()
            c_path = cf.name
            k_path = kf.name

        try:
            ssl_ctx.load_cert_chain(c_path, k_path)
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

            self._server = await asyncio.start_server(
                self.connection_handler,
                self.host,
                self.port,
                ssl=ssl_ctx,
            )
        finally:
            if os.path.exists(c_path):
                os.unlink(c_path)
            if os.path.exists(k_path):
                os.unlink(k_path)

    async def stop(self) -> None:
        """Stops the TLS TCP server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
