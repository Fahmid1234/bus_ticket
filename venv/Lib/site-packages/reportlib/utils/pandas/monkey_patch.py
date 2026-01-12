import sys
from pandas import DataFrame


def patch_pandas():
    def show(self, *args, **kwargs):
        if 'IPython.display' in sys.modules:
            from IPython.display import display, HTML
            display(HTML(self.to_html(*args, **kwargs)))

    DataFrame.show = show

    
def patch():
    patch_pandas()
