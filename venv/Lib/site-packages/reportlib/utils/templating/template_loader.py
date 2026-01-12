import os
from os.path import dirname, join, exists, abspath

import pandas as pd
from jinja2 import Environment, FileSystemLoader

__all__ = ['template_loader']


class TemplateLoader:
    def __init__(self):
        template_dirs = {
            join(dirname(__file__), 'templates'),
            join(dirname(pd.__file__), 'io', 'formats', 'templates'),
        }
        loader = FileSystemLoader(template_dirs)
        self.env = Environment(loader=loader, trim_blocks=True)

    def get_template(self, template_name):
        return self.env.get_template(template_name)
      
    def add_template_dir(self, template_dir):
        self.env.loader.searchpath.append(abspath(template_dir))
        
    def get_template_dirs(self):
        return list(self.env.loader.searchpath)

template_loader = TemplateLoader()
