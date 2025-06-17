import requests
import os
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subtitles-test")


def subtitle_extraction(
        file_path: str,
        output_path: str = None
):
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
            return None
        logger.info("服务健康检查成功")
    except requests.exceptions.ConnectionError:
        logger.error("服务未启动！请先运行FastAPI服务")
        return None

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
            return None

        logger.info(f"请求成功! 耗时: {elapsed:.2f}秒")

        if return_type == "text":
            # 文本响应
            result = response.json()
            logger.info(f"返回文本内容: {len(result['content'])} 字符")
            logger.debug(f"前100个字符: {result['content'][:100]}")

            # 保存到文件（如果需要）
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result["content"])
                logger.info(f"字幕保存到: {output_path}")
            return result["content"]
        else:
            # 文件响应
            srt_filename = response.headers['Content-Disposition'].split("filename=")[1].strip('"')
            logger.info(f"返回文件: {srt_filename} (大小: {len(response.content)} 字节)")

            # 保存文件
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"字幕保存到: {output_path}")
            else:
                # 生成默认输出路径
                output_path = os.path.splitext(file_path)[0] + "_subtitles.srt"
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"字幕保存到: {output_path}")

            return response.content

    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        return None
    finally:
        # 确保文件被关闭
        if 'files' in locals():
            files['audio_file'][1].close()


if __name__ == "__main__":
    # 示例测试配置
    test_file = "../media_files/test_video.mp4"  # 替换为你的测试文件
    output_srt = "./extracted_subtitles.srt"  # 输出的SRT文件路径

    logger.info("=== 测试开始 ===")
    logger.info(f"测试文件: {test_file}")
    logger.info(f"输出路径: {output_srt}")

    # 运行测试 - 文本返回模式
    logger.info("\n测试文本返回模式:")
    text_result = subtitle_extraction(test_file, output_srt)

    if text_result:
        logger.info("\n提取的部分字幕内容:")
        # 打印前5行
        lines = text_result.splitlines()
        for i, line in enumerate(lines[:min(10, len(lines))]):
            logger.info(f"{i + 1}: {line}")

    logger.info("=== 测试完成 ===")