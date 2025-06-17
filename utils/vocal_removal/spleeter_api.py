from typing import Tuple
import numpy as np
from spleeter.separator import Separator
from spleeter.audio.adapter import AudioAdapter

class SpleeterAPI:
    def __init__(self):
        self.separator = Separator('spleeter:2stems')
        self.audio_loader = AudioAdapter.default()

    def remove_vocal(self, input_wav_path: str) -> Tuple[np.ndarray, int]:
        """
        音频增强函数（修改为返回音频数据和采样率）

        参数: 输入wav文件路径
        返回: (增强后的音频数组, 采样率)
        """
        sample_rate = 44100
        waveform, _ = self.audio_loader.load(input_wav_path, sample_rate=sample_rate)
        # Perform the separation :
        prediction = self.separator.separate(waveform)

        accompaniment = prediction['accompaniment']

        return accompaniment, sample_rate
