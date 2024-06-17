"""Tests the parser module."""

from pathlib import Path

from sigmadsp.helper.parser import Parser

TEST_FILE_PATH = Path(__file__).parent / "test_parameter_file.params"


def test_parser() -> None:
    """Test the parser for correct extraction of parameters from a file."""
    p = Parser()
    p.run(TEST_FILE_PATH)

    # Test safeload registers
    data_safeload = p.get_matching_cells_by_parameter_name(p.cells, "__SafeLoad_Module__data_SafeLoad")
    address_safeload = p.get_matching_cells_by_parameter_name(p.cells, "__SafeLoad_Module__address_SafeLoad")
    num_safeload = p.get_matching_cells_by_parameter_name(p.cells, "__SafeLoad_Module__num_SafeLoad")

    assert len(data_safeload) == 1
    assert len(address_safeload) == 1
    assert len(num_safeload) == 1

    assert data_safeload[0].parameter_address == 0x6000
    assert address_safeload[0].parameter_address == 0x6005
    assert num_safeload[0].parameter_address == 0x6006

    # Test safety hash register
    safety_hash = p.safety_hash_cell
    assert safety_hash is not None
    assert safety_hash.is_safety_hash
    assert not safety_hash.is_volume_cell
    assert not safety_hash.is_adjustable
    assert safety_hash.parameter_value == 1661147736

    # Test volume cells
    volume_cells = p.volume_cells
    assert len(volume_cells) == 1

    volume_cell = volume_cells[0]
    assert volume_cell.is_adjustable
    assert not volume_cell.is_safety_hash
    assert volume_cell.is_volume_cell
    assert volume_cell.name_tokens == ["main"]
