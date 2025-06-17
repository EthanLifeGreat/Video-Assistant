from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
import numpy as np
import soundfile as sf  # 用于音频文件读写
import io
import tempfile
import os
from typing import Optional, Tuple

from spleeter_api import SpleeterAPI

vr_model = SpleeterAPI()

def remove(input_wav_path: str) -> Tuple[np.ndarray, int]:
    """
    人声去除函数（修改为返回音频数据和采样率）

    参数: 输入wav文件路径
    返回: (去除后的音频数组, 采样率)
    """
    try:

        # 执行去除处理
        enhanced_audio, sample_rate = vr_model.remove_vocal(input_wav_path)

        return enhanced_audio, sample_rate

    except Exception as e:
        print(f"人声去除失败: {str(e)}")
        raise


app = FastAPI(title="伴奏提取微服务")


@app.post("/remove")
async def remove_vocal(
        audio_file: UploadFile = File(..., description="上传的音频文件（支持wav/mp3等格式）"),
        output_format: Optional[str] = "wav"
):
    """
    接收音频文件并返回增强后的音频文件
    """
    # 支持的输出格式
    SUPPORTED_FORMATS = ["wav", "flac", "ogg"]
    if output_format.lower() not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的输出格式，请选择: {', '.join(SUPPORTED_FORMATS)}"
        )

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 保存上传的音频文件
            input_path = os.path.join(temp_dir, audio_file.filename)
            with open(input_path, "wb") as f:
                f.write(await audio_file.read())

            # 调用音频增强方法
            enhanced_audio, sample_rate = remove(input_path)

            # 将numpy数组转为音频字节流
            audio_bytes = io.BytesIO()
            sf.write(audio_bytes, enhanced_audio, sample_rate, format=output_format.lower())
            audio_bytes.seek(0)

            # 确定输出文件名
            base_name = os.path.splitext(audio_file.filename)[0]
            output_filename = f"{base_name}_enhanced.{output_format.lower()}"

            # 返回音频文件流
            return StreamingResponse(
                audio_bytes,
                media_type=f"audio/{output_format.lower()}",
                headers={"Content-Disposition": f"attachment; filename={output_filename}"}
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"音频增强失败: {str(e)}"
            )


if __name__ == "__main__":
    # 启动伴奏提取微服务
    uvicorn.run(app, host="0.0.0.0", port=9093)