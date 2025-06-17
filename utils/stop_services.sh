#!/bin/bash

# 确保脚本以正确方式运行
set -euo pipefail

# PID文件路径
PID_FILE="services.pid"

# 检查PID文件是否存在
if [[ ! -f "$PID_FILE" ]]; then
    echo "错误: 无法找到PID文件 $PID_FILE"
    echo "可能服务未启动，或已停止"
    exit 1
fi

echo "正在停止微服务集群..."
echo ""

# 从PID文件中读取并终止进程
while IFS='=' read -r key value; do
    # 忽略空行和注释
    [[ -z "$key" ]] && continue

    # 终止进程
    if kill -0 "$value" 2>/dev/null; then
        echo "正在停止 $key (PID: $value)..."
        kill "$value"
        # 等待进程结束最多5秒
        timeout 5 tail --pid="$value" -f /dev/null
        # 检查进程是否仍在运行
        if kill -0 "$value" 2>/dev/null; then
            echo "强制终止 $key (PID: $value)..."
            kill -9 "$value"
        fi
    else
        echo "进程 $key (PID: $value) 未运行"
    fi
done < "$PID_FILE"

# 删除PID文件
rm -f "$PID_FILE"

echo ""
echo "所有服务已停止!"