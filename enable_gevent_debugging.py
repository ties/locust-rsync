# Gevent hangs during monkey patching when a debugger is attached
# Source this file before importing locust when you want to use a debugger
# Original code by ayzerar at https://github.com/Microsoft/PTVS/issues/2390

from gevent import monkey

monkey.patch_all()


def setup_ptvsd(host="0.0.0.0", port=5678):
    import sys

    saved_modules = {}
    try:
        green_modules = set(
            [
                "socket",
                "ssl",
                "select",
                "urllib",
                "thread",
                "threading",
                "time",
                "logging",
                "os",
                "signal",
                "subprocess",
                "requests",
            ]
        )
        for modname in list(sys.modules.keys()):
            if modname.partition(".")[0] in green_modules:
                saved_modules[modname] = sys.modules.pop(modname)

        import debugpy  # pylint: disable=W0611

        debugpy.listen((host, port))
        debugpy.wait_for_client()
    finally:
        sys.modules.update(saved_modules)


setup_ptvsd()
