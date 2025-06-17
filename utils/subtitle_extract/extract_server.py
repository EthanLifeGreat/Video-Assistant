from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response
import uvicorn
import os
import tempfile
from typing import Optional
import uuid
import shutil
import logging

from whisperx_api import WhisperXAPI

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subtitles-api")



asr_model = WhisperXAPI()

app = FastAPI(
    title="字幕提取微服务",
    description="提供音频/视频文件字幕提取服务",
    version="1.0.0"
)


@app.get("/health")
def health_check():
    """服务健康检查端点"""
    return {"status": "ok", "message": "字幕提取服务正常运行"}


@app.post("/extract")
async def extract_subtitles(
        audio_file: UploadFile = File(..., description="上传的音频文件（支持wav/mp3等格式）"),
        return_type: str = "file",  # 支持file或text
        output_filename: Optional[str] = None
):
    """
    接收音频文件并返回SRT字幕文件或文本内容

    选项:
    - return_type: 返回类型 (file | text)
    - output_filename: 指定输出文件名（仅当返回文件时有效）
    """
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    logger.info(f"创建临时目录: {temp_dir}")

    try:
        # 保存上传的音频文件
        audio_path = os.path.join(temp_dir, audio_file.filename)
        with open(audio_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
            logger.info(f"保存上传文件 ({len(content)} 字节): {audio_file.filename}")

        # 调用字幕提取方法
        logger.info("开始字幕提取...")
        srt_content = asr_model.transcribe(audio_path)
        logger.info(f"成功提取字幕 ({len(srt_content)} 字符)")

        # 根据请求类型返回结果
        if return_type == "text":
            # 直接返回文本内容
            return {"filename": audio_file.filename, "content": srt_content}

        # 文件返回处理
        if not output_filename:
            base_name = os.path.splitext(audio_file.filename)[0]
            output_filename = f"{base_name}.srt"

        # 保存SRT文件
        srt_path = os.path.join(temp_dir, output_filename)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        logger.info(f"字幕文件保存到: {srt_path}")

        # 返回SRT文件 (使用Response确保文件发送完成后删除)
        return FileResponse(
            srt_path,
            media_type="application/x-subrip",
            filename=output_filename,
            background=shutil.rmtree(temp_dir)
        )
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"字幕提取失败: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9091, access_log=False)