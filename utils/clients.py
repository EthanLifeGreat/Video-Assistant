from typing import Optional

import requests
import os
import time
import logging
import subprocess
import tempfile
import shutil



def extract_audio_from_video(video_path, output_audio_format="wav"):
    """
    从视频中提取音频
    """
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, f"original_audio.{output_audio_format}")

    # 使用FFmpeg提取音频
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",  # 禁用视频流
        "-acodec", "pcm_s16le",  # WAV格式
        "-ar", "44100",  # 采样率
        "-ac", "2",  # 声道
        "-y",  # 覆盖输出
        audio_path
    ]

    logger.info(f"提取音频: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"音频提取失败: {result.stderr}")
        shutil.rmtree(temp_dir)
        return None, None

    logger.info(f"音频提取成功: {audio_path}")
    return audio_path, temp_dir


def combine_audio_video(video_path: str, audio_path: str, output_video_path: str) -> bool:
    """
    合并音频和视频文件

    参数:
        video_path (str): 输入视频文件路径（不含音频）
        audio_path (str): 输入音频文件路径
        output_video_path (str): 输出视频文件路径

    返回:
        bool: 处理是否成功
    """
    cmd = [
        "ffmpeg",
        "-i", video_path,  # 输入视频
        "-i", audio_path,  # 输入音频
        "-c:v", "copy",  # 复制视频流
        "-c:a", "aac",  # 编码音频为AAC
        "-strict", "-2",  # 启用实验性编码器
        "-b:a", "192k",  # 音频比特率
        "-map", "0:v",  # 选择第一个输入的视频流
        "-map", "1:a",  # 选择第二个输入的音频流
        "-shortest",  # 以最短流结束
        "-y",  # 覆盖输出
        output_video_path
    ]

    logger.info(f"合成视频命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"视频合成失败: {result.stderr}")
        return False

    logger.info(f"视频合成成功! 输出: {output_video_path}")
    return True


def enhance_video_audio(video_path, output_video_path, output_format="wav"):
    """
    增强视频中的音频并重新合成视频

    参数:
    video_path (str): 输入视频文件路径
    output_video_path (str): 输出视频文件路径
    output_format (str): 增强音频的中间格式 (wav, flac, ogg)

    返回:
    bool: 处理是否成功
    """
    # 服务端点
    url = "http://localhost:9092/enhance"

    # 确保服务正在运行
    try:
        requests.get("http://localhost:9092", timeout=5)
    except requests.exceptions.ConnectionError:
        logger.error("音频增强服务未启动！请先运行语音增强微服务")
        return False

    # 创建临时工作目录
    work_dir = tempfile.mkdtemp()
    logger.info(f"创建临时工作目录: {work_dir}")

    audio_temp_dir = None
    try:
        # 1. 从视频中提取音频
        logger.info(f"处理视频文件: {video_path}")
        audio_path, audio_temp_dir = extract_audio_from_video(video_path)
        if not audio_path:
            return False

        # 2. 发送音频到增强服务
        logger.info(f"发送音频到增强服务: {audio_path}")
        with open(audio_path, "rb") as f:
            files = {'audio_file': (os.path.basename(audio_path), f, "audio/wav")}
            params = {'output_format': output_format}

            start_time = time.time()
            response = requests.post(url, files=files, params=params)
            elapsed = time.time() - start_time

            if response.status_code != 200:
                logger.error(f"音频增强失败: HTTP {response.status_code} - {response.text}")
                return False

            logger.info(f"音频增强成功! 处理时间: {elapsed:.2f}秒")

            # 保存增强后的音频
            enhanced_audio_path = os.path.join(work_dir, f"enhanced_audio.{output_format}")
            with open(enhanced_audio_path, "wb") as f:
                f.write(response.content)
            logger.info(f"增强音频保存到: {enhanced_audio_path}")

        # 3. 合并增强后的音频和原始视频
        logger.info(f"合并增强音频与原始视频")

        # 调用抽象后的合成函数
        if not combine_audio_video(
                video_path=video_path,
                audio_path=enhanced_audio_path,
                output_video_path=output_video_path
        ):
            return False

        return True

    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return False
    finally:
        # 清理临时目录
        if audio_temp_dir:
            shutil.rmtree(audio_temp_dir, ignore_errors=True)
            logger.info(f"清理音频临时目录: {audio_temp_dir}")

        if work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
            logger.info(f"清理工作临时目录: {work_dir}")



def extract_subtitle(
        file_path: str,
        output_path: str
) -> Optional[bool]:
    """
    测试字幕提取服务

    参数:
    file_path (str): 本地音视频文件路径
    output_path (str): 输出SRT文件路径

    返回:
    bool: 处理是否成功
    """
    # 服务端点
    url = "http://localhost:9091/extract"

    # 确保服务正在运行
    try:
        health_res = requests.get("http://localhost:9091/health")
        if health_res.status_code != 200:
            logger.error(f"服务健康检查失败: HTTP {health_res.status_code}")
            return False
        logger.info("服务健康检查成功")
    except requests.exceptions.ConnectionError:
        logger.error("服务未启动！请先运行FastAPI服务")
        return False

    return_type = "text"
    try:
        # 准备文件上传
        filename = os.path.basename(file_path)
        files = {'audio_file': (filename, open(file_path, 'rb'))}

        # 请求参数
        params = {
            'return_type': return_type,
            'output_filename': os.path.basename(output_path) if output_path else None
        }

        logger.info(f"上传文件: {filename} (大小: {os.path.getsize(file_path)} 字节)")
        logger.info(f"请求参数: return_type={return_type}, output_filename={params['output_filename']}")

        # 发送请求
        start_time = time.time()
        response = requests.post(url, files=files, params=params)
        elapsed = time.time() - start_time

        # 处理响应
        if response.status_code != 200:
            logger.error(f"请求失败: HTTP {response.status_code} - {response.text}")
            return False

        logger.info(f"请求成功! 耗时: {elapsed:.2f}秒")

        # 文本响应
        result = response.json()
        logger.info(f"返回文本内容: {len(result['content'])} 字符")
        logger.debug(f"前100个字符: {result['content'][:100]}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result["content"])
        logger.info(f"字幕保存到: {output_path}")

        return True

    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        return False
    finally:
        # 确保文件被关闭
        if 'files' in locals():
            files['audio_file'][1].close()



def vocal_remove(video_path, output_audio_path, output_format="wav"):
    """
    去除视频中的人声并保存伴奏音频

    参数:
        video_path (str): 输入视频文件路径
        output_audio_path (str): 输出音频文件路径
        output_format (str): 输出音频格式 (wav, flac, ogg) - 默认wav

    返回:
        bool: 处理是否成功
    """
    # 伴奏提取微服务端点
    url = "http://localhost:9093/remove"

    # 确保伴奏提取服务正在运行
    try:
        # 验证服务是否可用
        health_check = requests.get("http://localhost:9093", timeout=5)
        if health_check.status_code != 200:
            logger.warning(f"伴奏提取服务响应异常: HTTP {health_check.status_code}")
    except requests.exceptions.ConnectionError:
        logger.error("伴奏提取服务未启动！请先运行伴奏提取微服务(端口9093)")
        return False
    except Exception as e:
        logger.error(f"服务检查失败: {str(e)}")
        return False

    audio_temp_dir = None
    try:
        # 1. 从视频中提取音频
        logger.info(f"提取视频音频: {video_path}")
        audio_path, audio_temp_dir = extract_audio_from_video(
            video_path,
            output_audio_format="wav"  # 提取时固定使用wav格式
        )
        if not audio_path or not os.path.exists(audio_path):
            logger.error("音频提取失败或提取的文件不存在")
            return False
        logger.info(f"成功提取音频: {audio_path}")

        # 2. 发送音频到伴奏提取服务
        logger.info(f"去除人声处理中...")
        with open(audio_path, "rb") as f:
            filename = os.path.basename(audio_path)
            files = {'audio_file': (filename, f, "audio/wav")}
            params = {'output_format': output_format}

            start_time = time.time()
            response = requests.post(url, files=files, params=params)
            elapsed = time.time() - start_time

            if response.status_code != 200:
                error_msg = response.text[:500] + "..." if len(response.text) > 500 else response.text
                logger.error(f"伴奏提取失败: HTTP {response.status_code} - {error_msg}")
                return False

            logger.info(f"伴奏提取成功! 处理时间: {elapsed:.2f}秒")

        # 3. 保存提取的伴奏音频
        logger.info(f"保存伴奏音频: {output_audio_path}")
        os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)
        with open(output_audio_path, "wb") as f:
            f.write(response.content)

        # 验证输出文件
        if not os.path.exists(output_audio_path) or os.path.getsize(output_audio_path) < 1024:
            logger.error(f"伴奏音频保存失败或文件过小: {output_audio_path}")
            return False

        logger.info(f"伴奏音频保存成功! 大小: {os.path.getsize(output_audio_path) / 1024:.2f} KB")
        return True

    except Exception as e:
        logger.error(f"人声去除失败: {str(e)}", exc_info=True)
        return False
    finally:
        # 清理临时目录
        if audio_temp_dir and os.path.exists(audio_temp_dir):
            try:
                shutil.rmtree(audio_temp_dir)
                logger.debug(f"清理音频临时目录: {audio_temp_dir}")
            except Exception as e:
                logger.warning(f"临时目录清理失败: {str(e)}")

if __name__ == "__main__":

    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("函数测试")

    # =====================================   音频增强   ===================================== #
    # 输入输出配置
    input_video = "./media_files/test_video.mp4"
    output_video = "./media_files/test_video_enhanced.mp4"

    logger.info(f"\n### 测试:  {input_video} -> {output_video}")
    success = enhance_video_audio(input_video, output_video)
    if success:
        logger.info(f"视频处理成功: {input_video} -> {output_video}")

    logger.info("=== 音频增强测试完成 ===")
    # =====================================   音频增强   ===================================== #

    # =====================================   字幕提取   ===================================== #
    # 示例测试配置
    test_file = "./media_files/test_video.mp4"  # 替换为你的测试文件
    output_srt = "./media_files/extracted_subtitles.srt"  # 输出的SRT文件路径

    logger.info("=== 测试开始 ===")
    logger.info(f"测试文件: {test_file}")
    logger.info(f"输出路径: {output_srt}")

    # 运行测试 - 文本返回模式
    logger.info("\n测试文本返回模式:")
    success = extract_subtitle(test_file, output_srt)
    if success:
        logger.info(f"字母提取成功: {test_file} -> {output_srt}")

    logger.info("=== 字幕提取测试完成 ===")
    # =====================================   字幕提取   ===================================== #

    # =====================================   人声去除   ===================================== #
    # 输入输出配置
    input_video = "./media_files/test_song.mp4"
    output_audio = "./media_files/vocal_removed.wav"

    logger.info(f"\n### 测试:  {input_video} -> {output_audio}")
    success = vocal_remove(input_video, output_audio)
    if success:
        logger.info(f"人声去除处理成功: {input_video} -> {output_audio}")
    # =====================================   人声去除   ===================================== #

    logger.info("=== 测试完成 ===")
