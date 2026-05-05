import importlib
import pkgutil

for _, modname, _ in pkgutil.iter_modules(__path__):
    if modname == "registry":
        continue
    importlib.import_module(f"{__name__}.{modname}")
