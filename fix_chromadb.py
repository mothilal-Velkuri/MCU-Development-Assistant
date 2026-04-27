import os
import chromadb

chroma_dir   = os.path.dirname(chromadb.__file__)
posthog_file = os.path.join(
    chroma_dir, "telemetry", "product", "posthog.py"
)
base_file = os.path.join(
    chroma_dir, "telemetry", "product", "__init__.py"
)

# Read and print base class to see exact signature
print("Base class __init__.py contents:")
with open(base_file, "r") as f:
    print(f.read())

# Write fix with **kw included
dummy = '''from overrides import override
from chromadb.telemetry.product import (
    ProductTelemetryClient,
    ProductTelemetryEvent,
)
from chromadb.config import System


class Posthog(ProductTelemetryClient):
    def __init__(self, system: System) -> None:
        super().__init__(system)

    @override
    def capture(self, event: ProductTelemetryEvent, **kw) -> None:
        pass
'''

with open(posthog_file, "w", encoding="utf-8") as f:
    f.write(dummy)

print(f"\nReplaced: {posthog_file}")
print("Done.")