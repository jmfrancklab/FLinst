import os
import subprocess

def should_compile_spincore():
    required_env_vars = ["conda_headers", "numpy"]
    return all(var in os.environ for var in required_env_vars)

if should_compile_spincore():
    subprocess.run(["meson", "setup", "builddir"], check=True)
    subprocess.run(["meson", "compile", "-C", "builddir"], check=True)
    subprocess.run(["meson", "install", "-C", "builddir"], check=True)
else:
    print("Skipping SpinCore_pp compilation due to missing environment variables.")
