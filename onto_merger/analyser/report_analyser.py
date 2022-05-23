"""Analyse input and produced data, pipeline processing, data profiling and data tests.

Produce data and figures are presented in the report.
"""
import json
import os
from datetime import timedelta
from pathlib import Path
from typing import List

import pandas as pd
from pandas import DataFrame
from pandas_profiling import __version__ as pandas_profiling_version

from onto_merger.analyser import report_analyser_utils
from onto_merger.analyser import plotly_utils
from onto_merger.analyser.analysis_utils import produce_table_with_namespace_column_for_node_ids, \
    produce_table_node_namespace_distribution, produce_table_with_namespace_column_pair, \
    get_namespace_column_name_for_column, produce_table_node_ids_from_edge_table
from onto_merger.analyser.constants import TABLE_STATS, \
    ANALYSIS_NODE_NAMESPACE_FREQ, \
    TABLE_SECTION, TABLE_SUMMARY, ANALYSIS_GENERAL, ANALYSIS_PROV, ANALYSIS_TYPE, ANALYSIS_MAPPED_NSS, \
    HEATMAP_MAPPED_NSS, ANALYSIS_CONNECTED_NSS, ANALYSIS_MERGES_NSS, \
    ANALYSIS_MERGES_NSS_FOR_CANONICAL, COLUMN_NAMESPACE_TARGET_ID, COLUMN_FREQ, \
    ANALYSIS_CONNECTED_NSS_CHART, GANTT_CHART
from onto_merger.data.constants import SCHEMA_NODE_ID_LIST_TABLE, COLUMN_DEFAULT_ID, COLUMN_COUNT, \
    COLUMN_PROVENANCE, COLUMN_RELATION, COLUMN_SOURCE_ID, COLUMN_TARGET_ID, \
    DIRECTORY_INPUT, DIRECTORY_OUTPUT, TABLES_NODE, TABLES_EDGE_HIERARCHY, TABLES_MAPPING, \
    TABLE_TYPE_MAPPING, TABLES_MERGE, TABLE_TYPE_NODE, TABLE_TYPE_EDGE, DIRECTORY_INTERMEDIATE, \
    TABLE_NODES_OBSOLETE, TABLE_MAPPINGS, TABLE_EDGES_HIERARCHY, TABLE_NODES, \
    TABLE_NODES_MERGED, TABLE_NODES_UNMAPPED, TABLE_NODES_DANGLING, \
    TABLE_ALIGNMENT_STEPS_REPORT, TABLE_CONNECTIVITY_STEPS_REPORT, TABLE_PIPELINE_STEPS_REPORT, \
    TABLE_EDGES_HIERARCHY_POST, TABLES_DOMAIN, TABLES_INPUT, TABLES_INTERMEDIATE, TABLE_MERGES_AGGREGATED, \
    TABLE_NODES_CONNECTED, DIRECTORY_ANALYSIS
from onto_merger.data.data_manager import DataManager
from onto_merger.data.dataclasses import NamedTable, DataRepository, AlignmentConfig
from onto_merger.logger.log import get_logger
from onto_merger.report.constants import SECTION_INPUT, SECTION_OUTPUT, SECTION_DATA_TESTS, \
    SECTION_DATA_PROFILING, SECTION_CONNECTIVITY, SECTION_OVERVIEW, SECTION_ALIGNMENT
from onto_merger.version import __version__ as onto_merger_version

logger = get_logger(__name__)

COVERED = "covered"


class ReportAnalyser:
    """Produce analysis data and illustrations"""

    def __init__(
            self,
            alignment_config: AlignmentConfig,
            data_repo: DataRepository,
            data_manager: DataManager,
    ):
        """Initialise the AlignmentManager class.

        :param alignment_config: The alignment process configuration dataclass.
        :param data_repo: The data repository that stores the input tables.
        :param data_manager: The data manager instance.
        """
        self._alignment_config = alignment_config
        self._data_manager = data_manager
        self._data_repo_input = data_repo

    def produce_report_data(self) -> None:
        pass


# MAIN #
def produce_report_data(data_manager: DataManager, data_repo: DataRepository) -> None:
    logger.info(f"Started producing report analysis...")
    data_test_stats = _produce_data_testing_analysis(data_manager=data_manager, data_repo=data_repo)
    data_profiling_stats = _produce_data_profiling_analysis(data_manager=data_manager, data_repo=data_repo)
    _produce_input_dataset_analysis(data_manager=data_manager, data_repo=data_repo)
    _produce_output_dataset_analysis(data_manager=data_manager, data_repo=data_repo)
    _produce_alignment_process_analysis(data_manager=data_manager, data_repo=data_repo)
    _produce_connectivity_process_analysis(data_manager=data_manager, data_repo=data_repo)
    _produce_overview_analysis(
        data_manager=data_manager,
        data_repo=data_repo,
        data_profiling_stats=data_profiling_stats,
        data_test_stats=data_test_stats,
    )
    # do overview summary total runtime & gantt LAST
    logger.info(f"Finished producing report analysis.")


# PRODUCE & SAVE for DATASET #
def _produce_input_dataset_analysis(data_manager: DataManager, data_repo: DataRepository) -> None:
    # analyse and save
    section_dataset_name = SECTION_INPUT
    logger.info(f"Producing report section '{section_dataset_name}' analysis...")
    _produce_and_save_summary_input(data_manager=data_manager, data_repo=data_repo)
    _produce_and_save_node_analysis(
        node_tables=[
            data_repo.get(table_name=TABLE_NODES), data_repo.get(table_name=TABLE_NODES_OBSOLETE)
        ],
        mappings=data_repo.get(table_name=TABLE_MAPPINGS).dataframe,
        edges_hierarchy=data_repo.get(table_name=TABLE_EDGES_HIERARCHY).dataframe,
        dataset=section_dataset_name,
        data_manager=data_manager
    )
    _produce_and_save_mapping_analysis(
        mappings=data_repo.get(table_name=TABLE_MAPPINGS).dataframe,
        dataset=section_dataset_name,
        data_manager=data_manager
    )
    _produce_and_save_hierarchy_edge_analysis(
        edges=data_repo.get(table_name=TABLE_EDGES_HIERARCHY).dataframe,
        dataset=section_dataset_name,
        data_manager=data_manager
    )


def _produce_output_dataset_analysis(data_manager: DataManager, data_repo: DataRepository) -> None:
    section_dataset_name = SECTION_OUTPUT
    logger.info(f"Producing report section '{section_dataset_name}' analysis...")
    _produce_and_save_summary_output(data_manager=data_manager, data_repo=data_repo)
    _produce_and_save_node_analysis(
        node_tables=[
            data_repo.get(table_name=TABLE_NODES)
        ],
        mappings=data_repo.get(table_name=TABLE_MAPPINGS).dataframe,
        edges_hierarchy=data_repo.get(table_name=TABLE_EDGES_HIERARCHY_POST).dataframe,
        dataset=section_dataset_name,
        data_manager=data_manager
    )
    _produce_and_save_mapping_analysis(
        mappings=data_repo.get(table_name=TABLE_MAPPINGS).dataframe,
        dataset=section_dataset_name,
        data_manager=data_manager
    )
    _produce_and_save_hierarchy_edge_analysis(
        edges=data_repo.get(table_name=TABLE_EDGES_HIERARCHY_POST).dataframe,
        dataset=section_dataset_name,
        data_manager=data_manager
    )


