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
import logging
import math
from typing import Optional

import model_navigator as nav


def dle_convnets_tf(
    model_name: str,
    max_batch_size: Optional[int] = None,
    trt_profile: Optional[nav.TensorRTProfile] = None,
):
    import tensorflow as tf  # pytype: disable=import-error
    from config.defaults import Config, base_config  # pytype: disable=import-error

    gpus = tf.config.experimental.list_physical_devices("GPU")
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

    logger = logging.getLogger(__package__)
    logger.info(f"Testing {model_name}...")
    if model_name == "EfficientNet-v1-B0":
        from config.efficientnet_v1.b0_cfg import config as model_config  # pytype: disable=import-error
        from model.efficientnet_model_v1 import Model  # pytype: disable=import-error
    elif model_name == "EfficientNet-v1-B4":
        from config.efficientnet_v1.b4_cfg import config as model_config  # pytype: disable=import-error
        from model.efficientnet_model_v1 import Model  # pytype: disable=import-error
    elif model_name == "EfficientNet-v2-S":
        from config.efficientnet_v2.s_cfg import config as model_config  # pytype: disable=import-error
        from model.efficientnet_model_v2 import Model  # pytype: disable=import-error
    else:
        raise ValueError(f"Unknown model: {model_name}")

    config = Config(**{**base_config.train, **base_config.runtime, **base_config.data, **base_config.predict})
    config.mparams = Config(model_config)
    config.num_classes = config.mparams.num_classes
    config.train_batch_size = config.batch_size
    config.mode = "predict"

    model = Model(config)

    dataloader = [tf.random.uniform(shape=[max_batch_size, 224, 224, 3], minval=0, maxval=1, dtype=tf.dtypes.float32)]

    custom_configs = [nav.OnnxConfig(opset=13)]
    if trt_profile:
        custom_configs.extend(
            [
                nav.TensorRTConfig(
                    trt_profile=trt_profile,
                ),
                nav.TensorFlowTensorRTConfig(
                    trt_profile=trt_profile,
                ),
            ]
        )

    batch_sizes = None
    if max_batch_size:
        pow2 = math.ceil(math.log(max_batch_size, 2)) + 1
        batch_sizes = [2**n for n in range(pow2)]

    package = nav.tensorflow.optimize(
        model=model,
        dataloader=dataloader,
        verbose=True,
        custom_configs=custom_configs,
        profiler_config=nav.ProfilerConfig(batch_sizes=batch_sizes),
    )
    return package