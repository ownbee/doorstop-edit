from pkg_resources import DistributionNotFound, get_distribution

__project__ = "doorstop-edit"

try:
    __version__ = get_distribution(__project__).version
except DistributionNotFound:
    __version__ = "(local)"