def _produce_alignment_process_analysis(data_manager: DataManager, data_repo: DataRepository) -> None:
    # analyse and save
    section_dataset_name = SECTION_ALIGNMENT
    logger.info(f"Producing report section '{section_dataset_name}' analysis...")
    _produce_and_save_summary_alignment(data_manager=data_manager, data_repo=data_repo)
    data_manager.save_analysis_table(
        analysis_table=_produce_node_namespace_freq(nodes=data_repo.get(table_name=TABLE_NODES_MERGED).dataframe),
        dataset=section_dataset_name,
        analysed_table_name=TABLE_NODES_MERGED,
        analysis_table_suffix=ANALYSIS_NODE_NAMESPACE_FREQ
    )
    _produce_and_save_merge_analysis(
        merges=data_repo.get(table_name=TABLE_MERGES_AGGREGATED).dataframe,
        dataset=section_dataset_name,
        data_manager=data_manager
    )
    data_manager.save_analysis_table(
        analysis_table=_produce_node_namespace_freq(nodes=data_repo.get(table_name=TABLE_NODES_UNMAPPED).dataframe),
        dataset=section_dataset_name,
        analysed_table_name=TABLE_NODES_UNMAPPED,
        analysis_table_suffix=ANALYSIS_NODE_NAMESPACE_FREQ
    )
    _produce_and_save_runtime_tables(
        table_name=TABLE_ALIGNMENT_STEPS_REPORT,
        section_dataset_name=section_dataset_name,
        data_manager=data_manager,
        data_repo=data_repo,
    )
    data_manager.save_analysis_table(
        analysis_table=data_repo.get(table_name=TABLE_ALIGNMENT_STEPS_REPORT).dataframe,
        dataset=section_dataset_name,
        analysed_table_name="steps",
        analysis_table_suffix="detail"
    )
    _produce_and_save_alignment_step_node_analysis(
        alignment_step_report=data_repo.get(table_name=TABLE_ALIGNMENT_STEPS_REPORT).dataframe,
        section_dataset_name=section_dataset_name,
        data_manager=data_manager,
    )


def _produce_connectivity_process_analysis(data_manager: DataManager, data_repo: DataRepository) -> None:
    section_dataset_name = SECTION_CONNECTIVITY
    logger.info(f"Producing report section '{section_dataset_name}' analysis...")
    _produce_and_save_summary_connectivity(data_manager=data_manager, data_repo=data_repo)
    data_manager.save_analysis_table(
        analysis_table=_produce_node_namespace_freq(
            nodes=data_repo.get(table_name=TABLE_NODES_CONNECTED).dataframe),
        dataset=section_dataset_name,
        analysed_table_name="nodes_connected",
        analysis_table_suffix=ANALYSIS_NODE_NAMESPACE_FREQ
    )
    data_manager.save_analysis_table(
        analysis_table=_produce_node_namespace_freq(
            nodes=data_repo.get(table_name=TABLE_NODES_DANGLING).dataframe),
        dataset=section_dataset_name,
        analysed_table_name=TABLE_NODES_DANGLING,
        analysis_table_suffix=ANALYSIS_NODE_NAMESPACE_FREQ
    )
    _produce_and_save_runtime_tables(
        table_name=TABLE_CONNECTIVITY_STEPS_REPORT,
        section_dataset_name=section_dataset_name,
        data_manager=data_manager,
        data_repo=data_repo,
    )
    data_manager.save_analysis_table(
        analysis_table=data_repo.get(table_name=TABLE_CONNECTIVITY_STEPS_REPORT).dataframe,
        dataset=section_dataset_name,
        analysed_table_name="steps",
        analysis_table_suffix="detail"
    )
    _produce_and_save_connectivity_step_node_analysis(
        step_report=data_repo.get(table_name=TABLE_CONNECTIVITY_STEPS_REPORT).dataframe,
        section_dataset_name=section_dataset_name,
        data_manager=data_manager,
    )
    _save_analysis_named_tables(
        tables=report_analyser_utils.produce_hierarchy_edge_path_analysis(
            hierarchy_edges_paths=data_manager.load_table(
                table_name="connectivity_hierarchy_edges_paths",
                process_directory=f"{DIRECTORY_OUTPUT}/{DIRECTORY_INTERMEDIATE}/{DIRECTORY_ANALYSIS}"
            ),
        ),
        dataset=section_dataset_name,
        analysed_table_name="hierarchy_edges_paths",
        data_manager=data_manager,
    )
    _save_analysis_named_tables(
        tables=report_analyser_utils.produce_connectivity_hierarchy_edge_overview_analysis(
            edges_input=data_repo.get(table_name=TABLE_EDGES_HIERARCHY).dataframe,
            edges_output=data_repo.get(table_name=TABLE_EDGES_HIERARCHY_POST).dataframe,
            data_manager=data_manager,
        ),
        dataset=section_dataset_name,
        analysed_table_name="hierarchy_edges_overview",
        data_manager=data_manager,
    )


def _produce_data_testing_analysis(
        data_manager: DataManager, data_repo: DataRepository
) -> (DataFrame, DataFrame):
    logger.info(f"Producing report section '{SECTION_DATA_TESTS}' analysis...")
    data_test_stats = _produce_data_testing_table_stats(data_manager=data_manager,
                                                        section_name=SECTION_DATA_TESTS)
    _produce_and_save_summary_data_tests(data_manager=data_manager,
                                         data_repo=data_repo,
                                         stats=data_test_stats)

    return data_test_stats


def _produce_data_profiling_analysis(
        data_manager: DataManager, data_repo: DataRepository
) -> (DataFrame, DataFrame):
    logger.info(f"Producing report section '{SECTION_DATA_PROFILING}' and '{SECTION_DATA_TESTS}' analysis...")
    data_profiling_stats = _produce_data_profiling_table_stats(data_manager=data_manager,
                                                               section_name=SECTION_DATA_PROFILING)
    _produce_and_save_summary_data_profiling(data_manager=data_manager,
                                             data_repo=data_repo,
                                             data_profiling_stats=data_profiling_stats)
    return data_profiling_stats


def _produce_overview_analysis(data_manager: DataManager,
                               data_repo: DataRepository,
                               data_profiling_stats: DataFrame,
                               data_test_stats: DataFrame) -> DataFrame:
    # analyse and save
    section_dataset_name = SECTION_OVERVIEW
    logger.info(f"Producing report section '{section_dataset_name}' analysis...")
    node_status_df = _produce_and_save_node_status_analyses(
        seed_name=data_manager.load_alignment_config().base_config.seed_ontology_name,
        data_manager=data_manager,
        data_repo=data_repo
    )
    _produce_and_save_validation_overview_analyses(
        data_manager=data_manager,
        data_profiling_stats=data_profiling_stats,
        data_test_stats=data_test_stats,
    )
    _produce_and_save_runtime_tables(
        table_name=TABLE_PIPELINE_STEPS_REPORT,
        section_dataset_name=section_dataset_name,
        data_manager=data_manager,
        data_repo=data_repo,
    )
    _produce_and_save_summary_overview(
        data_manager=data_manager,
        data_repo=data_repo,
        node_status=node_status_df,
    )
    _save_analysis_named_tables(
        tables=report_analyser_utils.produce_overview_hierarchy_edge_comparison(data_manager=data_manager),
        dataset=section_dataset_name,
        analysed_table_name="hierarchy_edge",
        data_manager=data_manager,
    )

    return node_status_df


