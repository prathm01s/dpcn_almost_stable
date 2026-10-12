"""Pipeline runner for Phase 1: Data Collection.

Sequentially executes all collection and processing stages:
01 -> 02 -> 03 -> 04 -> 05 -> 06 -> 07 -> 08 -> 10 -> 11 -> 14 -> 13
"""

import importlib
from src.common.logging import get_logger

logger = get_logger("collect_main")

STEPS = [
    ("src.collect.01_resolve_institutions", "run_step_01"),
    ("src.collect.02_build_roster", "run_step_02"),
    ("src.collect.03_pull_works", "run_step_03"),
    ("src.collect.04_recall_boosters", "run_step_04"),
    ("src.collect.05_filter_works", "run_step_05"),
    ("src.collect.06_attribute_authors", "run_step_06"),
    ("src.collect.07_match_faculty", "run_step_07"),
    ("src.collect.08_resolve_quartiles", "run_step_08"),
    ("src.collect.10_coauthor_institutes", "run_step_10"),
    ("src.collect.11_indian_citation_flags", "run_step_11"),
    ("src.collect.14_export", "run_step_14"),
    ("src.collect.13_validation_qa", "run_step_13"),
]


def main() -> None:
    logger.info("=== Starting Phase 1: Full Collection Pipeline ===")
    for module_name, func_name in STEPS:
        logger.info(f"--> Executing {module_name}.{func_name}...")
        mod = importlib.import_module(module_name)
        func = getattr(mod, func_name)
        func()
    logger.info("=== Phase 1 Pipeline Completed Successfully! ===")


if __name__ == "__main__":
    main()
