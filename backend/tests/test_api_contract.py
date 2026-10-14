from pathlib import Path
from typing import Any

import yaml

from app.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
CONTRACT_PATH = Path(__file__).parents[2] / "docs" / "api" / "openapi.yaml"


def test_implemented_routes_exist_in_source_contract() -> None:
    contract: dict[str, Any] = yaml.safe_load(CONTRACT_PATH.read_text())
    contract_paths = contract["paths"]
    runtime_paths = app.openapi()["paths"]

    for runtime_path, runtime_operations in runtime_paths.items():
        contract_path = runtime_path.removeprefix("/api/v1")
        assert contract_path in contract_paths

        for method in HTTP_METHODS.intersection(runtime_operations):
            runtime_operation = runtime_operations[method]
            contract_operation = contract_paths[contract_path].get(method)
            assert contract_operation is not None
            assert runtime_operation["operationId"] == contract_operation["operationId"]
