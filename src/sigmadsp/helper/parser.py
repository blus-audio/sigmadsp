"""A module that parses SigmaStudio project files and extracts adjustable cells
"""
import logging
from typing import List, Union


class Cell:
    """A cell object is a unit, which represents a cell from SigmaStudio."""

    adjustable_prefix = "adjustable_"
    volume_identifier = "volume"

    def __init__(self, name: List[str]):
        """Initializes a new cell.

        Args:
            name (List[str]): The name of the cell, as a list of string tokens.
        """
        self.name = name

        # The value of the parameter that is stored in this cell
        self.parameter_value: Union[int, float] = None

        # The address of the parameter in the DSP's memory
        self.parameter_address: int = None

        # The name of the parameter
        self.parameter_name: str = None

    @property
    def is_adjustable_cell(self) -> bool:
        """Determine, whether this is a user adjustable cell.

        Returns:
            bool: True, if adjustable, False otherwise.
        """
        return self.name.startswith(Cell.adjustable_prefix)

    @property
    def is_adjustable_volume_cell(self):
        """Determine, whether this is an adjustable volume cell.

        Returns:
            bool: True, if an adjustable volume cell, False otherwise.
        """
        if self.parameter_value is not None:
            return self.is_adjustable_cell and (Cell.volume_identifier in self.name)

        return False


class Parser:
    """Parses a parameter input file from Sigma Studio and detects cells in it."""

    def __init__(self):
        # A list of cells, to be filled with inputs from a file.
        self.cells: List[Cell] = []

    def run(self, file_path: str):
        """Parse an input file that was exported from Sigma Studio

        Args:
            file_path (str): The path to the input file
        """
        self.cells.clear()

        if not file_path.endswith(".params"):
            logging.error("The parameter file is not a *.params file! Aborting.")
            return

        # Proceed with opening the file
        try:
            with open(file_path, "r", encoding="utf8") as file:
                logging.info("Using parameter file path %s.", file_path)
                lines = file.readlines()

                cell: Cell = None

                for line in lines:
                    split_line = line.split()

                    if split_line:
                        if split_line[0] == "Cell" and split_line[1] == "Name":
                            name = " ".join(split_line[3:])
                            cell = Cell(name)
                            self.cells.append(cell)

                        elif split_line[0] == "Parameter":

                            if split_line[1] == "Name":
                                cell.parameter_name = " ".join(split_line[3:])

                            if split_line[1] == "Address":
                                cell.parameter_address = int(split_line[3])

                            if split_line[1] == "Value":
                                data = split_line[3]

                                try:
                                    cell.parameter_value = int(data)

                                except ValueError:
                                    cell.parameter_value = float(data)

                logging.info("Found a total number of %d cells.", len(self.cells))

        except FileNotFoundError:
            logging.info("Parameter file %s not found.", file_path)

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
