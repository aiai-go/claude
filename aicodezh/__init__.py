from .version import VERSION, APP_NAME, APP_NAME_EN
from .cli import run
from .agent import ChineseAgent, quick_query, PRESET_AGENTS
from .backend import detect_backend, SDKBackend, APIBackend
from .skills import SKILLS, get_enabled_skills, toggle_skill

__version__ = VERSION
