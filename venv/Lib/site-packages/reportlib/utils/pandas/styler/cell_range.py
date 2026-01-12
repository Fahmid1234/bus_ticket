from .cell import Cell

class CellRange:
    def __init__(self, start_row, end_row, start_column, end_column):
        self.start_row = start_row
        self.end_row = end_row
        self.start_column = start_column
        self.end_column = end_column
        
        self.top_left = Cell(start_row, start_column)
        self.top_right = Cell(start_row, end_column)
        self.bottom_left = Cell(end_row, start_column)
        self.bottom_right = Cell(end_row, end_column)
        
        self.rowspan = end_row - start_row + 1
        self.colspan = end_column - start_column + 1
        
    def is_collision_with(self, cell_range):
        return self.top_left.is_in_range(cell_range) or self.top_right.is_in_range(cell_range) or self.bottom_left.is_in_range(cell_range) or self.bottom_right.is_in_range(cell_range)
      
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False