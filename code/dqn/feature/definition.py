# !/usr/bin/env python3
# -*- coding: UTF-8 -*-
###########################################################################
# Copyright © 1998 - 2024 Tencent. All Rights Reserved.
###########################################################################
"""
Author: Tencent AI Arena Authors
"""


from kaiwu_agent.utils.common_func import create_cls, attached
import numpy as np
from dqn.config import Config
from dqn.feature.traffic_utils import *


SampleData = create_cls(
    "SampleData",
    obs=None,
    _obs=None,
    act=None,
    rew=None,
    ret=None,
    done=None,
    sub_action_mask=None,
    _sub_action_mask=None,
)

ObsData = create_cls("ObsData", feature=None, sub_action_mask=None)

ActData = create_cls("ActData", junction_id=None, phase_index=None, duration=None)


@attached
def observation_process(raw_obs, traffic_handler, env_info=None):
    """
    This function is an important function for feature processing, mainly responsible for:
        - Parsing raw data from proto data
        - Calculating features through raw data to obtain multiple feature vectors
        - Concatenation of features
        - Labeling of legal actions

    Args:
        - raw_obs: Raw feature data sent by battlesrv

    Returns:
        - ObsData: A variable containing observation and sub_action_mask
    """
    """
        该函数是特征处理的重要函数, 主要负责：
            - 从 proto 数据中解析原始数据
            - 通过原始数据计算特征, 得到多个特征向量
            - 特征的拼接
            - 合法动作的标注

        参数：
            - raw_obs: battlesrv 发送的原始特征数据

        返回：
            - ObsData: 包含 observation 与 sub_action_mask 的变量
    """
    observation, sub_action_mask = (
        [],
        [[]],
    )

    # Note: The unpacking of the following raw data is for example purposes only,
    # please modify according to the actual situation
    # 注意: 以下原始数据的解包为示例, 请根据实际情况修改
    frame_state = raw_obs[1].framestate

    # Parse frame_state
    # 解析 frame_state
    frame_no, frame_time, vehicles = frame_state.frame_no, frame_state.frame_time, frame_state.vehicles

    # Divide the lane into several grids along the lane direction and the vehicle driving direction
    # 沿车道方向和车辆行驶方向将车道划分为数个栅格
    speed_dict = {}
    position_dict = {}
    for junction_id in traffic_handler.traffic_info.junction_dict.keys():
        speed_dict[junction_id] = np.zeros((Config.GRID_WIDTH, Config.GRID_NUM))
        position_dict[junction_id] = np.zeros((Config.GRID_WIDTH, Config.GRID_NUM))

    # The default value of junction_id in a single intersection scenario is 0
    # 单交叉口场景junction_id默认为0
    junction_id = 0

    # Initialize state-related variables to prevent errors when there are no vehicles in the traffic scenario
    # 初始化状态相关变量, 防止交通场景内车辆为空时报错
    position = list(position_dict[junction_id].astype(int).flatten())
    speed = list(speed_dict[junction_id].flatten())

    for vehicle in vehicles:
        # Only count vehicles on the enter lane
        # 仅统计位于进口车道上的车辆信息
        if on_enter_lane(vehicle):
            # Convert the vehicle x,y coordinates to grid coordinates. Here,
            # get_lane_code maps the lane number to integers 0-13, corresponding to 14 import lanes
            # 将车辆x,y坐标转化为栅格坐标, 此处get_lane_code将车道编号映射至整数0-13, 对应14条进口车道
            x_pos = get_lane_code(vehicle)
            y_pos = int((vehicle.position_in_lane.y / 1000) // Config.GRID_LENGTH)

            if y_pos >= Config.GRID_NUM:
                continue

            speed_dict[vehicle.target_junction][x_pos, y_pos] = float(
                vehicle.speed / traffic_handler.traffic_info.vehicle_configs_dict[vehicle.v_config_id].max_speed
            )
            position_dict[vehicle.target_junction][x_pos, y_pos] = 1
        else:
            continue

    position = list(position_dict[junction_id].astype(int).flatten())
    speed = list(speed_dict[junction_id].flatten())

    # Integrate all state quantities into the observation
    # 将所有状态量整合在observation中
    observation = position + speed

    return ObsData(feature=observation, sub_action_mask=sub_action_mask)


@attached
def action_process(act_data):
    junction_id = act_data.junction_id
    phase_index = act_data.phase_index
    duration = act_data.duration * 1000
    return [junction_id, phase_index, duration]


@attached
def sample_process(list_game_data):
    r_data = np.array(list_game_data).squeeze()

    sample_datas = []
    for data in r_data:

        sample_data = SampleData(
            obs=data.obs,
            _obs=data._obs,
            sub_action_mask=data.sub_action_mask[0],
            _sub_action_mask=data._sub_action_mask[0],
            act=data.act,
            rew=data.rew,
            ret=data.ret,
            done=data.done,
        )
        # Convert time to align with the training data format
        # 转换时间与训练数据格式对齐
        sample_data.act[2] = int(sample_data.act[2] / 1000)

        sample_datas.append(sample_data)

    return sample_datas


def reward_shaping(raw_obs, traffic_handler, env_info=None):
    """
    This function is an important function for reward processing, mainly responsible for:
        - Unpacking data, obtaining the data required for reward calculation from raw_obs
        - Reward calculation, calculating rewards based on the unpacked data
        - Reward concatenation, concatenating all rewards into a list

    Parameters:
        - raw_obs: The original feature data sent by battlesrv
        - phase: The previous phase number predicted and executed
        - duration: The duration of the previous phase predicted and executed

    Returns:
        - phase reward: The reward corresponding to the action of the phase number
        - duration reward: The reward corresponding to the action of the phase duration
    """
    """
    该函数是奖励处理的重要函数, 主要负责：
        - 数据解包, 从 raw_obs 获取计算奖励所需要的数据
        - 奖励计算, 根据解包的数据计算奖励
        - 奖励拼接, 将所有的奖励拼接成一个list

    参数：
        - raw_obs: battlesrv 发送的原始特征数据
        - phase: 前一次预测并执行的相位编号
        - duration: 前一次预测并执行的相位持续时间

    返回：
        - phase reward: 对应相位编号动作的奖励
        - duration reward: 对应相位持续时间动作的奖励
    """
    junction_id = 0
    phase_reward, duration_reward = 0, 0

    frame_state = raw_obs[1].framestate
    vehicles = frame_state.vehicles

    # The difference in vehicle waiting time is used as a reward
    # 车辆等待时间差值作为奖励
    current_waiting_time = traffic_handler.traffic_info.get_all_junction_waiting_time(vehicles)[junction_id]
    phase_reward = (traffic_handler.traffic_info.old_waiting_time - current_waiting_time + 1000.0) / 1000.0
    duration_reward = (traffic_handler.traffic_info.old_waiting_time - current_waiting_time + 1000.0) / 1000.0

    traffic_handler.traffic_info.old_waiting_time = current_waiting_time
    return phase_reward, duration_reward


# SampleData <----> NumpyData
@attached
def SampleData2NumpyData(g_data):
    return np.hstack(
        (
            np.array(g_data.obs, dtype=np.float32),
            np.array(g_data._obs, dtype=np.float32),
            np.array(g_data.sub_action_mask, dtype=np.float32),
            np.array(g_data._sub_action_mask, dtype=np.float32),
            np.array(g_data.act, dtype=np.float32),
            np.array(g_data.rew, dtype=np.float32),
            np.array(g_data.ret, dtype=np.float32),
            np.array(g_data.done, dtype=np.float32),
        )
    )


@attached
def NumpyData2SampleData(s_data):
    return SampleData(
        obs=s_data[: Config.DIM_OF_OBSERVATION],
        _obs=s_data[Config.DIM_OF_OBSERVATION : Config.DIM_OF_OBSERVATION * 2],
        sub_action_mask=s_data[
            Config.DIM_OF_OBSERVATION * 2 : Config.DIM_OF_OBSERVATION * 2 + Config.DIM_SUB_ACTION_MASK
        ],
        _sub_action_mask=s_data[-8 - Config.DIM_SUB_ACTION_MASK : -8],
        act=s_data[-8:-5],
        rew=s_data[-5:-3],
        ret=s_data[-3:-1],
        done=s_data[-1],
    )
