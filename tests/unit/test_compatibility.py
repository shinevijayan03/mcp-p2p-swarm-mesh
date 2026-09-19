"""Test TC-NFR01-01: Python 3.10+ typing and runtime environment."""

import sys
import pytest

def test_python_runtime_version():
    """Verify runtime is Python 3.10+ as required by NFR-01."""
    assert sys.version_info >= (3, 10), "System requires Python 3.10 or higher"

def test_type_annotations_available():
    """Verify modern typing constructs are available and importable."""
    from mcp_mesh.registry.models import PeerNodeRecord, MeshToolDefinition
    assert hasattr(PeerNodeRecord, "model_fields")
    assert hasattr(MeshToolDefinition, "model_fields")
