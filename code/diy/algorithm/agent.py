# !/usr/bin/env python3
# -*- coding: UTF-8 -*-
###########################################################################
# Copyright © 1998 - 2024 Tencent. All Rights Reserved.
###########################################################################
"""
Author: Tencent AI Arena Authors
"""


import torch

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

from kaiwu_agent.agent.base_agent import (
    predict_wrapper,
    exploit_wrapper,
    learn_wrapper,
    save_model_wrapper,
    load_model_wrapper,
    BaseAgent,
)
from diy.model.model import Model
from kaiwu_agent.utils.common_func import attached
from diy.feature.definition import ActData
from diy.feature.definition import *
from diy.config import Config


@attached
class Agent(BaseAgent):
    def __init__(self, agent_type="player", device=None, logger=None, monitor=None):
        super().__init__(agent_type, device, logger, monitor)

    @predict_wrapper
    def predict(self, list_obs_data):
        pass

    @exploit_wrapper
    def exploit(self, list_obs_data):
        pass

    @learn_wrapper
    def learn(self, list_sample_data):
        pass

    @save_model_wrapper
    def save_model(self, path=None, id="1"):
        pass

    @load_model_wrapper
    def load_model(self, path=None, id="1"):
        pass
