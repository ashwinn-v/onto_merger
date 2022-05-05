"""Tests for the AlignmentManager."""
from typing import List

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame

from onto_merger.alignment.alignment_manager import (
    AlignmentManager,
    convert_alignment_steps_to_named_table,
    produce_source_alignment_priority_order,
)
from onto_merger.data.constants import (
    SCHEMA_ALIGNMENT_STEPS_TABLE,
    TABLE_ALIGNMENT_STEPS_REPORT,
    TABLE_MERGES,
    TABLE_NODES,
)
from onto_merger.data.dataclasses import AlignmentStep, DataRepository, NamedTable
from tests.fixtures import data_repo, source_alignment_priority_order


def test_produce_source_alignment_priority_order(data_repo, source_alignment_priority_order):
    actual = produce_source_alignment_priority_order(
        seed_ontology_name="MONDO", nodes=data_repo.get(TABLE_NODES).dataframe
    )
    assert actual == source_alignment_priority_order


def test_convert_alignment_steps_to_named_table():
    input_data = [
        AlignmentStep(
            mapping_type_group="eqv",
            source_id="FOO",
            step_counter=1,
            count_unmapped_nodes=100,
        ),
        AlignmentStep(
            mapping_type_group="eqv",
            source_id="BAR",
            step_counter=2,
            count_unmapped_nodes=90,
        ),
    ]
    actual = convert_alignment_steps_to_named_table(alignment_steps=input_data)
    expected = pd.DataFrame(
        [("eqv", "FOO", 1, 100, 0, 0, 0), ("eqv", "BAR", 2, 90, 0, 0, 0)],
        columns=SCHEMA_ALIGNMENT_STEPS_TABLE,
    )
    assert isinstance(actual, NamedTable)
    assert actual.name == TABLE_ALIGNMENT_STEPS_REPORT
    assert isinstance(actual.dataframe, DataFrame)
    assert np.array_equal(actual.dataframe.values, expected.values) is True
