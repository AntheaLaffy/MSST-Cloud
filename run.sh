#!/bin/bash

# =================================================================
# Music Source Separation - TUI Dashboard (v4 环境增强版)
# =================================================================

SETTINGS_FILE=".mss_dashboard_settings"
PRESETS_FILE=".mss_presets"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m'

MODELS=("apollo" "bandit" "bandit_v2" "bs_roformer" "htdemucs" "mdx23c" "mel_band_roformer" "scnet" "scnet_unofficial" "segm_models" "swin_upernet" "torchseg")

# =================================================================
# 1. 配置加载与 Python 环境检测
# =================================================================

load_settings() {
    if [ -f "$SETTINGS_FILE" ]; then
        source "$SETTINGS_FILE"
    else
        # 默认值
        BASE_CONFIG_DIR="./configs"
        BASE_CKPT_DIR="./results"
        BASE_INPUT_DIR="./input"
        BASE_OUTPUT_DIR="./output"
        CURRENT_MODEL="bs_roformer"
        CURRENT_CONFIG=""
        CURRENT_CKPT=""
        CURRENT_INPUT="./input"
        CURRENT_OUTPUT="./output"
        EXTRACT_INST="false"
        # 默认使用系统路径下的 python
        PYTHON_PATH=$(command -v python3 || command -v python)
    fi
}

save_settings() {
    cat > "$SETTINGS_FILE" <<EOF
BASE_CONFIG_DIR="$BASE_CONFIG_DIR"
BASE_CKPT_DIR="$BASE_CKPT_DIR"
BASE_INPUT_DIR="$BASE_INPUT_DIR"
BASE_OUTPUT_DIR="$BASE_OUTPUT_DIR"
CURRENT_MODEL="$CURRENT_MODEL"
CURRENT_CONFIG="$CURRENT_CONFIG"
CURRENT_CKPT="$CURRENT_CKPT"
CURRENT_INPUT="$CURRENT_INPUT"
CURRENT_OUTPUT="$CURRENT_OUTPUT"
EXTRACT_INST="$EXTRACT_INST"
PYTHON_PATH="$PYTHON_PATH"
EOF
}

# 获取当前 Python 版本信息
get_python_info() {
    if [[ -x "$PYTHON_PATH" ]] || command -v "$PYTHON_PATH" &>/dev/null; then
        version=$("$PYTHON_PATH" --version 2>&1)
        echo -e "${GREEN}$version${NC} ($PYTHON_PATH)"
    else
        echo -e "${RED}无效的 Python 路径!${NC}"
    fi
}

# =================================================================
# 2. 交互组件
# =================================================================

# 修改 Python 解释器路径
change_python_path() {
    echo -e "\n${YELLOW}--- 配置 Python 环境路径 ---${NC}"
    echo "如果是虚拟环境，请输入其 bin/Scripts 目录下的 python 完整路径。"
    echo -e "当前: ${CYAN}$PYTHON_PATH${NC}"
    read -e -p "输入新路径 (回车取消): " new_py
    if [ -z "$new_py" ]; then return; fi
    
    if [[ -x "$new_py" ]] || command -v "$new_py" &>/dev/null; then
        PYTHON_PATH="$new_py"
        save_settings
        echo -e "${GREEN}Python 环境已切换。${NC}"
    else
        echo -e "${RED}路径无效或无执行权限，未更该。${NC}"
    fi
    sleep 1
}

# 浏览并选择文件 (针对 Config/Checkpoint)
browse_and_select() {
    local base_dir_var=$1
    local base_dir="${!1}"
    local pattern=$2
    local title=$3
    local target_var=$4

    while true; do
        clear
        echo -e "${YELLOW}--- 浏览: $title ---${NC}"
        echo -e "当前目录: ${BLUE}$base_dir${NC} (按 'd' 修改目录)"
        echo -e "------------------------------------------------"
        
        shopt -s nullglob
        files=("$base_dir"/$pattern)
        shopt -u nullglob

        if [ ! -d "$base_dir" ]; then
            echo -e "${RED}目录不存在!${NC}"
        elif [ ${#files[@]} -eq 0 ]; then
            echo -e "${RED}未找到 $pattern 文件。${NC}"
        else
            local i=1
            for f in "${files[@]}"; do
                echo -e "${GREEN}[$i]${NC} $(basename "$f")"
                ((i++))
            done
        fi
        
        echo -e "------------------------------------------------"
        echo -e "[d] 修改浏览目录  [x] 返回"
        read -p "选择编号: " choice

        case $choice in
            [0-9]*)
                if [ "$choice" -ge 1 ] && [ "$choice" -le "${#files[@]}" ]; then
                    eval $target_var="\"${files[$((choice-1))]}\""
                    return 0
                fi ;;
            d)
                read -e -p "输入新目录: " -i "$base_dir" new_d
                eval $base_dir_var="\"$new_d\""
                base_dir="$new_d"
                save_settings ;;
            x) return 0 ;;
        esac
    done
}