# PRODUCE & SAVE for ENTITY #
def _produce_and_save_node_analysis(node_tables: List[NamedTable],
                                    mappings: DataFrame,
                                    edges_hierarchy: DataFrame,
                                    dataset: str,
                                    data_manager: DataManager) -> None:
    for table in node_tables:
        analysis_table = _produce_node_analysis(
            nodes=table.dataframe,
            mappings=mappings,
            edges_hierarchy=edges_hierarchy
        )
        data_manager.save_analysis_table(
            analysis_table=analysis_table,
            dataset=dataset,
            analysed_table_name=table.name,
            analysis_table_suffix=ANALYSIS_GENERAL
        )
        plotly_utils.produce_nodes_ns_freq_chart(
            analysis_table=analysis_table,
            file_path=data_manager.get_analysis_figure_path(
                dataset=dataset,
                analysed_table_name=table.name,
                analysis_table_suffix=ANALYSIS_GENERAL
            )
        )


def _produce_and_save_mapping_analysis(mappings: DataFrame,
                                       dataset: str,
                                       data_manager: DataManager) -> None:
    table_type = TABLE_MAPPINGS
    data_manager.save_analysis_table(
        analysis_table=_produce_mapping_analysis_for_prov(mappings=mappings),
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=ANALYSIS_PROV
    )
    mapping_type_analysis = _produce_mapping_analysis_for_type(mappings=mappings)
    data_manager.save_analysis_table(
        analysis_table=mapping_type_analysis,
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=ANALYSIS_TYPE
    )
    plotly_utils.produce_mapping_type_freq_chart(
        analysis_table=mapping_type_analysis,
        file_path=data_manager.get_analysis_figure_path(
            dataset=dataset,
            analysed_table_name=table_type,
            analysis_table_suffix="type_analysis"
        )
    )
    data_manager.save_analysis_table(
        analysis_table=_produce_mapping_analysis_for_mapped_nss(mappings=mappings),
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=ANALYSIS_MAPPED_NSS
    )
    mapped_nss_heatmap_data = _produce_edges_analysis_for_mapped_or_connected_nss_heatmap(
        edges=mappings,
        prune=False,
        directed_edge=False
    )
    data_manager.save_analysis_table(
        analysis_table=mapped_nss_heatmap_data,
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=HEATMAP_MAPPED_NSS,
        index=True
    )
    plotly_utils.produce_edge_heatmap(
        analysis_table=mapped_nss_heatmap_data,
        file_path=data_manager.get_analysis_figure_path(
            dataset=dataset,
            analysed_table_name=table_type,
            analysis_table_suffix=ANALYSIS_MAPPED_NSS
        )
    )


def _produce_and_save_hierarchy_edge_analysis(edges: DataFrame,
                                              dataset: str,
                                              data_manager: DataManager) -> None:
    table_type = TABLE_EDGES_HIERARCHY
    data_manager.save_analysis_table(
        analysis_table=report_analyser_utils.produce_hierarchy_edge_analysis_for_mapped_nss(edges=edges),
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=ANALYSIS_CONNECTED_NSS
    )
    connected_nss = _produce_source_to_target_analysis_for_directed_edge(edges=edges)
    data_manager.save_analysis_table(
        analysis_table=connected_nss,
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=ANALYSIS_CONNECTED_NSS_CHART
    )
    plotly_utils.produce_hierarchy_nss_stacked_bar_chart(
        analysis_table=connected_nss,
        file_path=data_manager.get_analysis_figure_path(
            dataset=dataset,
            analysed_table_name=table_type,
            analysis_table_suffix=ANALYSIS_CONNECTED_NSS_CHART
        )
    )


def _produce_and_save_merge_analysis(merges: DataFrame,
                                     dataset: str,
                                     data_manager: DataManager) -> None:
    table_type = "merges"
    merged_nss = _produce_source_to_target_analysis_for_directed_edge(edges=merges)
    data_manager.save_analysis_table(
        analysis_table=merged_nss,
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=ANALYSIS_MERGES_NSS
    )
    plotly_utils.produce_merged_nss_stacked_bar_chart(
        analysis_table=merged_nss,
        file_path=data_manager.get_analysis_figure_path(
            dataset=dataset,
            analysed_table_name=table_type,
            analysis_table_suffix=ANALYSIS_MERGES_NSS
        )
    )
    data_manager.save_analysis_table(
        analysis_table=_produce_merge_analysis_for_merged_nss_for_canonical(merges=merges),
        dataset=dataset,
        analysed_table_name=table_type,
        analysis_table_suffix=ANALYSIS_MERGES_NSS_FOR_CANONICAL
    )
    _save_analysis_named_tables(
        tables=report_analyser_utils.produce_merge_cluster_analysis(merges_aggregated=merges,
                                                                    data_manager=data_manager),
        dataset=dataset,
        analysed_table_name=table_type,
        data_manager=data_manager,
    )


# HELPERS todo
def print_df_stats(df, name):
    # print("\n\n", name, "\n\t", len(df), "\n\t", list(df))
    # print(df.head(10))
    pass


def _save_analysis_named_tables(tables: List[NamedTable],
                                dataset: str,
                                analysed_table_name: str,
                                data_manager: DataManager) -> None:
    for table in tables:
        data_manager.save_analysis_table(
            analysis_table=table.dataframe,
            dataset=dataset,
            analysed_table_name=analysed_table_name,
            analysis_table_suffix=table.name,
        )


# ANALYSIS #
def _produce_node_namespace_distribution_with_type(nodes: DataFrame, metric_name: str) -> DataFrame:
    node_namespace_distribution_df = produce_table_node_namespace_distribution(
        node_table=produce_table_with_namespace_column_for_node_ids(table=nodes)
    )[["namespace", "count"]]
    df = node_namespace_distribution_df.rename(
        columns={"count": f"{metric_name}_count"}
    )
    return df


def _produce_node_covered_by_edge_table(nodes: DataFrame,
                                        edges: DataFrame,
                                        coverage_column: str) -> DataFrame:
    node_id_list_of_edges = produce_table_node_ids_from_edge_table(edges=edges)
    node_id_list_of_edges[coverage_column] = True
    nodes_covered = pd.merge(
        nodes[SCHEMA_NODE_ID_LIST_TABLE],
        node_id_list_of_edges,
        how="left",
        on=COLUMN_DEFAULT_ID,
    ).dropna(subset=[coverage_column])
    return nodes_covered[SCHEMA_NODE_ID_LIST_TABLE]


def _produce_node_analysis(nodes: DataFrame, mappings: DataFrame, edges_hierarchy: DataFrame) -> DataFrame:
    node_namespace_distribution_df = _produce_node_namespace_distribution_with_type(
        nodes=nodes, metric_name="namespace"
    )

    node_mapping_coverage_df = _produce_node_covered_by_edge_table(nodes=nodes,
                                                                   edges=mappings,
                                                                   coverage_column=COVERED)
    node_mapping_coverage_distribution_df = _produce_node_namespace_distribution_with_type(
        nodes=node_mapping_coverage_df, metric_name="mapping_coverage"
    )

    node_edge_coverage_df = _produce_node_covered_by_edge_table(nodes=nodes,
                                                                edges=edges_hierarchy,
                                                                coverage_column=COVERED)
    node_edge_coverage_distribution_df = _produce_node_namespace_distribution_with_type(
        nodes=node_edge_coverage_df, metric_name="edge_coverage"
    )

    # merge
    node_analysis = node_namespace_distribution_df
    if len(node_edge_coverage_distribution_df) > 0:
        node_analysis = pd.merge(
            node_analysis,
            node_mapping_coverage_distribution_df,
            how="outer",
            on="namespace",
        )
    else:
        node_analysis["mapping_coverage_count"] = 0
    if len(node_edge_coverage_distribution_df) > 0:
        node_analysis = pd.merge(
            node_analysis,
            node_edge_coverage_distribution_df,
            how="outer",
            on="namespace",
        ).fillna(0, inplace=False)
    else:
        node_analysis["edge_coverage_count"] = 0

    # add freq
    node_analysis["namespace_freq"] = node_analysis.apply(
        lambda x: (round(x['namespace_count'] / len(nodes) * 100, 2)), axis=1
    )
    # add relative freq
    node_analysis["mapping_coverage_freq"] = node_analysis.apply(
        lambda x: (round(x['mapping_coverage_count'] / x['namespace_count'] * 100, 2)), axis=1
    )
    node_analysis["edge_coverage_freq"] = node_analysis.apply(
        lambda x: (round(x['edge_coverage_count'] / x['namespace_count'] * 100, 2)), axis=1
    )
    return node_analysis


