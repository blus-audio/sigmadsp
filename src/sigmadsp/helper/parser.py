import logging
from typing import List


class Cell:
    adjustable_prefix = "adjustable_"
    volume_identifier = "volume"

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
    def is_adjustable_cell(self) -> bool:
        """Determine, whether this is a user adjustable cell

        Returns:
            bool: True, if adjustable, False otherwise.
        """
        return self.name.startswith(Cell.adjustable_prefix)

    @property
    def is_adjustable_volume_cell(self):
        """Determine, whether this is an adjustable volume cell

        Returns:
            bool: True, if an adjustable volume cell, False otherwise.
        """
        try:
            self.parameter_value

        except AttributeError:
            return False

        else: 
            return self.is_adjustable_cell and (Cell.volume_identifier in self.name)


class Parser:
    def run(self, file_name: str):
        """Parse an input file that was exported from Sigma Studio

        Args:
            file_name (str): [description]
        """
        self.cells = []
        self.cell: Cell = None

        if not file_name.endswith(".params"):
            logging.error("The parameter file is not a *.params file! Aborting.")

        else:
            try:
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

            except FileNotFoundError:
                logging.info(f"Parameter file {file_name} not found.")

    @property 
    def volume_cells(self) -> List[Cell]:
        """Returns all cells that can be used for volume adjustment.
        These are user defined with a certain name pattern.

        Returns:
            List[Cell]: The list of adjustable volume cells
        """
        collected_cells = []
        for cell in self.cells:
            if cell.is_adjustable_volume_cell:
                collected_cells.append(cell)
        
        return collected_cells