# =================================================================
# 3. 主循环
# =================================================================

load_settings

while true; do
    clear
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${WHITE}Music Source Separation - TUI Dashboard v4${NC}"
    echo -e "${BLUE}============================================================${NC}"
    
    # 0. 环境显示
    echo -ne " 0) ${YELLOW}Python Env:${NC}  "
    get_python_info

    echo -e "\n${YELLOW}▼ Inference Configuration${NC}"
    
    # 1. Model Type
    echo -e " 1) Model Type:     ${CYAN}$CURRENT_MODEL${NC}"
    
    # 2. Config File
    c_disp=$(basename "$CURRENT_CONFIG")
    [ -z "$CURRENT_CONFIG" ] && c_disp="${RED}[未选择]${NC}"
    echo -e " 2) Config File:    ${WHITE}$c_disp${NC}"

    # 3. Checkpoint
    k_disp=$(basename "$CURRENT_CKPT")
    [ -z "$CURRENT_CKPT" ] && k_disp="${RED}[未选择]${NC}"
    echo -e " 3) Checkpoint:     ${WHITE}$k_disp${NC}"

    # 4. Input Folder
    echo -e " 4) Input Folder:   ${GRAY}$CURRENT_INPUT${NC}"

    # 5. Output Folder
    echo -e " 5) Output Folder:  ${GRAY}$CURRENT_OUTPUT${NC}"

    # 6. Extract Instrumental
    inst_mark="[ ]"
    [[ "$EXTRACT_INST" == "true" ]] && inst_mark="${GREEN}[x]${NC}"
    echo -e " 6) Extract Inst:   $inst_mark"

    echo -e "${BLUE}------------------------------------------------------------${NC}"
    echo -e " [R] ${GREEN}RUN INFERENCE${NC}    [P] Presets    [Q] Quit"
    echo -e "${BLUE}------------------------------------------------------------${NC}"
    
    read -p "选择项目 (0-6) 或 操作: " main_op

    case $main_op in
        0) change_python_path ;;
        1) # 模型选择逻辑
           echo -e "\n选择模型编号:"
           for i in "${!MODELS[@]}"; do echo " [$((i+1))] ${MODELS[$i]}"; done
           read -p ">> " m_idx
           [[ "$m_idx" =~ ^[0-9]+$ ]] && CURRENT_MODEL="${MODELS[$((m_idx-1))]}" ;;
        2) browse_and_select "BASE_CONFIG_DIR" "*.yaml" "Configs" "CURRENT_CONFIG" ;;
        3) browse_and_select "BASE_CKPT_DIR" "*" "Checkpoints" "CURRENT_CKPT" ;;
        4) read -e -p "输入 Input 文件夹: " -i "$CURRENT_INPUT" CURRENT_INPUT ;;
        5) read -e -p "输入 Output 文件夹: " -i "$CURRENT_OUTPUT" CURRENT_OUTPUT ;;
        6) [[ "$EXTRACT_INST" == "true" ]] && EXTRACT_INST="false" || EXTRACT_INST="true" ;;
        r|R)
            if [[ ! -f "$CURRENT_CONFIG" ]]; then
                echo -e "${RED}错误: Config 文件无效!${NC}"; sleep 1; continue
            fi
            save_settings
            echo -e "\n${BLUE}执行指令中...${NC}"
            CMD=("$PYTHON_PATH" "inference.py" "--model_type" "$CURRENT_MODEL" "--config_path" "$CURRENT_CONFIG" "--input_folder" "$CURRENT_INPUT" "--store_dir" "$CURRENT_OUTPUT")
            [[ -n "$CURRENT_CKPT" ]] && CMD+=("--start_check_point" "$CURRENT_CKPT")
            [[ "$EXTRACT_INST" == "true" ]] && CMD+=("--extract_instrumental")
            
            "${CMD[@]}"
            echo -e "\n${GREEN}任务完成。按回车返回。${NC}"; read ;;
        q|Q) exit 0 ;;
    esac
    save_settings
done