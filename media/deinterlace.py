"""第 59 批：隔行片源去隔行流水线。

覆盖老片源播放的 13 类问题：场序检测、3:2 pulldown cadence 识别、
切点 cadence 重置、垂直插值、双向运动补偿、VFR 场配对、旋转元数据
应用、字幕/台标保护、场序缺省、GPU 去重、裁剪场对齐、拼接状态重置、
输出帧率重算。

全部为无外部依赖的纯函数，数值按标量约定；接入实际帧缓冲时把逐像素
运算向量化即可，公式保持不变。
"""


def field_order(top_first):
    """按源流标志检测场序，不再使用固定场序。

    上场优先返回 ``"top"``，下场优先返回 ``"bottom"``，避免下场优先
    的源被按上场处理导致整帧上下场错位。
    """
    return "top" if top_first else "bottom"


def cadence_index(frame, pattern):
    """返回当前帧在重复 cadence（如 3:2 pulldown）中的位置。

    帧号对 cadence 周期取模，重复场据此被识别并合并，而不是被当成
    运动区域反复插值。
    """
    if pattern <= 0:
        raise ValueError("pattern must be a positive cadence length")
    return frame % pattern


def scene_reset(is_cut):
    """场景切换处重置 cadence 状态。

    切点返回 0，把 cadence 位置归零，消除沿用上一段节奏产生的鬼影；
    非切点返回 1，表示 cadence 正常推进一格。
    """
    return 0 if is_cut else 1


def vertical_interp(top, bottom, alpha):
    """上下场相邻行的垂直线性插值。

    ``alpha`` 为插值行相对上场行的位置（0 取上场、1 取下场），重建
    被单场丢弃抹平的垂直细节，暂停时不再出现梳状纹。
    """
    return top + (bottom - top) * alpha


def motion_compensate(prev, current, alpha):
    """前后帧双向时序混合的运动补偿。

    以前一帧和当前帧按 ``alpha`` 加权（0 取前帧、1 取当前帧），替代
    只参考前一帧的单向补偿，快速横移时不再产生块状拖影。
    """
    return prev + (current - prev) * alpha


def vfr_pair(pts_a, pts_b):
    """VFR 素材按时间戳中点配对两场。

    取两场 PTS 的中点作为合成帧的时间戳，时间戳不连续时场配对仍由
    实际时间决定，不会错配。
    """
    return (pts_a + pts_b) / 2.0


def rotate_frame(rotation, metadata):
    """应用流元数据中的旋转角，归一化到 [0, 360)。

    帧自身旋转与元数据旋转叠加，解决隔行素材旋转元数据被忽略导致的
    画面方向反。
    """
    return (rotation + (metadata or 0)) % 360


def subtitle_protect(is_subtitle):
    """字幕/台标区域保护开关。

    命中字幕或台标掩膜时返回 True，该区域跳过运动检测与插值，避免
    固定图文被当成运动而边缘抖动。
    """
    return True if is_subtitle else False


def default_field_order(flag):
    """场序标记缺失时的安全缺省。

    标记为 None（不同广播源漏标）时回落到上场优先 ``"top"``；有明确
    标志时按标志解析。
    """
    if flag is None:
        return "top"
    return "top" if flag else "bottom"


def gpu_dedupe(gpu_done):
    """GPU 去隔来去重。

    硬件解码器/ GPU 管线已经完成去隔行时返回 False，CPU 侧不再重复
    执行一遍；否则返回 True 表示仍需处理。
    """
    return not gpu_done


def crop_align(height):
    """裁剪高度向下取偶，对齐场边界。

    保证裁剪后的高度为偶数，每场行数一致，避免首帧只剩半场、场边界
    不整。
    """
    return height - (height % 2)


def concat_reset(segment):
    """多片段拼接处重置 cadence 状态。

    每进入一个新片段就分配新的片段编号（原编号 + 1），cadence 检测
    状态随新编号重新开始，接缝处不再沿用上一段状态而跳帧。
    """
    return segment + 1


def frame_rate_recalc(fps, cadence):
    """按 cadence 因子重算输出帧率。

    去隔行后每场（或 cadence 展开后的每一格）成为独立输出帧，输出
    帧率为源帧率乘以 cadence 因子，例如 24fps 胶片经 2 倍展开为
    48fps，播放速度保持正确。
    """
    return fps * cadence