def _produce_node_namespace_freq(nodes: DataFrame) -> DataFrame:
    df = _produce_node_namespace_distribution_with_type(
        nodes=nodes, metric_name="namespace"
    )
    df["namespace_freq"] = df.apply(
        lambda x: (round((x['namespace_count'] / len(nodes) * 100), 3)), axis=1
    )
    return df


# NODE STATUS TABLES & CHARTS #
def _produce_and_save_node_status_analyses(
        seed_name: str, data_manager: DataManager, data_repo: DataRepository,
) -> DataFrame:
    # assume seed is all connected

    seed_ontology_name = data_manager.load_alignment_config().base_config.seed_ontology_name

    # data tables
    steps_report_alignment = data_repo.get(table_name=TABLE_ALIGNMENT_STEPS_REPORT).dataframe
    steps_report_connectivity = data_repo.get(table_name=TABLE_CONNECTIVITY_STEPS_REPORT).dataframe
    merge_analysis_df = _produce_merge_analysis_for_merged_nss_for_canonical(
        merges=data_repo.get(TABLE_MERGES_AGGREGATED).dataframe
    )
    nodes_input_df = produce_table_with_namespace_column_for_node_ids(
        table=data_repo.get(table_name=TABLE_NODES).dataframe
    )
    nodes_merged_df = data_repo.get(table_name=TABLE_NODES_MERGED).dataframe
    nodes_connected_df = data_repo.get(table_name=TABLE_NODES_CONNECTED).dataframe
    nodes_dangling_df = data_repo.get(table_name=TABLE_NODES_DANGLING).dataframe

    # INPUT
    nodes_input = len(nodes_input_df)
    nodes_seed = len(nodes_input_df
        .query(
        expr=f"{get_namespace_column_name_for_column(COLUMN_DEFAULT_ID)} == '{seed_ontology_name}'"))
    nodes_not_seed = nodes_input - nodes_seed

    # ALIGNMENT
    nodes_merged_total = len(nodes_merged_df)
    nodes_merged_to_seed = merge_analysis_df \
        .query(expr=f'{COLUMN_NAMESPACE_TARGET_ID} == "{seed_name}"', inplace=False)['count'].sum()
    nodes_merged_to_not_seed = nodes_merged_total - nodes_merged_to_seed
    nodes_unmapped = nodes_input - nodes_seed - nodes_merged_total
    nodes_aligned = nodes_seed + nodes_merged_total

    # CONNECTIVITY
    nodes_connected = len(nodes_connected_df)
    nodes_dangling = len(nodes_dangling_df)
    nodes_connected_excluding_seed = nodes_connected - nodes_seed
    nodes_merged_to_connected_excluding_seed = 0
    nodes_merged_to_dangling = 0

    # OUTPUT
    nodes_input_output_diff = nodes_input - (nodes_input - (nodes_merged_to_seed + nodes_merged_to_not_seed))

    # INPUT:    | Seed | Others |
    input_data = [
        [SECTION_INPUT, nodes_seed, "Seed"],
        [SECTION_INPUT, nodes_not_seed, "Other input"],
    ]
    _process_node_status_table_and_plot(
        data=input_data,
        total_count=nodes_input,
        section_dataset_name=SECTION_INPUT,
        data_manager=data_manager,
    )

    # ALG:      | Seed | Merged to seed | Merged | Unmapped |
    alignment_data = [
        [SECTION_ALIGNMENT, nodes_seed, "Seed"],
        [SECTION_ALIGNMENT, nodes_merged_to_seed, "Merged to seed"],
        [SECTION_ALIGNMENT, nodes_merged_to_not_seed, "Merged"],
        [SECTION_ALIGNMENT, nodes_unmapped, "Unmapped"],
    ]
    _process_node_status_table_and_plot(
        data=alignment_data,
        total_count=nodes_input,
        section_dataset_name=SECTION_ALIGNMENT,
        data_manager=data_manager,
    )

    # CON:      | Seed | Merged and Connected | Connected | Dangling |
    connectivity_data = [
        [SECTION_CONNECTIVITY, nodes_aligned, "Aligned"],
        [SECTION_CONNECTIVITY, nodes_connected_excluding_seed, "Connected"],
        [SECTION_CONNECTIVITY, nodes_dangling, "Dangling"],
    ]
    _process_node_status_table_and_plot(
        data=connectivity_data,
        total_count=nodes_input,
        section_dataset_name=SECTION_CONNECTIVITY,
        data_manager=data_manager,
    )

    # Output
    output_data = [
        [SECTION_OUTPUT, nodes_connected, "Connected"],
        [SECTION_OUTPUT, nodes_dangling, "Dangling"],
        [SECTION_OUTPUT, nodes_input_output_diff, "Diff from Input"],
    ]
    _process_node_status_table_and_plot(
        data=output_data,
        total_count=nodes_input,
        section_dataset_name=SECTION_OUTPUT,
        data_manager=data_manager,
    )

    # Overview
    overview_data = input_data + alignment_data + connectivity_data + output_data
    overview_df = _process_node_status_table_and_plot(
        data=overview_data,
        total_count=nodes_input,
        section_dataset_name=SECTION_OVERVIEW,
        data_manager=data_manager,
        is_one_bar=False
    )

    # overview status
    overview_node_status_table = [
        [SECTION_INPUT, nodes_input, "<b>Input nodes</b>"],
        [SECTION_INPUT, nodes_seed, "Seed nodes"],
        [SECTION_INPUT, nodes_not_seed, "Nodes excluding seed"],
        [SECTION_ALIGNMENT, nodes_aligned, "<b>Aligned nodes(seed + merged)</b>"],
        [SECTION_ALIGNMENT, nodes_merged_to_seed, "Nodes merged to seed"],
        [SECTION_ALIGNMENT, nodes_merged_to_not_seed, "Nodes Merged to other than seed"],
        [SECTION_ALIGNMENT, nodes_unmapped, "Unmapped nodes"],
        [SECTION_CONNECTIVITY, nodes_aligned, "<b>Connected nodes (seed + other connected)</b>"],
        [SECTION_CONNECTIVITY, nodes_connected_excluding_seed, "\tConnected nodes (excluding seed + merged to seed)"],
        [SECTION_CONNECTIVITY, nodes_dangling, "Dangling nodes (not connected or merged)"],
        [SECTION_OUTPUT, nodes_input_output_diff, "<b>Input & Output node diff</b>"],
    ]
    _produce_and_save_node_status_table(
        data=overview_node_status_table,
        total_count=nodes_input,
        section_dataset_name=SECTION_OVERVIEW,
        data_manager=data_manager,
    )
    return overview_df


def _produce_and_save_node_status_table(
        data: List[list], total_count: int, section_dataset_name: str,
        data_manager: DataManager,
) -> DataFrame:
    df = pd.DataFrame(data, columns=["category", "count", "status_no_freq"])
    df = _add_ratio_to_node_status_table(
        node_status_table=df, total_count=total_count,
    )
    data_manager.save_analysis_table(
        analysis_table=df,
        dataset=section_dataset_name,
        analysed_table_name="node",
        analysis_table_suffix="status",
    )
    return df


