#!/bin/bash

# 确保脚本以正确方式运行
set -euo pipefail

# 定义日志目录
LOGDIR="logs"
mkdir -p "$LOGDIR"

# 定义输出文件用于存储PID
PID_FILE="services.pid"

echo "正在启动微服务集群..."

# 启动第一个服务 - 语音增强服务 (9092端口)
echo "启动语音增强服务 (端口: 9092)..."
/home/chenyx/miniconda3/bin/conda run -n clearvoice --no-capture-output python /sdd/chenyx/Python_Projects/Audio-Processes/voice_enhancement/enhance_server.py > "$LOGDIR/enhance_service.log" 2>&1 &
ENHANCE_PID=$!
echo "语音增强服务 PID: $ENHANCE_PID"

# 启动第二个服务 - 字幕提取服务 (9091端口)
echo "启动字幕提取服务 (端口: 9091)..."
/home/chenyx/miniconda3/bin/conda run -n whisperx --no-capture-output python /sdd/chenyx/Python_Projects/Audio-Processes/subtitle_extract/extract_server.py > "$LOGDIR/subtitle_service.log" 2>&1 &
SUBTITLE_PID=$!
echo "字幕提取服务 PID: $SUBTITLE_PID"

# 启动第三个服务 - 伴奏提取服务 (9093端口)
echo "启动伴奏提取服务 (端口: 9093)..."
/home/chenyx/miniconda3/bin/conda run -n spleeter --no-capture-output python /sdd/chenyx/Python_Projects/Audio-Processes/vocal_removal/remove_server.py > "$LOGDIR/remove_service.log" 2>&1 &
REMOVE_PID=$!
echo "伴奏提取服务 PID: $REMOVE_PID"

# 将PID保存到文件
{
    echo "ENHANCE_PID=$ENHANCE_PID"
    echo "SUBTITLE_PID=$SUBTITLE_PID"
    echo "REMOVE_PID=$REMOVE_PID"
} > "$PID_FILE"

echo ""
echo "所有服务已启动!"
echo "PID已保存至: $PID_FILE"
echo "日志目录: $LOGDIR"

# 打印运行状态
echo ""
echo "当前运行状态:"
ps -p $ENHANCE_PID,$SUBTITLE_PID,$REMOVE_PID -o pid,command

echo ""
echo "要停止服务，请运行: ./stop_services.sh"