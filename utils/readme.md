# 本文件夹 `utils/` 用于 `mp4` 后台文件处理
  mp4处理函数包括：
  1. 人声增强 (Voice Enhancement)
  2. 伴奏提取 (Vocal Removal)
  3. 字幕提取 (Subtitle Extraction)

## `client.py` 是 mp4 处理函数的函数库
  文件中的三个函数分别访问不同的微服务对 `mp4` 进行相应的处理，得到对应的输出结果。

## `seam.py` 是使用接缝进行开发可以调用的函数库
  因为不同的 `mp4` 处理函数需要不同的 `python` 环境运行，所以使用微服务实现这些功能。当微服务未启动时，可以用`seam.py`中的函数测试前端代码。

## `start_services.sh` 用于在提供微服务的服务器上启动三个 mp4 处理服务

## `stop_services.sh` 用于终止这些服务
