#!/bin/bash
# 脚本位置: scripts/pack_latest.sh
# 用法: ./scripts/pack_latest.sh N
# 功能: 将 analyses 下最新修改的 N 个子目录及其直接文件打包为 analyses/analyses.zip
#       压缩包内直接以子目录为根，不含 analyses/ 前缀

set -euo pipefail

# --- 参数检查 ---
if [ $# -eq 0 ]; then
    echo "用法: $0 N"
    echo "示例: $0 5   # 打包 analyses 下最新修改的 5 个子目录"
    exit 1
fi

n="$1"
if ! [[ "$n" =~ ^[0-9]+$ ]] || [ "$n" -eq 0 ]; then
    echo "错误: N 必须为正整数"
    exit 1
fi

# --- 目录定位 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"      # 项目根目录
ANALYSES_DIR="$PROJECT_DIR/analyses"

if [ ! -d "$ANALYSES_DIR" ]; then
    echo "错误: 找不到 analyses 目录: $ANALYSES_DIR"
    exit 1
fi

cd "$ANALYSES_DIR"   # 进入 analyses 目录，后续所有操作均基于此

# --- 选出最新的 N 个子目录（相对名称，安全处理特殊字符） ---
selected_dirs=()
while IFS= read -r -d '' dir; do
    selected_dirs+=("$dir")
done < <(
    find . -maxdepth 1 -mindepth 1 -type d \
        -printf '%T@ %P\0' |              # 输出：时间戳 相对目录名\0
    sort -rnz |                             # 按时间降序
    head -z -n "$n" |                       # 取前 N 个
    sed -z 's/^[^ ]* //'                    # 去掉时间戳，只留目录名
)

if [ ${#selected_dirs[@]} -eq 0 ]; then
    echo "analyses 下没有子目录，退出。"
    exit 1
fi

echo "已选择以下最新目录:"
printf '  %s\n' "${selected_dirs[@]}"

# --- 收集所有深度 2 的直接文件（相对路径） ---
file_list=()
for dir in "${selected_dirs[@]}"; do
    while IFS= read -r -d '' file; do
        file_list+=("$file")    # 此时 file 是 ./子目录/文件名 或 子目录/文件名
    done < <(find "$dir" -maxdepth 1 -type f -print0 2>/dev/null || true)
done

if [ ${#file_list[@]} -eq 0 ]; then
    echo "选中的目录中没有直接文件，退出。"
    exit 1
fi

# --- 打包到 analyses 目录下 ---
zip_file="analyses.zip"          # 相对 ANALYSES_DIR 的路径
rm -f "$zip_file"
zip -q "$zip_file" "${file_list[@]}"
echo "完成: 已将 ${#file_list[@]} 个文件打包至 $ANALYSES_DIR/$zip_file"
