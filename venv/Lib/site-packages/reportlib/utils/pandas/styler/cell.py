class Cell:
    def __init__(self, row, column):
        self.row = row
        self.column = column
        
    def is_in_range(self, cell_range):
        return cell_range.start_row <= self.row <= cell_range.end_row and cell_range.start_column <= self.column <= cell_range.end_column
      
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False