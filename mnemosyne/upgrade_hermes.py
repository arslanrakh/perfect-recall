"""Compatibility notice for the retired upstream package updater."""
def upgrade_command(args=None):
    print("Upgrade PerfectRecall using the Python environment that runs Hermes:")
    print("python -m pip install --upgrade git+https://github.com/arslanrakh/perfectrecall.git")
    return 0
