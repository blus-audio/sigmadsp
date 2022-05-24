"""A module that parses SigmaStudio project files and extracts adjustable cells."""
import logging
from dataclasses import dataclass
from itertools import dropwhile, takewhile
from typing import ClassVar, List, Union

# A logger for this module
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Cell:
    """A cell object is a unit, which represents a cell from SigmaStudio."""

    # The full name of the cell (e.g. 'adjustable_volume_main_left').
    full_name: str

    # The register address of the parameter.
    parameter_address: int

    # The name of the parameter, as defined in SigmaStudio.
    parameter_name: str

    # The value of the parameter, if any.
    parameter_value: Union[int, float, None]

    # This string separates prefixes within a cell name.
    PREFIX_SEPARATOR: ClassVar[str] = "_"

    # The prefix that marks a cell as adjustable.
    ADJUSTABLE_PREFIX: ClassVar[str] = "adjustable"

    # If a parameter carries this description in its name, it is a register that can be adjusted externally.
    # This is in contrast to parameters that are marked with "alpha".
    TARGET_PARAMETER: ClassVar[str] = "target"

    # The cell name prefix for cells that adjust volume.
    VOLUME_PREFIX: ClassVar[str] = "volume"

    # The cell name for a safety hash.
    SAFETY_HASH: ClassVar[str] = "safety_hash"

    # A complete list of valid prefixes, which are understood by the parser.
    VALID_PREFIX_TOKENS: ClassVar[List[str]] = [ADJUSTABLE_PREFIX, VOLUME_PREFIX]

    @property
    def full_name_tokens(self) -> List[str]:
        """Extract the separated full name, where the separator string is removed.

        For example 'adjustable_volume_main_left' is converted to ['adjustable', 'volume', 'main', 'left']

        Returns:
            List[str]: The list of tokens in the full name.
        """
        return self.full_name.split(Cell.PREFIX_SEPARATOR)

    @property
    def name_tokens(self) -> List[str]:
        """Return the name tokens of the cell without prefix tokens.

        For example ['main', 'left'] for a full cell name 'adjustable_volume_main_left'.

        Returns:
            str: The unprefixed cell name, if prefix tokens exist. The 'full_name_tokens' otherwise.
        """
        if self.prefix_tokens is None:
            return self.full_name_tokens

        return self.full_name_tokens[len(self.prefix_tokens) :]

    @property
    def prefix_tokens(self) -> List[str]:
        """Return only the prefix tokens of the cell.

        For example ['adjustable', 'volume'] for a full cell name 'adjustable_volume_main_left'.

        Returns:
            Union[List[str], None]: The list of tokens, if they are valid prefixes, None otherwise.
        """
        if Cell.PREFIX_SEPARATOR in self.full_name:
            return [prefix for prefix in self.full_name_tokens if prefix in Cell.VALID_PREFIX_TOKENS]

        else:
            return []

    @property
    def is_adjustable(self) -> bool:
        """Determine, whether the cell is adjustable.

        Returns:
            bool: True, if adjustable, False otherwise.
        """
        return Cell.ADJUSTABLE_PREFIX in self.prefix_tokens

    @property
    def is_safety_hash(self) -> bool:
        """Determine, whether the cell contains a safety hash.

        Returns:
            bool: True, if it does, False otherwise.
        """
        return self.full_name == Cell.SAFETY_HASH

    @property
    def is_volume_cell(self) -> bool:
        """Determine, whether the cell is an adjustable volume cell.

        Returns:
            bool: True, if it is an adjustable volume cell, False otherwise.
        """
        return (
            self.is_adjustable
            and (Cell.VOLUME_PREFIX in self.prefix_tokens)
            and (Cell.TARGET_PARAMETER in self.parameter_name)
        )