def _process_node_status_table_and_plot(
        data: List[list], total_count: int, section_dataset_name: str,
        data_manager: DataManager, is_one_bar: bool = True,
) -> DataFrame:
    node_status_table = _produce_and_save_node_status_table(
        data=data,
        total_count=total_count,
        section_dataset_name=section_dataset_name,
        data_manager=data_manager,
    )
    plotly_utils.produce_status_stacked_bar_chart(
        analysis_table=node_status_table,
        file_path=data_manager.get_analysis_figure_path(
            dataset=section_dataset_name,
            analysed_table_name="node",
            analysis_table_suffix="status",
        ),
        is_one_bar=is_one_bar,
    )
    return node_status_table


def _add_ratio_to_node_status_table(node_status_table: DataFrame, total_count: int) -> DataFrame:
    node_status_table["ratio"] = node_status_table.apply(
        lambda x: (round((x['count'] / total_count * 100), 3)), axis=1
    )
    node_status_table["status"] = node_status_table.apply(
        lambda x: f"{x['status_no_freq']} ({x['ratio']:.1f}%)", axis=1
    )
    return node_status_table


# MAPPING #
def _produce_mapping_analysis_for_type(mappings: DataFrame) -> DataFrame:
    df = mappings[[COLUMN_RELATION, COLUMN_PROVENANCE, COLUMN_SOURCE_ID]].groupby([COLUMN_RELATION]) \
        .agg(count=(COLUMN_SOURCE_ID, 'count'),
             provs=(COLUMN_PROVENANCE, lambda x: set(x))) \
        .reset_index() \
        .sort_values(COLUMN_COUNT, ascending=False)
    df["freq"] = df.apply(
        lambda x: (round((x['count'] / len(mappings) * 100), 3)), axis=1
    )
    return df


def _produce_mapping_analysis_for_prov(mappings: DataFrame) -> DataFrame:
    df = mappings[[COLUMN_RELATION, COLUMN_PROVENANCE, COLUMN_SOURCE_ID]].groupby([COLUMN_PROVENANCE]) \
        .agg(count=(COLUMN_SOURCE_ID, 'count'),
             relations=(COLUMN_RELATION, lambda x: set(x))) \
        .reset_index() \
        .sort_values(COLUMN_COUNT, ascending=False)
    return df


def _produce_mapping_analysis_for_mapped_nss(mappings: DataFrame) -> DataFrame:
    col_nss_set = 'nss_set'
    df = produce_table_with_namespace_column_for_node_ids(table=mappings)
    df[col_nss_set] = df.apply(
        lambda x: str({x[get_namespace_column_name_for_column(COLUMN_SOURCE_ID)],
                       x[get_namespace_column_name_for_column(COLUMN_TARGET_ID)]}),
        axis=1
    )
    df = df[[col_nss_set, COLUMN_RELATION, COLUMN_PROVENANCE, COLUMN_SOURCE_ID]] \
        .groupby([col_nss_set]) \
        .agg(count=(COLUMN_SOURCE_ID, 'count'),
             types=(COLUMN_RELATION, lambda x: set(x)),
             provs=(COLUMN_PROVENANCE, lambda x: set(x))) \
        .reset_index() \
        .sort_values(COLUMN_COUNT, ascending=False)
    df["freq"] = df.apply(
        lambda x: (round((x['count'] / len(mappings) * 100), 2)), axis=1
    )
    return df


# EDGE #
def _produce_edges_analysis_for_mapped_or_connected_nss_heatmap(edges: DataFrame,
                                                                prune: bool = False,
                                                                directed_edge: bool = False) -> DataFrame:
    cols = [get_namespace_column_name_for_column(COLUMN_SOURCE_ID),
            get_namespace_column_name_for_column(COLUMN_TARGET_ID)]
    df = produce_table_with_namespace_column_for_node_ids(table=edges)
    df: DataFrame = df.groupby(cols).agg(count=(COLUMN_SOURCE_ID, 'count')) \
        .reset_index().sort_values(COLUMN_COUNT, ascending=False)

    # matrix
    namespaces = sorted(list(set((df[cols[0]].tolist() + df[cols[1]].tolist()))))
    matrix = [[0 for _ in namespaces] for _ in namespaces]
    for _, row in df.iterrows():
        src_ns = row[cols[0]]
        trg_ns = row[cols[1]]
        count = row[COLUMN_COUNT]
        current_value1 = matrix[namespaces.index(src_ns)][namespaces.index(trg_ns)]
        matrix[namespaces.index(src_ns)][namespaces.index(trg_ns)] += current_value1 + count
        if directed_edge is False:
            current_value2 = matrix[namespaces.index(trg_ns)][namespaces.index(src_ns)]
            matrix[namespaces.index(trg_ns)][namespaces.index(src_ns)] += current_value2 + count
    matrix_df = pd.DataFrame(matrix, columns=namespaces, index=namespaces)

    # prune 0s
    if prune is True:
        matrix_df = matrix_df.loc[~(matrix_df == 0).all(axis=1)]
        matrix_df = matrix_df.loc[:, (matrix_df != 0).any(axis=0)]

    return matrix_df


def _produce_source_to_target_analysis_for_directed_edge(edges: DataFrame) -> DataFrame:
    cols = [get_namespace_column_name_for_column(COLUMN_SOURCE_ID),
            get_namespace_column_name_for_column(COLUMN_TARGET_ID)]
    df = produce_table_with_namespace_column_pair(
        table=produce_table_with_namespace_column_for_node_ids(table=edges)) \
        .groupby(cols) \
        .agg(count=(COLUMN_SOURCE_ID, COLUMN_COUNT)) \
        .reset_index() \
        .sort_values(COLUMN_COUNT, ascending=False)
    df[COLUMN_FREQ] = df.apply(
        lambda x: (round((x[COLUMN_COUNT] / len(edges) * 100), 3)), axis=1
    )
    return df


# MERGE #
def _produce_merge_analysis_for_merged_nss_for_canonical(merges: DataFrame) -> DataFrame:
    df = produce_table_with_namespace_column_pair(
        table=produce_table_with_namespace_column_for_node_ids(table=merges)) \
        .groupby([get_namespace_column_name_for_column(COLUMN_TARGET_ID)]) \
        .agg(count=(COLUMN_SOURCE_ID, 'count'),
             source_nss=(get_namespace_column_name_for_column(COLUMN_SOURCE_ID), lambda x: set(x))) \
        .reset_index() \
        .sort_values(COLUMN_COUNT, ascending=False)
    df["freq"] = df.apply(
        lambda x: (round((x[COLUMN_COUNT] / len(merges) * 100), 3)), axis=1
    )
    return df


# PROCESSING #
def _produce_and_save_alignment_step_node_analysis(
        alignment_step_report: DataFrame,
        section_dataset_name: str,
        data_manager: DataManager,
) -> None:
    mapped_count = 0
    data = []
    for _, row in alignment_step_report.iterrows():
        mapped_count += row['count_mappings']
        data.append([row['step_counter'], mapped_count, "Mapped",
                     f"{row['step_counter']} : {row['source']}"])
        data.append([row['step_counter'], (row['count_unmapped_nodes'] - row['count_mappings']), "Unmapped",
                     f"{row['step_counter']} : {row['source']}"])
    df = pd.DataFrame(data=data, columns=["step", "count", "status", "step_name"])
    start_unmapped = alignment_step_report["count_unmapped_nodes"].iloc[0]
    df["freq"] = df.apply(
        lambda x: (round((x[COLUMN_COUNT] / start_unmapped * 100), 1)), axis=1
    )
    plotly_utils.produce_vertical_bar_chart_stacked(
        analysis_table=df,
        file_path=data_manager.get_analysis_figure_path(
            dataset=section_dataset_name,
            analysed_table_name="step_node_analysis",
            analysis_table_suffix="stacked_bar_chart"
        ),
    )


