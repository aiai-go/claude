from .version import VERSION, APP_NAME, APP_NAME_EN
from .cli import run
from .agent import ChineseAgent, quick_query, PRESET_AGENTS
from .backend import detect_backend, SDKBackend, APIBackend

__version__ = VERSION
