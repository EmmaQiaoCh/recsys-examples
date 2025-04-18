# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from dataclasses import dataclass
from enum import Enum, unique
from typing import Optional

import torch
from megatron.core import parallel_state
from megatron.core.transformer import TransformerConfig


@unique
class KernelBackend(Enum):
    """
    Enum class representing different kernel backends.

    Attributes:
      TRITON: Represents the TRITON backend.
      PYTORCH: Represents the PYTORCH backend.
      CUTLASS: Represents the CUTLASS backend.
    """

    TRITON = "TRITON"
    PYTORCH = "PYTORCH"
    CUTLASS = "CUTLASS"


@dataclass
class PositionEncodingConfig:
    """
    Configuration data class for position encoding settings.

    Args:
      num_position_buckets: The number of buckets used for position encoding.
      num_time_buckets: The number of buckets used for time encoding.
      use_time_encoding: A boolean flag indicating whether time encoding should be used.

    """

    num_position_buckets: int
    num_time_buckets: int
    use_time_encoding: bool


@dataclass
class HSTUConfig(TransformerConfig):
    """
    HSTUConfig is a configuration data class for the HSTU model, inheriting from TransformerConfig.

    Args:
      position_encoding_config (PositionEncodingConfig): Position embedding config. Defaults to None.
      is_causal (bool): Indicates if the model is causal. Defaults to True.
      enable_relative_attention_bias (bool): Flag to enable relative attention bias. Defaults to False.
      kernel_backend (KernelBackend): Backend for kernel operations. Defaults to KernelBackend.CUTLASS.
      target_group_size (int): The size of the sub-candidate group where causal attention is applied only within a sub-group (usually in the case of ranking). Defaults to 1.
    """

    position_encoding_config: Optional[PositionEncodingConfig] = None
    is_causal: bool = True
    enable_relative_attention_bias: bool = False

    kernel_backend: KernelBackend = KernelBackend.CUTLASS

    target_group_size: int = 1

    def __post_init__(self):
        super().__post_init__()


def get_hstu_config(
    hidden_size,
    kv_channels,
    num_attention_heads,
    num_layers,
    init_method,
    dtype,
    position_encoding_config: Optional[PositionEncodingConfig] = None,
    hidden_dropout=0.2,
    norm_epsilon=1e-5,
    is_causal: bool = True,
    kernel_backend: KernelBackend = KernelBackend.CUTLASS,
    target_group_size: int = 1,
) -> HSTUConfig:
    """
    Create the HSTU configuration.

    Args:
        hidden_size (int): The hidden dimension size.
        kv_channels (int): Number of key-value channels (per attention head).
        num_attention_heads (int): Number of attention heads.
        num_layers (int): Number of attention layers.
        init_method (Callable): Initialization method. A callable that takes a tensor and initializes it. Note that this is only used to initialize the weight of the linear layers. The bias is initialized to zero.
        dtype (torch.dtype): Data type (e.g., torch.float16).
        position_encoding_config (Optional[PositionEncodingConfig], optional): Position embedding config. Defaults to None.
        hidden_dropout (float, optional): Dropout rate for hidden layers. Defaults to 0.2.
        norm_epsilon (float, optional): Epsilon value for normalization. Defaults to 1e-5.
        is_causal (bool, optional): Whether the attention is causal. Defaults to False.
        kernel_backend (KernelBackend, optional): Backend for kernel operations. Defaults to KernelBackend.CUTLASS.

    Returns:
        HSTUConfig: The HSTU configuration object.
    """
    is_bf16 = dtype == torch.bfloat16
    is_fp16 = dtype == torch.float16

    return HSTUConfig(  # type: ignore
        position_encoding_config=position_encoding_config,
        hidden_size=hidden_size,
        kv_channels=kv_channels,
        num_attention_heads=num_attention_heads,
        hidden_dropout=hidden_dropout,
        layernorm_epsilon=norm_epsilon,
        num_layers=num_layers,
        bf16=is_bf16,
        tensor_model_parallel_size=parallel_state.get_tensor_model_parallel_world_size(),
        pipeline_model_parallel_size=parallel_state.get_pipeline_model_parallel_world_size(),
        context_parallel_size=parallel_state.get_pipeline_model_parallel_world_size(),
        init_method=init_method,
        fp16=is_fp16,
        is_causal=is_causal,
        kernel_backend=kernel_backend,
        target_group_size=target_group_size,
    )