class Parser:
    """Parse a parameter input file from Sigma Studio and detects cells in it."""

    def __init__(self):
        """Initialize the parameter file parser with an empty list of cells."""
        self.cells: List[Cell] = []

    def extract_cell(self, cell_lines: List[str]) -> Union[Cell, None]:
        """Read a block of data from the parameter listing, and creates a new Cell from it.

        Args:
            cell_lines (List[str]): The lines from the listing to read from.

        Returns:
            Union[Cell, None]: The new Cell, if the data from the listing is valid, None otherwise.
        """
        parameter_value: Union[float, int, None] = None
        parameter_name: str
        parameter_address: int

        for line in cell_lines:
            # Assemble a cell from the information in the cell_lines
            split_line = line.split()

            if split_line:
                if split_line[0] == "Cell" and split_line[1] == "Name":

                    name = " ".join(split_line[3:])

                elif split_line[0] == "Parameter":

                    if split_line[1] == "Name":
                        parameter_name = " ".join(split_line[3:])

                    if split_line[1] == "Address":
                        parameter_address = int(split_line[3])

                    if split_line[1] == "Value":
                        data = split_line[3]

                        try:
                            parameter_value = int(data)

                        except ValueError:
                            parameter_value = float(data)

        try:
            # Create a new cell, based on the collected parameters
            return Cell(name, parameter_address, parameter_name, parameter_value)

        except NameError:
            # This fails, if any of the required parameters were not extracted successfully.
            return None

    def run(self, file_path: str) -> None:
        """Parse an input file that was exported from Sigma Studio.

        Args:
            file_path (str): The path to the input file
        """
        self.cells.clear()

        if not file_path.endswith(".params"):
            logger.error("The parameter file is not a *.params file! Aborting.")
            return

        # Proceed with opening the file
        try:
            with open(file_path, "r", encoding="utf8") as file:
                logger.info("Using parameter file path %s.", file_path)

                line_iterator = iter(file.readlines())

                while True:
                    # The cascaded iterator looks for blocks within the parameter file, which define a cell.
                    # These blocks are surrounded by empty lines that only contain '\n'.
                    cell_lines = list(takewhile(lambda x: x != "\n", dropwhile(lambda x: x == "\n", line_iterator)))

                    if not cell_lines:
                        # No more blocks to be found in the parameter file.
                        break

                    cell = self.extract_cell(cell_lines)

                    if cell is None:
                        continue

                    elif cell not in self.cells:
                        self.cells.append(cell)

                logger.info("Found a total number of %d unique parameter cells.", len(self.cells))

        except FileNotFoundError:
            logger.info("Parameter file %s not found.", file_path)

    @property
    def safety_hash_cell(self) -> Union[Cell, None]:
        """Find and return the safety hash cell, if it exists.

        Returns:
            Cell: The safety hash cell.
        """
        safety_hash_cells = [cell for cell in self.cells if cell.is_safety_hash]

        if 1 != len(safety_hash_cells):
            # There must be exactly one safety hash cell.
            return None

        else:
            return safety_hash_cells[0]

    @property
    def volume_cells(self) -> List[Cell]:
        """Return all cells that can be used for volume adjustment. These are user defined with a certain name pattern.

        Returns:
            List[Cell]: The list of adjustable volume cells
        """
        return [cell for cell in self.cells if cell.is_volume_cell]

    def get_matching_cells_by_name_tokens(self, all_cells: List[Cell], name_tokens: List[str]) -> List[Cell]:
        """Find cells in a list of cells, whose names match the specified name tokens.

        Args:
            all_cells (List[Cell]): The list of cells to parse.
            name_tokens (List[str]): The tokens to check against.

        Returns:
            List[Cell]: The matched cells
        """
        return [cell for cell in all_cells if name_tokens == cell.name_tokens]

    def get_matching_cells_by_parameter_name(
        self, all_cells: List[Cell], parameter_name: str, match_substring=False
    ) -> List[Cell]:
        """Find cells in a list of cells, whose parameter names match the specified string.

        Args:
            all_cells (List[Cell]): The list of cells to parse.
            parameter_name (str): The string to check against.
            match_substring (bool): If False, only matches parameter names that are exactly `parameter_name`.
                Otherwise, matches if `parameter_name` is a substring of the parameter name.

        Returns:
            List[Cell]: The matched cells
        """
        if match_substring:
            return [cell for cell in all_cells if parameter_name in cell.parameter_name]

        else:
            return [cell for cell in all_cells if parameter_name == cell.parameter_name]
