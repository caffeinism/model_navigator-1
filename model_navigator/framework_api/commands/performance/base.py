# Copyright (c) 2021-2022, NVIDIA CORPORATION. All rights reserved.
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

from typing import List, Optional

import numpy
from polygraphy.backend.base import BaseRunner

from model_navigator.framework_api.commands.core import Command, Performance
from model_navigator.framework_api.common import Sample


def expand_sample(sample: Sample, axis: int, n: int):
    expanded_sample = {}
    for name, tensor in sample.items():
        expanded_sample[name] = tensor.repeat(n, axis=axis)
    return expanded_sample


class PerformanceBase(Command):
    def _get_runner(self, **kwargs) -> BaseRunner:
        raise NotImplementedError

    def __call__(
        self,
        profiling_sample: Sample,
        batch_dim: Optional[int],
        max_batch_size: Optional[int],
        **kwargs,
    ) -> List[Performance]:

        runner = self._get_runner(profiling_sample=profiling_sample, **kwargs)

        expanded_sample = (
            expand_sample(profiling_sample, batch_dim, max_batch_size) if batch_dim is not None else profiling_sample
        )

        time_measurements = {1: [], max_batch_size: []}
        with runner:
            for _ in range(10):
                runner.infer(profiling_sample)
                time_measurements[1].append(runner.last_inference_time())

                runner.infer(expanded_sample)
                time_measurements[max_batch_size].append(runner.last_inference_time())

        latency = {key: float(numpy.median(val)) for key, val in time_measurements.items()}
        return [Performance(key, latency_sec * 1000, 1 / latency_sec) for key, latency_sec in latency.items()]
