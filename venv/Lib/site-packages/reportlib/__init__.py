from .report import Report
from .utils.pandas import Styler
from .utils.config_parser import ConfigParser
from .utils.templating import template_loader

add_template_dir = template_loader.add_template_dir