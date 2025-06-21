import sys
import os
try:
    from desafio.columns_solver import Columns as ColumnsBase
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from columns_solver import Columns as ColumnsBase

class Columns(ColumnsBase):
    pass
