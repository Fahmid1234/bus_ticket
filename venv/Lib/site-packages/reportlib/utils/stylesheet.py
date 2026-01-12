import sys
from os.path import join, exists
from css_html_js_minify import css_minify
from reportlib.utils.templating import template_loader

class StyleSheet:
    def __init__(self):
        self.styles = ['base/styles.css']
        self.load()
        
    def append(self, stylesheet):
        self.styles.append(stylesheet)
        self.load()
        
    def extend(self, stylesheet):
        self.styles.extend(stylesheet)
        self.load()
        
    def load(self, display=True):
        self.loaded_styles = []
        for path in self.styles:
            for folder in template_loader.get_template_dirs():
                _path = join(folder, path)
                if exists(_path):
                    with open(_path, 'r') as f:
                        css = f.read()
                        css = css_minify(css)
                        self.loaded_styles.append(css)
                        if display and 'IPython.display' in sys.modules:
                            from IPython.display import display, HTML
                            display(HTML(f'<style>{css}</style>'))
                    break