def _produce_and_save_connectivity_step_node_analysis(
        step_report: DataFrame,
        section_dataset_name: str,
        data_manager: DataManager,
) -> None:
    connected_count = 0
    dangling_start = step_report["count_unmapped_nodes"].sum()
    data = []
    for _, row in step_report.iterrows():
        connected_count += row['count_connected_nodes']
        data.append([row['step_counter'], connected_count, "Connected",
                     f"{row['step_counter']} : {row['source']}"])
        data.append([row['step_counter'], (dangling_start - connected_count), "Dangling",
                     f"{row['step_counter']} : {row['source']}"])
    df = pd.DataFrame(data=data, columns=["step", "count", "status", "step_name"])
    df["freq"] = df.apply(
        lambda x: (round((x[COLUMN_COUNT] / dangling_start * 100), 1)), axis=1
    )
    plotly_utils.produce_vertical_bar_chart_stacked(
        analysis_table=df,
        file_path=data_manager.get_analysis_figure_path(
            dataset=section_dataset_name,
            analysed_table_name="step_node_analysis",
            analysis_table_suffix="stacked_bar_chart"
        ),
    )


# OVERVIEW #
def _produce_and_save_validation_overview_analyses(data_manager: DataManager,
                                                   data_profiling_stats: DataFrame,
                                                   data_test_stats: DataFrame):
    df_merged = pd.merge(
        data_profiling_stats[['directory', 'type', 'name', 'rows', 'columns', 'size_float']],
        data_test_stats[['directory', 'type', 'name', 'nb_validations', 'nb_failed_validations']],
        how="left",
        on=['directory', 'name'],
    )
    summary_data = []
    for directory in [DIRECTORY_INPUT, DIRECTORY_INTERMEDIATE, DIRECTORY_OUTPUT]:
        df = df_merged.query(expr=f"directory == '{directory}'", inplace=False)
        nb_validations = df['nb_validations'].sum()
        nb_failed_validations = df['nb_failed_validations'].sum()
        success_ratio = f"{(nb_validations - nb_failed_validations) / nb_validations * 100:.2f}%"
        summary_data.append(
            [directory, df['name'].count(), df['rows'].sum(), f"{(df['size_float'].sum() / float(1 << 20)):,.2f}MB",
             nb_validations, nb_failed_validations, success_ratio, (True if nb_failed_validations == 0 else False)]
        )
    summary_df = pd.DataFrame(summary_data,
                              columns=['directory', 'tables', 'rows', 'file_size',
                                       'nb_validations', 'nb_failed_validations',
                                       'success_ratio', 'success_status'])
    data_manager.save_analysis_table(
        analysis_table=summary_df,
        dataset=SECTION_OVERVIEW,
        analysed_table_name="data_profiling_and_tests",
        analysis_table_suffix="summary"
    )


# TABLE DATA STATS #
def _get_table_type_for_table_name(table_name: str) -> str:
    if table_name in TABLES_NODE:
        return TABLE_TYPE_NODE
    elif table_name in TABLES_EDGE_HIERARCHY:
        return TABLE_TYPE_EDGE
    elif table_name in TABLES_MAPPING:
        return TABLE_TYPE_MAPPING
    elif table_name in TABLES_MERGE:
        return TABLE_TYPE_MAPPING


def _get_file_size_in_mb_for_named_table(table_name: str,
                                         folder_path: str) -> str:
    f_size = os.path.getsize(os.path.abspath(f"{folder_path}/{table_name}.csv"))
    return f"{f_size / float(1 << 20):,.3f}MB"


def _get_file_size_for_named_table(table_name: str,
                                   folder_path: str) -> float:
    return os.path.getsize(os.path.abspath(f"{folder_path}/{table_name}.csv"))


def _produce_ge_validation_report_map(validation_folder: str) -> dict:
    return {
        str(path).split("validations/")[-1].split("/")[0].replace("_table", ""): str(path).split("output/report/")[-1]
        for path in Path(validation_folder).rglob('*.html')
    }


def _produce_ge_validation_analysis(data_manager: DataManager, ) -> dict:
    data: List[dict] = []
    for path in Path(data_manager.get_ge_json_validations_folder_path()).rglob('*.json'):
        with open(str(path)) as json_file:
            validation_json = json.load(json_file)
            data.append(
                {
                    "table_name": validation_json['meta']['active_batch_definition']['datasource_name'].replace(
                        "_datasource", ""),
                    "directory_name": validation_json['meta']['active_batch_definition']['data_asset_name'].split("_")[
                        0],
                    "nb_validations": validation_json['statistics']['evaluated_expectations'],
                    "success_percent": validation_json['statistics']['success_percent'],
                    "nb_failed_validations": validation_json['statistics']['unsuccessful_expectations'],
                    "success": validation_json['success'],
                    "ge_version": validation_json['meta']["great_expectations_version"],
                }
            )
    data_dic = {
        f"{item['directory_name']}_{item['table_name']}": item
        for item in data
    }
    return data_dic


def _produce_data_profiling_stats_for_directory(tables: List[NamedTable],
                                                folder_path: str,
                                                data_manager: DataManager) -> List[dict]:
    return [
        {
            "type": _get_table_type_for_table_name(table_name=table.name),
            "name": f"{table.name}.csv",
            "rows": len(table.dataframe),
            "columns": len(list(table.dataframe)),
            "size": _get_file_size_in_mb_for_named_table(
                table_name=table.name,
                folder_path=folder_path
            ),
            "size_float": _get_file_size_for_named_table(
                table_name=table.name,
                folder_path=folder_path
            ),
            "report": data_manager.get_profiled_table_report_path(
                table_name=table.name,
                relative_path=True
            )
        }
        for table in tables if "steps_report" not in table.name
    ]


def _produce_data_test_stats_for_directory(tables: List[str],
                                           directory: str,
                                           ge_validation_report_map: dict,
                                           validation_analysis: dict) -> List[dict]:
    return [
        {
            "type": _get_table_type_for_table_name(table_name=table),
            "name": f'{table.replace("_domain", "")}.csv',
            "report": ge_validation_report_map.get(table),
            "nb_validations": validation_analysis[f"{directory}_{table}"]["nb_validations"],
            "nb_failed_validations": validation_analysis[f"{directory}_{table}"]["nb_failed_validations"],
            "success_percent": validation_analysis[f"{directory}_{table}"]["success_percent"],
            "ge_version": validation_analysis[f"{directory}_{table}"]["ge_version"],
        }
        for table in tables if "steps_report" not in table
    ]


