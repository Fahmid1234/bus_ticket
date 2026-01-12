import sys
from uuid import uuid4

import htmlmin
import yaml

from reportlib.utils.pandas.styler import Styler
from reportlib.utils.templating import template_loader
from reportlib.utils.stylesheet import StyleSheet
from premailer import transform


class Report:
    def __init__(self,
                 template_name='base/base.html',
                 styles=None,
                 title=None, extra=None, context=None):
        self.template_name = template_name
        
        self.stylesheet = StyleSheet()
        if isinstance(styles, str):
            self.stylesheet.append(styles)
        elif isinstance(styles, list):
            self.stylesheet.extend(styles)
        
        self.title = title
        self.extra = extra
        self.tables = []
        self.context = context or {}
        
    @property
    def _format_context(self):
        return {
            **self.context,
            'title': self.title,
        }
        
    @property
    def _render_context(self):
        return {
            **self.context,
            'title': self.title,
            'extra': self.extra,
            'tables': self.tables,
            'styles': self._load_styles(),
        }

    def add_table(self, stylers):
        if isinstance(stylers, Styler):
            self.tables.append(stylers)
        elif isinstance(stylers, (list, tuple)):
            if len(stylers) == 1:
                self.add_table(stylers[0])
            else:
                for i, styler in enumerate(stylers):
                    if i > 0:
                        styler.skip_table_open_tag = True
                    if i < len(stylers) - 1:
                        styler.skip_table_close_tag = True
                    self.tables.append(styler)
        else:
            raise ValueError('`styler` must be an instance of `reportlib.utils.pandas.styler.Styler` or a list of them')
            
    def add_grouped_table(self, stylers):
        print('add_grouped_table was deprecated in version 3.2, use add_table instead')
        self.add_table(stylers)
        
    def _load_styles(self):
        self.stylesheet.load(display=False)
        return self.stylesheet.loaded_styles

    def render(self):
        template = template_loader.get_template(self.template_name)
        html_string = template.render(self._render_context)
        html_string = htmlmin.minify(
            html_string,
            remove_comments=True,
            remove_empty_space=True,
            reduce_boolean_attributes=True,
            reduce_empty_attributes=True,
            remove_optional_attribute_quotes=True,
            convert_charrefs=True,
        )
        html_string = transform(
            html_string,
            disable_validation=True,
            remove_classes=True,
            disable_leftover_css=True,
        )
        return html_string
      
    def run(self):
        print('run() was deprecated in version 3.3, use render() instead')

    def show(self):
        if 'IPython.display' in sys.modules:
            from IPython.display import display, HTML
            html_string = self.render()
            display(HTML(html_string))