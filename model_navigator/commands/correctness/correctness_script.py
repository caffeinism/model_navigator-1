# Copyright (c) 2021-2023, NVIDIA CORPORATION. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Script for running correctness tests on a runner."""

import json
import pathlib
import sys
from typing import List, Optional

import fire
import numpy as np
from polygraphy.comparator import util as comp_util

from model_navigator.commands.correctness.correctness import Tolerance, TolerancePerOutputName
from model_navigator.logger import LOGGER
from model_navigator.runners.registry import get_runner
from model_navigator.utils.dataloader import load_samples
from model_navigator.utils.tensor import TensorMetadata


def get_model() -> object:
    """Get model instance.

    Returns:
        Model to be tested for correctness.
    """
    raise NotImplementedError(
        "Please implement the get_model() function if model cannot be read by the runner from the path."
    )


def correctness(
    batch_dim: int,
    results_path: str,
    runner_name: str,
    input_metadata: List,
    output_metadata: List,
    navigator_workspace: Optional[str] = None,
    model_path: Optional[str] = None,
) -> None:
    """Run correcntess tests.

    Args:
        batch_dim (int): Batch dimension.
        results_path (str): Output results path.
        runner_name (str): Name of the model's runner.
        input_metadata (List): Input metadata.
        output_metadata (List): Output metadata.
        navigator_workspace (Optional[str], optional): Model Navigator workspace path.
            When None use current workdir. Defaults to None.
        model_path (Optional[str], optional): Path to the model.
            When None use `get_model()` to load the model. Defaults to None.
    """
    if not navigator_workspace:
        navigator_workspace = pathlib.Path.cwd()
    navigator_workspace = pathlib.Path(navigator_workspace)

    correctness_samples = load_samples("correctness_samples", navigator_workspace, batch_dim)
    correctness_samples_output = load_samples("correctness_samples_output", navigator_workspace, batch_dim)

    if model_path:
        model = navigator_workspace / model_path
    else:
        model = get_model()

    input_metadata = TensorMetadata.from_json(input_metadata)
    output_metadata = TensorMetadata.from_json(output_metadata)
    runner = get_runner(runner_name)(
        model=model,
        input_metadata=input_metadata,
        output_metadata=output_metadata,
    )  # pytype: disable=not-instantiable

    per_output_tolerance = TolerancePerOutputName({name: Tolerance(0.0, 0.0) for name in output_metadata})
    with runner:
        for sample, original_output in zip(correctness_samples, correctness_samples_output):
            comp_output = runner.infer(sample)

            is_len_valid = len(original_output) == len(comp_output)
            if not is_len_valid:
                LOGGER.error("Original model output length is different from exported model output")
                sys.exit(1)

            for name in output_metadata:
                if any(np.isnan(comp_output[name]).flatten()):
                    LOGGER.error("Comparison output contains NaN")
                    sys.exit(1)

                if any(np.isinf(comp_output[name]).flatten()):
                    LOGGER.error("Comparison output contains inf")
                    sys.exit(1)

                out0, out1 = original_output[name], comp_output[name]
                absdiff = np.abs(out0 - out1)
                absout1 = np.abs(out1)

                reldiff = absdiff / absout1
                max_reldiff = comp_util.compute_max(reldiff)
                max_absdiff = comp_util.compute_max(absdiff)

                if max_absdiff > per_output_tolerance[name].atol:
                    per_output_tolerance[name].atol = float(max_absdiff)
                if max_reldiff > per_output_tolerance[name].rtol:
                    per_output_tolerance[name].rtol = float(max_reldiff)

    results_path = pathlib.Path(results_path)
    with results_path.open("w") as f:
        json.dump(per_output_tolerance.to_json(), f)


if __name__ == "__main__":
    fire.Fire(correctness)