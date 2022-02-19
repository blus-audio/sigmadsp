import logging
from typing import List


class Cell:
    @property
    def parameter_value(self):
        return self._parameter_value

    @parameter_value.setter
    def parameter_value(self, new_parameter_value: int):
        self._parameter_value = new_parameter_value

    @property
    def parameter_address(self):
        return self._parameter_address

    @parameter_address.setter
    def parameter_address(self, new_parameter_address: int):
        self._parameter_address = new_parameter_address

    @property
    def parameter_name(self):
        return self._parameter_name

    @parameter_name.setter
    def parameter_name(self, new_parameter_name: str):
        self._parameter_name = new_parameter_name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name: List[str]):
        self._name = new_name

    @property
    def is_adjustable_cell(self):
        return self.name.startswith("adjustable_")

    @property
    def is_adjustable_volume_cell(self):
        try:
            self.parameter_value

        except AttributeError:
            return False

        else: 
            return self.is_adjustable_cell and ("volume" in self.name)


class Parser:
    def run(self, file_name: str):
        self.cells = []
        self.cell: Cell = None

        with open(file_name, "r") as file:
            logging.info(f"Using parameter file path {file_name}.")
            lines = file.readlines()

            for line in lines:
                split_line = line.split()
                
                if split_line:
                    if split_line[0] == "Cell" and split_line[1] == "Name":
                        self.cell = Cell()
                        self.cells.append(self.cell)

                        self.cell.name = " ".join(split_line[3:])

                    elif split_line[0] == "Parameter":

                        if split_line[1] == "Name":
                            self.cell.parameter_name = " ".join(split_line[3:])

                        if split_line[1] == "Address":
                            self.cell.parameter_address = int(split_line[3])
                            
                        if split_line[1] == "Value":
                            data = split_line[3]
                            
                            try:
                                self.cell.parameter_value = int(data)
                            
                            except ValueError:
                                self.cell.parameter_value = float(data)
            
            logging.info(f"Found a total number of {len(self.cells)} cells.")

    @property 
    def volume_cells(self) -> List[Cell]:
        cells = []
        for cell in self.cells:
            if cell.is_adjustable_volume_cell:
                cells.append(cell)
        
        return cells

# for cell in p.cells:
#     if cell.is_adjustable_volume_cell:
#         print(cell.name)
#         print(cell.parameter_address)