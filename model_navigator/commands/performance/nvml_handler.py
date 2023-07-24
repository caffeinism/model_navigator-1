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
"""NVML handler."""

from typing import ContextManager, Optional

import numpy as np
from pynvml import (
    NVML_CLOCK_GRAPHICS,
    NVMLError,
    nvmlDeviceGetClockInfo,
    nvmlDeviceGetComputeRunningProcesses,
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    nvmlInit,
    nvmlShutdown,
)


class NvmlHandler(ContextManager):
    """Context manager for initializing and shutting down NVML."""

    def __init__(self) -> None:
        """Creates NVML context manager."""
        self._nvml_exists = False

    def __enter__(self) -> "NvmlHandler":
        """Initializes NVML."""
        try:
            nvmlInit()
            self._nvml_exists = True
        except NVMLError:
            self._nvml_exists = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Shuts down NVML."""
        if self._nvml_exists:
            nvmlShutdown()
            self._nvml_exists = False

    @property
    def gpu_clock(self) -> Optional[float]:
        """Returns average gpu clock frequency in MHz for running gpus (if they exist)."""
        if not self._nvml_exists:
            return None

        gpus_running = 0
        gpu_clocks_sum = 0
        for i in range(self.gpu_count):
            handle = nvmlDeviceGetHandleByIndex(i)
            if len(nvmlDeviceGetComputeRunningProcesses(handle)) > 0:
                gpus_running += 1
                gpu_clocks_sum += nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS)
        with np.errstate(invalid="ignore"):
            return np.divide(gpu_clocks_sum, gpus_running)

    @property
    def gpu_count(self) -> int:
        """Returns number of available gpus."""
        if not self._nvml_exists:
            return 0
        return nvmlDeviceGetCount()
