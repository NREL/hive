import os

rust_environ = os.environ.get("USE_RUST")

if rust_environ is None:
    USE_RUST = False
else:
    USE_RUST = True