def _produce_data_profiling_table_stats(data_manager: DataManager, section_name: str) -> DataFrame:
    main_path = f"{data_manager.get_analysis_folder_path()}/{section_name}"
    input_df = pd.DataFrame(
        _produce_data_profiling_stats_for_directory(
            tables=data_manager.load_input_tables(),
            folder_path=data_manager.get_input_folder_path(),
            data_manager=data_manager
        )
    )
    input_df['directory'] = DIRECTORY_INPUT
    input_df.to_csv(f"{main_path}_{DIRECTORY_INPUT}_{TABLE_STATS}.csv")

    intermed_df = pd.DataFrame(
        _produce_data_profiling_stats_for_directory(
            tables=data_manager.load_intermediate_tables(),
            folder_path=data_manager.get_intermediate_folder_path(),
            data_manager=data_manager
        )
    )
    intermed_df['directory'] = DIRECTORY_INTERMEDIATE
    intermed_df.to_csv(f"{main_path}_{DIRECTORY_INTERMEDIATE}_{TABLE_STATS}.csv")

    output_df = pd.DataFrame(
        _produce_data_profiling_stats_for_directory(
            tables=data_manager.load_output_tables(),
            folder_path=data_manager.get_domain_ontology_folder_path(),
            data_manager=data_manager
        )
    )
    output_df['directory'] = DIRECTORY_OUTPUT
    output_df.to_csv(f"{main_path}_{DIRECTORY_OUTPUT}_{TABLE_STATS}.csv")
    all_df = pd.concat([input_df, intermed_df, output_df])
    return all_df


def _produce_data_testing_table_stats(data_manager: DataManager, section_name: str) -> DataFrame:
    validation_analysis = _produce_ge_validation_analysis(data_manager=data_manager)
    ge_validation_report_map = _produce_ge_validation_report_map(
        validation_folder=data_manager.get_ge_data_docs_validations_folder_path(),
    )
    main_path = f"{data_manager.get_analysis_folder_path()}/{section_name}"

    input_df = pd.DataFrame(
        _produce_data_test_stats_for_directory(
            tables=TABLES_INPUT,
            ge_validation_report_map=ge_validation_report_map,
            validation_analysis=validation_analysis,
            directory=DIRECTORY_INPUT,
        )
    )
    input_df['directory'] = DIRECTORY_INPUT
    input_df.to_csv(f"{main_path}_{DIRECTORY_INPUT}_{TABLE_STATS}.csv")

    intermed_df = pd.DataFrame(
        _produce_data_test_stats_for_directory(
            tables=TABLES_INTERMEDIATE,
            ge_validation_report_map=ge_validation_report_map,
            validation_analysis=validation_analysis,
            directory=DIRECTORY_INTERMEDIATE,
        )
    )
    intermed_df['directory'] = DIRECTORY_INTERMEDIATE
    intermed_df.to_csv(f"{main_path}_{DIRECTORY_INTERMEDIATE}_{TABLE_STATS}.csv")

    output_df = pd.DataFrame(
        _produce_data_test_stats_for_directory(
            tables=TABLES_DOMAIN,
            ge_validation_report_map=ge_validation_report_map,
            validation_analysis=validation_analysis,
            directory="domain",
        )
    )
    output_df['directory'] = DIRECTORY_OUTPUT
    output_df.to_csv(f"{main_path}_{DIRECTORY_OUTPUT}_{TABLE_STATS}.csv")
    all_df = pd.concat([input_df, intermed_df, output_df])
    return all_df


# RUNTIME
def _add_elapsed_seconds_column_to_runtime(runtime: DataFrame) -> DataFrame:
    runtime['elapsed_sec'] = runtime.apply(
        lambda x: f"{x['elapsed']:.2f} sec",
        axis=1
    )
    return runtime


def _produce_and_save_runtime_tables(
        table_name: str,
        section_dataset_name: str,
        data_manager: DataManager,
        data_repo: DataRepository,
) -> None:
    runtime_table = _add_elapsed_seconds_column_to_runtime(
        runtime=data_repo.get(table_name=table_name).dataframe
    )
    # plot
    plotly_utils.produce_gantt_chart(
        analysis_table=runtime_table,
        file_path=data_manager.get_analysis_figure_path(
            dataset=section_dataset_name,
            analysed_table_name="pipeline_steps_report",
            analysis_table_suffix=GANTT_CHART
        ),
        label_replacement={}
    )
    # support table: step duration
    # runtime_table['elapsed_sec'] = runtime_table.apply(
    #     lambda x: timedelta(seconds=int(x['elapsed'])),
    #     axis=1
    # )
    data_manager.save_analysis_table(
        analysis_table=runtime_table[["task", "elapsed_sec"]],
        dataset=section_dataset_name,
        analysed_table_name="pipeline_steps_report",
        analysis_table_suffix="step_duration"
    )
    # support table: runtime overview
    runtime_overview = [
        ("Number of steps", len(runtime_table)),
        ("Total runtime", timedelta(seconds=int(runtime_table['elapsed'].sum()))),
        ("Start", runtime_table["start"].iloc[0]),
        ("End", runtime_table["end"].iloc[len(runtime_table) - 1]),
        # ("Min runtime", timedelta(seconds=(runtime_table['elapsed'].min()))),
        # ("Avg runtime", timedelta(seconds=(runtime_table['elapsed'].mean()))),
        # ("Max runtime", timedelta(seconds=(runtime_table['elapsed'].max()))),
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(runtime_overview, columns=["metric", "value"]),
        dataset=section_dataset_name,
        analysed_table_name="pipeline_steps_report",
        analysis_table_suffix="runtime_overview"
    )


def _get_runtime_for_main_step(
        process_name: str,
        data_repo: DataRepository,
) -> str:
    runtime_df = _add_elapsed_seconds_column_to_runtime(
        runtime=data_repo.get(table_name=TABLE_PIPELINE_STEPS_REPORT).dataframe
    )
    runtime_table_for_process = runtime_df[runtime_df['task'].str.contains(process_name)]
    elapsed = int(runtime_table_for_process['elapsed'].sum())
    return str(timedelta(seconds=elapsed))


# SECTION SUMMARIES #
def _produce_and_save_summary_overview(
        data_manager: DataManager, data_repo: DataRepository, node_status: DataFrame,
) -> None:
    config = data_manager.load_alignment_config()
    steps_report = data_repo.get(table_name=TABLE_PIPELINE_STEPS_REPORT).dataframe
    elapsed_time = timedelta(seconds=int(steps_report['elapsed'].sum()))
    summary = [
        {"metric": "Dataset (folder name)",
         "values": f"<code>{data_manager.get_project_folder_path().split('/')[-1]}</code>"},
        {"metric": "Dataset",
         "values": '<a href="../.." target="_blank">Link</a>'},
        {"metric": "Domain", "values": config.base_config.domain_node_type},
        {"metric": "Seed ontology", "values": config.base_config.seed_ontology_name},
        {"metric": "Total runtime", "values": elapsed_time},
        {"metric": "OntoMerger version", "values": f"<code>{onto_merger_version}</code>"},
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(summary),
        dataset=SECTION_OVERVIEW,
        analysed_table_name=TABLE_SECTION,
        analysis_table_suffix=TABLE_SUMMARY
    )


def _produce_and_save_summary_input(data_manager: DataManager, data_repo: DataRepository) -> None:
    summary = [
        {"metric": "Dataset",
         "values": f'<a href="../../input" target="_blank">Link</a>'},
        {"metric": "Number of nodes", "values": len(data_repo.get(table_name=TABLE_NODES).dataframe)},
        {"metric": "Number of obsolete nodes", "values": len(data_repo.get(table_name=TABLE_NODES_OBSOLETE).dataframe)},
        {"metric": "Number of mappings", "values": len(data_repo.get(table_name=TABLE_MAPPINGS).dataframe)},
        {"metric": "Number of hierarchy edges",
         "values": len(data_repo.get(table_name=TABLE_EDGES_HIERARCHY).dataframe)},
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(summary),
        dataset=SECTION_INPUT,
        analysed_table_name=TABLE_SECTION,
        analysis_table_suffix=TABLE_SUMMARY
    )


