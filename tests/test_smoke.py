import importlib

import pytest

MODULES = [
    "agent",
    "agent.cli",
    "agent.figma_client",
    "agent.ir_parser",
    "agent.planner",
    "agent.codegen",
    "agent.validator",
    "agent.repair",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_importable(module_name: str) -> None:
    importlib.import_module(module_name)
