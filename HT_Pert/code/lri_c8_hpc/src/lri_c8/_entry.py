"""Lightweight entry point for both `python -m lri_c8` and the installed `lri-c8` command:
provisional graceful-stop handlers are installed before numpy/numba/scipy are imported."""
def main(argv=None):
    from . import _signals
    _signals.install()
    from .cli import main as cli_main
    return cli_main(argv)