def _produce_and_save_summary_output(data_manager: DataManager, data_repo: DataRepository) -> None:
    nodes_connected = produce_table_node_ids_from_edge_table(edges=data_repo.get(TABLE_EDGES_HIERARCHY_POST).dataframe)
    nb_unique_nodes = (len(data_repo.get(table_name=TABLE_NODES).dataframe)
                       - len(data_repo.get(table_name=TABLE_MERGES_AGGREGATED).dataframe))
    summary = [
        {"metric": "Dataset",
         "values": f'<a href="../../output/domain_ontology" target="_blank">Link</a>'},
        {"metric": "Number of unique nodes", "values": nb_unique_nodes},
        {"metric": "Number of merged nodes",
         "values": len(data_repo.get(table_name=TABLE_MERGES_AGGREGATED).dataframe)},
        {"metric": "Number of connected nodes (in hierarchy)", "values": len(nodes_connected)},
        {"metric": "Percentage of connected nodes",
         "values": f"{round(len(nodes_connected) / nb_unique_nodes * 100, 2)}%"},
        {"metric": "Number of dangling nodes (not in hierarchy)",
         "values": f"{len(data_repo.get(TABLE_NODES_DANGLING).dataframe)}"},
        {"metric": "Percentage of dangling nodes",
         "values": f"{round(len(data_repo.get(TABLE_NODES_DANGLING).dataframe) / nb_unique_nodes * 100, 2)}%"},
        {"metric": "Number of mappings", "values": len(data_repo.get(table_name=TABLE_MAPPINGS).dataframe)},
        {"metric": "Number of hierarchy edges",
         "values": len(data_repo.get(table_name=TABLE_EDGES_HIERARCHY).dataframe)},
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(summary),
        dataset=SECTION_OUTPUT,
        analysed_table_name=TABLE_SECTION,
        analysis_table_suffix=TABLE_SUMMARY
    )


def _produce_and_save_summary_alignment(data_manager: DataManager, data_repo: DataRepository) -> None:
    steps_report = data_repo.get(table_name=TABLE_ALIGNMENT_STEPS_REPORT).dataframe
    nodes_input = steps_report['count_unmapped_nodes'].iloc[0]
    nodes_seed = steps_report['count_merged_nodes'].iloc[0]
    nodes_merged = steps_report['count_merged_nodes'].sum() - nodes_seed
    nodes_unmapped = nodes_input - nodes_seed - nodes_merged
    summary = [
        {"metric": "Process runtime",
         "values": _get_runtime_for_main_step(process_name="ALIGNMENT", data_repo=data_repo)},
        {"metric": "Number of steps", "values": len(steps_report)},
        {"metric": "Number of sources", "values": len(set(steps_report['source'].tolist())) - 1},
        {"metric": "Number of mapping type groups used",
         "values": len(set(steps_report['mapping_type_group'].tolist()))},
        {"metric": "Number of input nodes", "values": nodes_input},
        {"metric": "Number of seed nodes", "values": nodes_seed},
        {"metric": "Number of merged nodes (excluding seed)", "values": nodes_merged},
        {"metric": "Number of unmapped nodes", "values": nodes_unmapped},
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(summary),
        dataset=SECTION_ALIGNMENT,
        analysed_table_name=TABLE_SECTION,
        analysis_table_suffix=TABLE_SUMMARY
    )


def _produce_and_save_summary_connectivity(data_manager: DataManager, data_repo: DataRepository) -> None:
    steps_report = data_repo.get(table_name=TABLE_CONNECTIVITY_STEPS_REPORT).dataframe
    nodes_to_connect = len(data_repo.get(table_name=TABLE_NODES_UNMAPPED).dataframe)
    nodes_connected_seed = steps_report['count_connected_nodes'].iloc[0]
    nodes_connected_not_seed = steps_report['count_connected_nodes'].sum() - nodes_connected_seed
    edges_input_df = data_repo.get(table_name=TABLE_EDGES_HIERARCHY).dataframe
    edges_input = len(edges_input_df)
    edges_seed = steps_report['count_available_edges'].iloc[0]
    edges_output = steps_report['count_produced_edges'].sum()
    edges_produced = edges_output - edges_seed
    summary = [
        {"metric": "Process runtime",
         "values": _get_runtime_for_main_step(process_name="CONNECTIVITY", data_repo=data_repo)},
        {"metric": "Number of steps run", "values": len(steps_report)},
        {"metric": "Number of nodes to connect (excluding seed)", "values": nodes_to_connect},
        {"metric": "Number of connected nodes (excluding seed)", "values": nodes_connected_not_seed},
        {"metric": "Number of input hierarchy edges", "values": edges_input},
        {"metric": "Number of seed hierarchy edges", "values": edges_seed},
        {"metric": "Number of produced hierarchy edges", "values": edges_produced},
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(summary),
        dataset=SECTION_CONNECTIVITY,
        analysed_table_name=TABLE_SECTION,
        analysis_table_suffix=TABLE_SUMMARY
    )


def _produce_and_save_summary_data_tests(data_manager: DataManager,
                                         data_repo: DataRepository,
                                         stats: DataFrame) -> None:
    summary = [
        {"metric": "Process runtime",
         "values": _get_runtime_for_main_step(process_name="VALIDATION", data_repo=data_repo)},
        {"metric": "Data docs report",
         "values": '<a href="data_docs/local_site/index.html" target="_blank">Link</a>'},
        {"metric": "Number of tables tested", "values": len(stats)},
        {"metric": "Number of data tests run", "values": stats['nb_validations'].sum()},
        {"metric": "Number of failed tests (input data)",
         "values": stats.query(expr=f"directory == '{DIRECTORY_INPUT}'", inplace=False)
         ['nb_failed_validations'].sum()},
        {"metric": "Number of failed tests (intermediate data)",
         "values": stats.query(expr=f"directory == '{DIRECTORY_INTERMEDIATE}'", inplace=False)
         ['nb_failed_validations'].sum()},
        {"metric": "Number of failed tests (output data)",
         "values": stats.query(expr=f"directory == '{DIRECTORY_OUTPUT}'", inplace=False)
         ['nb_failed_validations'].sum()},
        {"metric": "Total failed tests", "values": stats['nb_failed_validations'].sum()},
        {"metric": "Great Expectations package version", "values": f"<code>{stats['ge_version'].iloc[0]}</code>"},
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(summary),
        dataset=SECTION_DATA_TESTS,
        analysed_table_name=TABLE_SECTION,
        analysis_table_suffix=TABLE_SUMMARY
    )


def _produce_and_save_summary_data_profiling(data_manager: DataManager,
                                             data_repo: DataRepository,
                                             data_profiling_stats: DataFrame) -> None:
    summary = [
        {"metric": "Process runtime",
         "values": _get_runtime_for_main_step(process_name="PROFILING", data_repo=data_repo)},
        {"metric": "Data profiling reports (folder)",
         "values": f'<a href="data_profile_reports/" target="_blank">Link</a>'},
        {"metric": "Number of tables profiled", "values": len(data_profiling_stats)},
        {"metric": "Number of rows profiled", "values": data_profiling_stats['rows'].sum()},
        {"metric": "Total file size",
         "values": f"{data_profiling_stats['size_float'].sum() / float(1 << 20):,.3f}MB"},
        {"metric": "Pandas profiling version package version",
         "values": f"<code>{pandas_profiling_version}</code>"},
    ]
    data_manager.save_analysis_table(
        analysis_table=pd.DataFrame(summary),
        dataset=SECTION_DATA_PROFILING,
        analysed_table_name=TABLE_SECTION,
        analysis_table_suffix=TABLE_SUMMARY
    )
