import curses
import os
import json
import shlex
import subprocess
import threading
import time
import sys
import signal
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ============================================================
# 基础配置
# ============================================================

CACHE_FILE = "mvsep_cache.json"

# ============================================================
# 状态管理类
# ============================================================

class TUIState:
    """统一管理TUI状态，解决索引不一致问题"""
    
    def __init__(self):
        # VIEW模式状态
        self.view_mode = True
        self.current_visible_index = 0  # 可见字段列表中的索引
        self.selected_process_id = None
        
        # EDIT模式状态
        self.edit_mode = False
        self.editing_field_id = None  # EDIT模式下使用field_id，而不是索引
        self.edit_buffer = ""
        self.edit_cursor_pos = 0
        self.preview_items = []
        self.preview_selected_index = -1
        
        # 命令模式状态
        self.command_mode = False
        self.command_buffer = ""
        
        # 帮助模式状态
        self.help_mode = False
        self.previous_mode = "VIEW"
        
        # 进程选择模式状态
        self.process_selection_mode = False
    
    def ensure_valid_index(self, visible_fields):
        """确保当前索引在有效范围内"""
        if not visible_fields:
            self.current_visible_index = 0
            return
        
        if self.current_visible_index < 0:
            self.current_visible_index = 0
        elif self.current_visible_index >= len(visible_fields):
            self.current_visible_index = len(visible_fields) - 1
    
    def ensure_valid_edit_cursor(self):
        """确保编辑光标在有效位置"""
        if self.edit_buffer is None:
            self.edit_buffer = ""
        
        buffer_len = len(str(self.edit_buffer))
        if self.edit_cursor_pos < 0:
            self.edit_cursor_pos = 0
        elif self.edit_cursor_pos > buffer_len:
            self.edit_cursor_pos = buffer_len
    
    def enter_edit_mode(self, field_id, initial_value=""):
        """进入编辑模式"""
        self.view_mode = False
        self.edit_mode = True
        self.editing_field_id = field_id
        self.edit_buffer = str(initial_value)
        self.edit_cursor_pos = len(self.edit_buffer)
        self.preview_items = []
        self.preview_selected_index = -1
    
    def exit_edit_mode(self):
        """退出编辑模式"""
        self.edit_mode = False
        self.editing_field_id = None
        self.edit_buffer = ""
        self.edit_cursor_pos = 0
        self.preview_items = []
        self.preview_selected_index = -1
        self.view_mode = True
        
        # 找到编辑字段在可见列表中的位置，更新current_visible_index
        if self.editing_field_id is not None:
            visible_fields = get_current_fields()
            for i, field in enumerate(visible_fields):
                if field["id"] == self.editing_field_id:
                    self.current_visible_index = i
                    break
    
    def enter_command_mode(self):
        """进入命令模式"""
        self.view_mode = False
        self.command_mode = True
        self.command_buffer = ""
    
    def exit_command_mode(self):
        """退出命令模式"""
        self.command_mode = False
        self.view_mode = True
    
    def toggle_process_selection(self, processes):
        """切换进程选择模式"""
        if processes and not self.process_selection_mode:
            self.process_selection_mode = True
            self.selected_process_id = processes[0]["id"] if processes else None
        else:
            self.process_selection_mode = False
            self.selected_process_id = None
    
    def get_editing_field(self):
        """获取正在编辑的字段"""
        if self.editing_field_id is not None:
            return get_field_by_id(self.editing_field_id)
        return None

# ============================================================
# 全局字段定义库
# ============================================================

# 所有字段的全局定义，每个字段有唯一ID
ALL_FIELDS = {
    # inference界面的字段
    0: {"id": 0, "name": "model_type", "type": "enum",
        "options": [
            "mdx23c", "htdemucs", "segm_models", "mel_band_roformer", 
            "bs_roformer", "torchseg", "swin_upernet", "bandit", "scnet",
            "bandit_v2", "apollo", "bs_mamba2", "conformer", "bs_conformer",
            "scnet_tran", "scnet_masked"
        ],
        "default": "mdx23c", "value": "mdx23c"},
    
    1: {"id": 1, "name": "preset", "type": "path",
        "default": "./preset", "value": "./preset"},
    
    2: {"id": 2, "name": "config_path", "type": "path",
        "default": "configs/config_mdx23c_musdb18.yaml", "value": "configs/config_mdx23c_musdb18.yaml"},
    
    3: {"id": 3, "name": "start_check_point", "type": "path",
        "default": "", "value": ""},
    
    4: {"id": 4, "name": "input_folder", "type": "path",
        "default": "", "value": ""},
    
    5: {"id": 5, "name": "store_dir", "type": "path",
        "default": "separation_results", "value": "separation_results"},
    
    6: {"id": 6, "name": "device_ids", "type": "enum",
        "options": ["0", "1", "0,1", "1,0", "0,1,2,3"],
        "default": "0", "value": "0"},
    
    7: {"id": 7, "name": "extract_instrumental", "type": "bool",
        "default": False, "value": False},
    
    8: {"id": 8, "name": "verbose", "type": "bool",
        "default": False, "value": False},
    
    9: {"id": 9, "name": "float32", "type": "bool",
        "default": False, "value": False},
    
    # train界面的字段
    100: {"id": 100, "name": "model_type", "type": "enum",
          "options": [
              "mdx23c", "htdemucs", "segm_models", "mel_band_roformer", 
              "bs_roformer", "torchseg", "swin_upernet", "bandit", "scnet",
              "bandit_v2", "apollo", "bs_mamba2", "conformer", "bs_conformer",
              "scnet_tran", "scnet_masked"
          ],
          "default": "mdx23c", "value": "mdx23c"},
    
    101: {"id": 101, "name": "config_path", "type": "path",
          "default": "configs/config_mdx23c_musdb18.yaml", "value": "configs/config_mdx23c_musdb18.yaml"},
    
    102: {"id": 102, "name": "start_check_point", "type": "path",
          "default": "", "value": ""},
    
    103: {"id": 103, "name": "results_path", "type": "path",
          "default": "results", "value": "results"},
    
    104: {"id": 104, "name": "data_path", "type": "path",
          "default": "", "value": ""},
    
    105: {"id": 105, "name": "valid_path", "type": "path",
          "default": "", "value": ""},
    
    106: {"id": 106, "name": "num_workers", "type": "num",
          "default": 4, "value": 4},
    
    107: {"id": 107, "name": "device_ids", "type": "enum",
          "options": ["0", "1", "0,1", "1,0", "0,1,2,3"],
          "default": "0", "value": "0"},
}

# ============================================================
# 界面定义与字段绑定（包含可见性）
# ============================================================

SCREENS = {
    "inference": {
        "name": "推理配置",
        # 字段绑定：field_id 和 visible（是否默认显示）
        "field_bindings": [
            {"field_id": 0, "visible": True},   # model_type
            {"field_id": 1, "visible": True},   # preset
            {"field_id": 2, "visible": True},   # config_path
            {"field_id": 3, "visible": True},   # start_check_point
            {"field_id": 4, "visible": True},   # input_folder
            {"field_id": 5, "visible": True},   # store_dir
            {"field_id": 6, "visible": False},  # device_ids (GUI中不显示)
            {"field_id": 7, "visible": True},   # extract_instrumental
            {"field_id": 8, "visible": False},  # verbose (GUI中不显示)
            {"field_id": 9, "visible": False},  # float32 (GUI中不显示)
        ],
        "field_mapping": {
            "model_type": "--model_type",
            "config_path": "--config_path",
            "start_check_point": "--start_check_point",
            "input_folder": "--input_folder",
            "store_dir": "--store_dir",
            "device_ids": "--device_ids",
            "extract_instrumental": "--extract_instrumental",
            "verbose": "--verbose",
            "float32": "--float32",
        }
    },
    "train": {
        "name": "训练配置",
        "field_bindings": [
            {"field_id": 100, "visible": True},  # model_type
            {"field_id": 101, "visible": True},  # config_path
            {"field_id": 102, "visible": True},  # start_check_point
            {"field_id": 103, "visible": True},  # results_path
            {"field_id": 104, "visible": True},  # data_path
            {"field_id": 105, "visible": True},  # valid_path
            {"field_id": 106, "visible": True},  # num_workers
            {"field_id": 107, "visible": True},  # device_ids
        ],
        "field_mapping": {
            "model_type": "--model_type",
            "config_path": "--config_path",
            "start_check_point": "--start_check_point",
            "results_path": "--results_path",
            "data_path": "--data_path",
            "valid_path": "--valid_path",
            "num_workers": "--num_workers",
            "device_ids": "--device_ids",
        }
    }
}

# 全局变量
CURRENT_SCREEN = "inference"
CURRENT_LANG = "zh"
DEBUG_MODE = False

# ============================================================
# 多语言 - 新增进程管理相关文本
# ============================================================

LANGS = {
    "zh": {
        "header": "=== MVSEP TUI ===",
        "fields": "字段:",
        "editing": "编辑:",
        "preview": "预览:",
        "processes": "进程管理:",
        "help_bar":
            ":q 退出 | Enter 编辑/确认 | Esc 回退 | Tab 补全 | Ctrl+F 预览 | :run运行推理 | :help 帮助",
        "cmd_hint": "命令模式",
        "help_title": "帮助",
        "cmd_prompt": "命令栏",
        "process_id": "ID",
        "process_pid": "PID",
        "process_cmd": "命令",
        "process_status": "状态",
        "process_start": "启动时间",
        "process_no": "无运行进程",
        "process_running": "运行中",
        "process_completed": "已完成",
        "process_killed": "已终止",
        "process_failed": "失败",
        "kill_success": "已终止进程",
        "kill_all_success": "已终止所有进程",
        "kill_error": "无法终止进程",
        "no_process": "无运行进程",
        "process_created": "进程已创建",
        "process_error": "进程启动失败",
        "switch_to_train": "按F2切换到训练界面",
        "switch_to_inference": "按F2切换到推理界面",
        "screen_inference": "推理配置",
        "screen_train": "训练配置",
    },
    "en": {
        "header": "=== MVSEP TUI ===",
        "fields": "Fields:",
        "editing": "Editing:",
        "preview": "Preview:",
        "processes": "Process Management:",
        "help_bar":
            ":q exit | Enter Edit | Tab Complete | Ctrl+F Preview | :run inference | :help useful_information",
        "cmd_hint": "Command Mode",
        "help_title": "Help",
        "cmd_prompt": "Command Bar",
        "process_id": "ID",
        "process_pid": "PID",
        "process_cmd": "Command",
        "process_status": "Status",
        "process_start": "Start Time",
        "process_no": "No running processes",
        "process_running": "Running",
        "process_completed": "Completed",
        "process_killed": "Killed",
        "process_failed": "Failed",
        "kill_success": "Process terminated",
        "kill_all_success": "All processes terminated",
        "kill_error": "Failed to terminate process",
        "no_process": "No running processes",
        "process_created": "Process created",
        "process_error": "Process start failed",
        "switch_to_train": "Press F2 to switch to training screen",
        "switch_to_inference": "Press F2 to switch to inference screen",
        "screen_inference": "Inference Config",
        "screen_train": "Training Config",
    }
}

# ============================================================
# 统一的字段访问函数
# ============================================================

def get_field_by_id(field_id):
    """安全地通过ID获取字段"""
    return ALL_FIELDS.get(field_id)

def get_visible_fields():
    """获取当前界面可见字段（考虑调试模式）"""
    screen_info = SCREENS[CURRENT_SCREEN]
    visible_fields = []
    
    for binding in screen_info["field_bindings"]:
        if binding["visible"] or DEBUG_MODE:
            field = get_field_by_id(binding["field_id"])
            if field:
                field_with_visibility = field.copy()
                field_with_visibility["visible"] = binding["visible"]
                visible_fields.append(field_with_visibility)
    
    return visible_fields

def get_current_field_for_view(state):
    """为VIEW模式获取当前选中的字段"""
    visible_fields = get_visible_fields()
    if 0 <= state.current_visible_index < len(visible_fields):
        return visible_fields[state.current_visible_index]
    return None

def get_current_field_id_for_view(state):
    """为VIEW模式获取当前选中的字段ID"""
    field = get_current_field_for_view(state)
    return field["id"] if field else None

# 布尔值预览选项
BOOL_PREVIEW = ["True", "False"]

def get_all_current_fields():
    """获取当前界面的所有字段（无论可见性，用于编辑和命令构建）"""
    screen_info = SCREENS[CURRENT_SCREEN]
    field_bindings = screen_info["field_bindings"]
    
    fields = []
    for binding in field_bindings:
        field = ALL_FIELDS.get(binding["field_id"])
        if field:
            field_with_visibility = field.copy()
            field_with_visibility["visible"] = binding["visible"]
            fields.append(field_with_visibility)
    
    return fields

def get_field_by_name(field_name):
    """根据名称获取字段（在当前界面所有字段中）"""
    for field in get_all_current_fields():
        if field["name"] == field_name:
            return field
    return None

def get_current_fields():
    """获取当前界面的字段列表（根据可见性和调试模式）"""
    screen_info = SCREENS[CURRENT_SCREEN]
    field_bindings = screen_info["field_bindings"]
    
    fields = []
    for binding in field_bindings:
        field = ALL_FIELDS.get(binding["field_id"])
        if field:
            # 如果字段存在，添加可见性信息
            field_with_visibility = field.copy()
            field_with_visibility["visible"] = binding["visible"]
            fields.append(field_with_visibility)
    
    # 在非调试模式下，只显示visible为True的字段
    if not DEBUG_MODE:
        fields = [f for f in fields if f["visible"]]
    
    return fields

# ============================================================
# 安全的路径预览系统
# ============================================================

def safe_path_preview(buf, limit=64):
    """安全的路径预览，处理各种边界情况"""
    if buf is None:
        return []
    
    buf_str = str(buf).strip()
    if not buf_str:
        return []
    
    # 检查路径是否存在
    if os.path.isdir(buf_str) or os.path.isfile(buf_str):
        base = buf_str
        name = ""
    else:
        base, name = os.path.split(buf_str)
        if not base:
            base = "."
    
    # 确保base是字符串
    base = str(base)
    
    if not os.path.exists(base):
        return []
    
    try:
        items = os.listdir(base)
    except (OSError, PermissionError):
        return []
    
    res = []
    for item in items:
        if not name or name.lower() in item.lower():
            full_path = os.path.join(base, item)
            try:
                if os.path.isdir(full_path):
                    res.append(full_path + os.path.sep)
                else:
                    res.append(full_path)
            except (OSError, PermissionError):
                continue
    
    return sorted(res)[:limit]

def safe_build_preview(field, edit_buf):
    """安全的预览构建，处理各种字段类型"""
    if not field:
        return []
    
    if field["type"] == "path":
        return safe_path_preview(edit_buf)
    elif field["type"] == "enum":
        options = field.get("options", [])
        if not options:
            return []
        return [opt for opt in options if edit_buf.lower() in opt.lower()]
    elif field["type"] == "bool":
        return BOOL_PREVIEW
    elif field["type"] == "num":
        common_nums = ["1", "2", "4", "8", "16", "32", "64"]
        return [n for n in common_nums if edit_buf in n]
    return []

# ============================================================
# 编辑系统重构
# ============================================================

class EditSystem:
    """专门的编辑系统，处理所有编辑逻辑"""
    
    @staticmethod
    def handle_backspace(state):
        """处理退格键"""
        if state.edit_buffer and state.edit_cursor_pos > 0:
            # 删除光标前一个字符
            state.edit_buffer = (
                state.edit_buffer[:state.edit_cursor_pos - 1] + 
                state.edit_buffer[state.edit_cursor_pos:]
            )
            state.edit_cursor_pos -= 1
            return True
        return False
    
    @staticmethod
    def handle_delete(state):
        """处理删除键"""
        if state.edit_buffer and state.edit_cursor_pos < len(state.edit_buffer):
            state.edit_buffer = (
                state.edit_buffer[:state.edit_cursor_pos] + 
                state.edit_buffer[state.edit_cursor_pos + 1:]
            )
            return True
        return False
    
    @staticmethod
    def handle_character_input(state, char):
        """处理字符输入"""
        state.edit_buffer = (
            state.edit_buffer[:state.edit_cursor_pos] + 
            char + 
            state.edit_buffer[state.edit_cursor_pos:]
        )
        state.edit_cursor_pos += 1
    
    @staticmethod
    def handle_tab_completion(state, field):
        """处理Tab补全"""
        if not state.preview_items:
            return False
        
        if state.preview_selected_index >= 0:
            selected_item = state.preview_items[state.preview_selected_index]
        else:
            selected_item = state.preview_items[0]
        
        state.edit_buffer = selected_item
        state.edit_cursor_pos = len(state.edit_buffer)
        return True
    
    @staticmethod
    def handle_enter_confirmation(state):
        """处理Enter确认编辑"""
        field = state.get_editing_field()
        if not field:
            return False
        
        # 根据字段类型转换值
        if field["type"] == "bool":
            if state.edit_buffer.lower() in ["true", "1", "yes", "on"]:
                field["value"] = True
            else:
                field["value"] = False
        elif field["type"] == "num":
            try:
                if "." in state.edit_buffer:
                    field["value"] = float(state.edit_buffer)
                else:
                    field["value"] = int(state.edit_buffer)
            except ValueError:
                field["value"] = state.edit_buffer
        else:
            # path和enum类型保持字符串
            field["value"] = state.edit_buffer
        
        # 保存到缓存
        save_cache()
        return True
    
    @staticmethod
    def update_preview(state, field):
        """安全更新预览"""
        try:
            if field and state.edit_buffer is not None:
                # 确保 edit_buffer 是字符串
                edit_buf_str = str(state.edit_buffer)
                state.preview_items = safe_build_preview(field, edit_buf_str)
                
                # 确保预览选择索引有效
                if state.preview_selected_index >= len(state.preview_items):
                    state.preview_selected_index = max(0, len(state.preview_items) - 1)
            else:
                state.preview_items = []
        except Exception:
            state.preview_items = []
        
        # 确保编辑光标位置有效
        state.ensure_valid_edit_cursor()

# ============================================================
# 进程管理数据结构
# ============================================================

class ProcessManager:
    """管理多个推理进程"""
    
    def __init__(self):
        self.processes = []  # 存储所有进程信息
        self.next_id = 1
        self.lock = threading.Lock()
    
    def add_process(self, pid, cmd, proc_obj=None):
        """添加新进程到管理列表"""
        with self.lock:
            process_info = {
                "id": self.next_id,
                "pid": pid,
                "cmd": cmd,
                "proc_obj": proc_obj,
                "start_time": datetime.now().strftime("%H:%M:%S"),
                "status": "running",
                "return_code": None
            }
            self.processes.append(process_info)
            self.next_id += 1
            return process_info["id"]
    
    def get_process(self, pid_or_id):
        """根据PID或ID获取进程信息"""
        with self.lock:
            for p in self.processes:
                if p["pid"] == pid_or_id or p["id"] == pid_or_id:
                    return p
            return None
    
    def update_status(self, pid, status, return_code=None):
        """更新进程状态"""
        with self.lock:
            for p in self.processes:
                if p["pid"] == pid:
                    p["status"] = status
                    if return_code is not None:
                        p["return_code"] = return_code
                    return True
            return False
    
    def remove_process(self, pid_or_id):
        """移除进程"""
        with self.lock:
            for i, p in enumerate(self.processes):
                if p["pid"] == pid_or_id or p["id"] == pid_or_id:
                    return self.processes.pop(i)
            return None
    
    def kill_process(self, pid_or_id):
        """终止指定进程"""
        process = self.get_process(pid_or_id)
        if process and process["proc_obj"]:
            try:
                if sys.platform.startswith("win"):
                    process["proc_obj"].terminate()
                else:
                    os.kill(process["pid"], signal.SIGTERM)
                self.update_status(process["pid"], "killed")
                return True
            except:
                return False
        return False
    
    def kill_all(self):
        """终止所有进程"""
        with self.lock:
            success_count = 0
            for p in self.processes:
                if p["status"] == "running" and p["proc_obj"]:
                    try:
                        if sys.platform.startswith("win"):
                            p["proc_obj"].terminate()
                        else:
                            os.kill(p["pid"], signal.SIGTERM)
                        p["status"] = "killed"
                        success_count += 1
                    except:
                        pass
            return success_count
    
    def cleanup_finished(self):
        """清理已完成的进程"""
        with self.lock:
            # 保留最近10个已完成进程供查看
            completed = [p for p in self.processes if p["status"] != "running"]
            running = [p for p in self.processes if p["status"] == "running"]
            
            # 如果已完成进程太多，只保留最新的10个
            if len(completed) > 10:
                completed = completed[-10:]
            
            self.processes = running + completed
    
    def get_all_processes(self):
        """获取所有进程信息"""
        with self.lock:
            return self.processes.copy()

# 全局进程管理器
process_manager = ProcessManager()

# ============================================================
# 缓存 / 导入 / 另存 - 支持动态绑定
# ============================================================

def load_cache():
    """加载缓存，支持界面层级存储"""
    if not os.path.exists(CACHE_FILE):
        return
    
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 版本检测：旧版本是扁平结构，新版本有界面层级
        if isinstance(data, dict) and "inference" in data:
            # 新版本：有界面层级
            for screen_name, screen_data in data.items():
                if screen_name in SCREENS:
                    for field_id_str, value in screen_data.items():
                        field_id = int(field_id_str)
                        if field_id in ALL_FIELDS:
                            ALL_FIELDS[field_id]["value"] = value
        else:
            # 旧版本：扁平结构，尝试加载到对应字段
            for field_id_str, value in data.items():
                try:
                    field_id = int(field_id_str)
                    if field_id in ALL_FIELDS:
                        ALL_FIELDS[field_id]["value"] = value
                except ValueError:
                    pass
            
            # 保存为新格式
            save_cache()
            
    except Exception as e:
        print(f"加载缓存失败: {e}")
        # 如果缓存文件损坏，创建新的
        save_cache()


def save_cache():
    """保存缓存，按界面层级存储所有字段"""
    data = {}
    
    for screen_name, screen_info in SCREENS.items():
        screen_data = {}
        for binding in screen_info["field_bindings"]:
            field_id = binding["field_id"]
            field = ALL_FIELDS[field_id]
            if field["value"] not in ("", None):
                screen_data[str(field_id)] = field["value"]
        data[screen_name] = screen_data
    
    with open(CACHE_FILE, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def save_as(path):
    """另存为当前界面的配置（保存所有字段）"""
    screen_info = SCREENS[CURRENT_SCREEN]
    data = {}
    
    for binding in screen_info["field_bindings"]:
        field_id = binding["field_id"]
        field = ALL_FIELDS[field_id]
        if field["value"] not in ("", None):
            data[str(field_id)] = field["value"]
    
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def import_fields(path):
    """导入配置到当前界面（导入到所有字段）"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        screen_info = SCREENS[CURRENT_SCREEN]
        imported = 0
        
        for field_id_str, value in data.items():
            field_id = int(field_id_str)
            # 检查字段是否属于当前界面
            for binding in screen_info["field_bindings"]:
                if binding["field_id"] == field_id:
                    if field_id in ALL_FIELDS:
                        ALL_FIELDS[field_id]["value"] = value
                        imported += 1
                    break
        
        save_cache()  # 更新缓存
        return imported
    except Exception as e:
        print(f"导入失败: {e}")
        return 0

# ============================================================
# 预览系统
# ============================================================

def path_preview(buf, limit=64):
    if not buf:
        return []
    base, name = os.path.split(buf)
    if base == "":
        base = "."
    if not os.path.isdir(base):
        return []
    try:
        items = os.listdir(base)
    except Exception:
        return []

    res = []
    for it in items:
        if name in it:
            full = os.path.join(base, it)
            if os.path.isdir(full):
                full += "/"
            res.append(full)
    return sorted(res)[:limit]


def build_preview(field, edit_buf):
    if field["type"] == "path":
        return safe_path_preview(edit_buf)  # 使用安全版本
    if field["type"] == "enum":
        return [o for o in field["options"] if edit_buf.lower() in o.lower()]
    if field["type"] == "bool":
        return BOOL_PREVIEW
    if field["type"] == "num":
        # 数字类型可以预览一些常用值
        common_nums = ["1", "2", "4", "8", "16", "32", "64"]
        return [n for n in common_nums if edit_buf in n]
    return []


def safe_draw_preview_column_major(stdscr, items, start_y, max_h, col_w, selected):
    """安全的预览绘制函数"""
    if not items:
        return
    
    # 获取当前窗口尺寸
    h, w = stdscr.getmaxyx()
    if start_y >= h:
        return
    
    rows = min(max_h, h - start_y - 1)
    if rows <= 0:
        return
    
    cols = (len(items) + rows - 1) // rows
    idx = 0
    
    for c in range(cols):
        for r in range(rows):
            if idx >= len(items):
                return
            
            y = start_y + r
            x = 2 + c * col_w
            
            # 检查坐标是否在窗口内
            if y < 0 or y >= h or x < 0 or x >= w:
                idx += 1
                continue
            
            # 安全处理文本
            text = str(items[idx]) if items[idx] is not None else ""
            text = text[:max(0, col_w - 4)]
            
            # 构建显示文本
            if idx == selected:
                display_text = "-> " + text
            else:
                display_text = "   " + text
            
            # 确保不会超出窗口右边界
            max_text_len = max(0, w - x)
            display_text = display_text[:max_text_len]
            
            # 安全绘制
            try:
                if idx == selected:
                    stdscr.addstr(y, x, display_text, curses.A_REVERSE)
                else:
                    stdscr.addstr(y, x, display_text)
            except curses.error:
                pass  # 忽略绘制错误
            
            idx += 1


def draw_preview_column_major(stdscr, items, start_y, max_h, col_w, selected):
    # 旧函数保留兼容性，但实际使用安全版本
    safe_draw_preview_column_major(stdscr, items, start_y, max_h, col_w, selected)

# ============================================================
# 进程显示系统
# ============================================================

def safe_draw_fields(stdscr, start_y, fields, current_index, is_view_mode):
    """安全地绘制字段列表"""
    h, w = stdscr.getmaxyx()
    max_fields = min(len(fields), h - start_y - 5)
    
    for i in range(max_fields):
        y = start_y + i
        if y >= h:
            break
        
        field = fields[i]
        mark = ">>" if i == current_index and is_view_mode else "  "
        
        # 安全格式化值
        if field["type"] == "bool":
            val = "True" if field["value"] else "False"
        else:
            val = str(field["value"])
        
        # 截断显示值
        display_val = val[:max(0, w - 40)]
        
        # 构建显示文本
        field_name = field["name"]
        if DEBUG_MODE and not field.get("visible", True):
            field_name = f"{field_name} [隐藏]"
        
        display_text = f"{mark} {field_name}: {display_val}"
        
        # 截断到窗口宽度
        max_len = max(0, w - 2)
        display_text = display_text[:max_len]
        
        # 安全绘制
        try:
            attr = 0
            if i == current_index and is_view_mode:
                attr = curses.A_BOLD
            if DEBUG_MODE and not field.get("visible", True):
                try:
                    attr |= curses.color_pair(3)
                except:
                    pass
            
            stdscr.addstr(y, 2, display_text, attr)
        except curses.error:
            pass


def safe_draw_edit_buffer(stdscr, y, x, edit_buffer, cursor_pos):
    """安全地绘制编辑缓冲区"""
    h, w = stdscr.getmaxyx()
    if y >= h or x >= w:
        return
    
    # 计算最大显示长度
    max_len = max(0, w - x - 2)
    
    # 安全处理编辑缓冲区
    buf_str = str(edit_buffer) if edit_buffer is not None else ""
    
    for i, ch in enumerate(buf_str[:max_len]):
        try:
            attr = curses.A_REVERSE if i == cursor_pos else 0
            stdscr.addstr(y, x + i, ch, attr)
        except curses.error:
            break
    
    # 光标在末尾的情况
    if cursor_pos == len(buf_str) and cursor_pos < max_len:
        try:
            stdscr.addstr(y, x + cursor_pos, " ", curses.A_REVERSE)
        except curses.error:
            pass


def safe_draw_process_list(stdscr, start_y, max_h, max_w, selected_pid=None):
    """安全绘制进程列表"""
    processes = process_manager.get_all_processes()
    lang = LANGS[CURRENT_LANG]
    
    # 获取窗口尺寸
    h, w = stdscr.getmaxyx()
    if start_y >= h:
        return 0
    
    if not processes:
        safe_addstr(stdscr, start_y, 2, lang["process_no"])
        return 0
    
    # 表头
    headers = [
        (lang["process_id"], 6),
        (lang["process_pid"], 8),
        (lang["process_status"], 10),
        (lang["process_start"], 12),
        (lang["process_cmd"], max_w - 40)
    ]
    
    # 安全绘制表头
    x_pos = 2
    for header, width in headers:
        if x_pos >= w:
            break
        safe_addstr(stdscr, start_y, x_pos, header[:width])
        x_pos += width + 2
    
    # 安全绘制进程行
    for i, proc in enumerate(processes):
        y = start_y + 1 + i
        if y >= h:
            break
        
        # 状态颜色
        status = proc["status"]
        attr = 0
        if status == "running":
            attr = curses.A_BOLD
        elif status == "completed":
            attr = curses.A_DIM
        elif status in ["killed", "failed"]:
            attr = curses.A_BLINK
        
        # 如果被选中，反显
        if selected_pid == proc["id"]:
            attr |= curses.A_REVERSE
        
        # 绘制每一列
        x_pos = 2
        
        # ID
        id_str = str(proc["id"])
        safe_addstr(stdscr, y, x_pos, id_str, attr)
        x_pos += 8
        
        # PID
        if x_pos < w:
            pid_str = str(proc["pid"])
            safe_addstr(stdscr, y, x_pos, pid_str, attr)
        x_pos += 10
        
        # 状态
        if x_pos < w:
            status_text = lang.get(f"process_{status}", status)
            safe_addstr(stdscr, y, x_pos, status_text[:10], attr)
        x_pos += 12
        
        # 开始时间
        if x_pos < w:
            time_str = proc["start_time"]
            safe_addstr(stdscr, y, x_pos, time_str[:12], attr)
        x_pos += 14
        
        # 命令（截断）
        if x_pos < w:
            cmd_str = proc["cmd"]
            max_cmd_len = max(0, w - x_pos - 2)
            if len(cmd_str) > max_cmd_len:
                cmd_str = cmd_str[:max_cmd_len-3] + "..."
            safe_addstr(stdscr, y, x_pos, cmd_str, attr)
    
    return len(processes)


def draw_process_list(stdscr, start_y, max_h, max_w, selected_pid=None):
    # 旧函数保留兼容性，但实际使用安全版本
    return safe_draw_process_list(stdscr, start_y, max_h, max_w, selected_pid)

# ============================================================
# Help 内容 - 更新以包含调试模式说明
# ============================================================

HELP_TEXT = [
    ":q                退出程序",
    "Ctrl+C            退出程序（强制）",
    ":run              运行（推理或训练）",
    ":kill <pid/id>    杀死指定进程",
    ":kill all         杀死所有进程",
    ":ps               显示进程列表",
    ":save [file]      另存字段配置",
    ":import <file>    导入字段配置",
    ":language <lang>  切换语言",
    ":help             打开帮助",
    "",
    "ESC               返回上一级（模式 / 界面）",
    "Ctrl+U            清空输入",
    "Ctrl+D            切换调试模式",
    "F2                切换推理/训练界面",
    "",
    "退出方式对比:",
    "  :q        - 优雅退出，终止所有进程",
    "  Ctrl+C    - 强制退出，终止所有进程",
    "",
    "参数传递规则:",
    "  - 空值字段不会传递给命令",
    "  - 布尔值False不会添加参数",
    "  - 数字0是有效值，会正常传递",
    "  - preset字段仅用于界面，不传递给命令",
    "",
    "调试模式（Ctrl+D）:",
    "  - 显示所有字段（包括默认隐藏的字段）",
    "  - 显示命令构建的详细信息",
    "  - 隐藏字段标记为 [隐藏]",
    "  - 可以编辑和修改隐藏字段的值",
    "",
    "隐藏字段说明:",
    "  - 这些字段有默认值，通常不需要修改",
    "  - 高级用户可以在调试模式下调整",
    "  - 修改后会影响命令执行",
]

# ============================================================
# 工具函数
# ============================================================

def visual_width(s: str) -> int:
    """计算字符串的视觉宽度（处理中文字符）"""
    if s is None:
        return 0
    w = 0
    for ch in str(s):
        w += 2 if ord(ch) > 127 else 1
    return w


def trim_to_width(s: str, max_w: int) -> str:
    """根据视觉宽度截断字符串"""
    if s is None:
        return ""
    
    res = ""
    w = 0
    for ch in str(s):
        cw = 2 if ord(ch) > 127 else 1
        if w + cw > max_w:
            break
        res += ch
        w += cw
    return res


def safe_addstr(stdscr, y, x, text, attr=0):
    """安全的addstr函数，自动处理边界"""
    try:
        h, w = stdscr.getmaxyx()
        
        # 检查坐标是否有效
        if y < 0 or y >= h or x < 0 or x >= w:
            return False
        
        # 截断文本以适应窗口
        max_len = max(0, w - x)
        if max_len == 0:
            return False
        
        text_str = str(text) if text is not None else ""
        display_text = text_str[:max_len]
        
        # 绘制
        stdscr.addstr(y, x, display_text, attr)
        return True
    except curses.error:
        return False


def safe_addhline(stdscr, y, x, ch, length):
    """安全的水平线绘制"""
    try:
        h, w = stdscr.getmaxyx()
        
        # 检查坐标
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        
        # 计算实际长度
        actual_length = min(length, w - x)
        if actual_length <= 0:
            return
        
        # 绘制
        stdscr.hline(y, x, ch, actual_length)
    except curses.error:
        pass


def safe_draw_explain_bar(stdscr, y, w, explain_lines):
    """安全的解释栏绘制"""
    if not explain_lines:
        return
    
    # 获取当前窗口高度
    h, actual_w = stdscr.getmaxyx()
    if y >= h or w <= 0:
        return
    
    raw = explain_lines[-1]
    if not raw:
        return
    
    msg = trim_to_width(raw, w - 4)
    vw = visual_width(msg)
    x = w - vw - 2
    if x < 2:
        x = 2
    
    # 确保不会超出窗口右边界
    if x + vw >= actual_w:
        msg = trim_to_width(msg, actual_w - x - 2)
        vw = visual_width(msg)
    
    # 安全绘制
    try:
        stdscr.addstr(y, x, msg)
    except curses.error:
        pass


def draw_explain_bar(stdscr, y, w, explain_lines):
    # 旧函数保留兼容性，但实际使用安全版本
    safe_draw_explain_bar(stdscr, y, w, explain_lines)


def safe_getch(stdscr, timeout_ms=-1):
    """
    安全的getch函数，处理KeyboardInterrupt
    返回: 按键代码或None（如果超时或被中断）
    """
    try:
        if timeout_ms > 0:
            stdscr.timeout(timeout_ms)
            key = stdscr.getch()
            stdscr.timeout(-1)  # 恢复阻塞模式
        else:
            key = stdscr.getch()
        return key
    except KeyboardInterrupt:
        return 3  # ASCII码3对应Ctrl+C
    except Exception:
        return None


def graceful_exit(state, explain_lines, confirm=True):
    """优雅退出程序"""
    # 终止所有进程
    killed = process_manager.kill_all()
    if killed > 0:
        explain_lines.append(f"已终止{killed}个进程")
    
    # 保存当前配置
    save_cache()
    
    # 返回True表示确认退出
    return True

# ============================================================
# run 命令管理
# ============================================================

# ============================================================
# 空值判断工具函数
# ============================================================

def is_empty_field_value(value, field_type=None):
    """
    判断字段值是否为空
    
    规则：
    1. None -> 空
    2. 空字符串 -> 空
    3. 仅包含空白字符的字符串 -> 空
    4. 空列表/字典/元组 -> 空
    5. 布尔值False -> 有效值（不视为空）
    6. 数字0 -> 有效值（不视为空）
    
    Args:
        value: 字段值
        field_type: 字段类型（可选）
    
    Returns:
        bool: 是否为空值
    """
    if value is None:
        return True
    
    # 字符串类型
    if isinstance(value, str):
        stripped = value.strip()
        # 空字符串视为空
        if stripped == "":
            return True
        # 对于路径类型，即使有值也需要检查是否为有效路径
        if field_type == "path":
            # 如果路径包含占位符或模板变量，视为有效值
            if stripped.startswith("{") and stripped.endswith("}"):
                return False
            # 路径中只包含点或斜杠的视为空
            if stripped in [".", "..", "/", "\\"]:
                return True
        return False
    
    # 布尔类型：True和False都是有效值
    if isinstance(value, bool):
        return False
    
    # 数字类型：0是有效值
    if isinstance(value, (int, float)):
        return False
    
    # 集合类型
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    
    # 其他类型
    return False

def build_run_command():
    """构建当前界面的运行命令（空值字段不包含在命令中）"""
    cmd = []
    
    if CURRENT_SCREEN == "inference":
        cmd = ["python", "inference.py"]
    elif CURRENT_SCREEN == "train":
        cmd = ["python", "train.py"]
    else:
        return []
    
    screen_info = SCREENS[CURRENT_SCREEN]
    field_mapping = screen_info["field_mapping"]
    
    # 记录被跳过的字段，用于调试信息
    skipped_fields = []
    
    # 特殊字段处理规则
    special_field_rules = {
        # inference界面的特殊规则
        "inference": {
            "device_ids": lambda v: v != "0",  # 默认值"0"也视为有效
            "num_workers": lambda v: v != 0,   # 0可能表示不使用多进程
        },
        # train界面的特殊规则
        "train": {
            "num_workers": lambda v: v != 0,
        }
    }
    
    # 应用特殊规则
    current_screen = CURRENT_SCREEN
    special_rules = special_field_rules.get(current_screen, {})
    
    # 使用所有字段构建命令（包括隐藏字段）
    for field in get_all_current_fields():
        field_name = field["name"]
        
        # 跳过preset字段，它不传递给命令
        if field_name == "preset":
            continue
            
        key = field_mapping.get(field_name)
        if not key:
            continue
            
        val = field["value"]
        field_type = field["type"]
        
        # 检查是否有特殊规则
        special_rule = special_rules.get(field_name)
        if special_rule:
            # 应用特殊规则
            if not special_rule(val):
                if DEBUG_MODE:
                    print(f"DEBUG: 根据特殊规则跳过字段 {field_name} (值: {val})")
                continue
        else:
            # 使用通用空值判断
            if is_empty_field_value(val, field_type):
                skipped_fields.append(field_name)
                if DEBUG_MODE:
                    print(f"DEBUG: 跳过空值字段 {field_name}")
                continue
            
        # 特殊处理bool类型
        if field_type == "bool":
            # 对于bool类型，只有True值才添加参数
            bool_str = str(val).lower()
            if bool_str in ["true", "1", "yes", "on", "t"]:
                cmd.append(key)
                if DEBUG_MODE:
                    print(f"DEBUG: 添加布尔参数 {key}")
            else:
                # False值不添加参数，但记录在调试模式
                if DEBUG_MODE:
                    print(f"DEBUG: 跳过布尔参数 {key} (值为{val})")
        else:
            # 其他类型：添加参数和值
            cmd.extend([key, str(val)])
            if DEBUG_MODE:
                print(f"DEBUG: 添加参数 {key} {val}")
    
    # 在调试模式下显示跳过的字段
    if DEBUG_MODE and skipped_fields:
        print(f"DEBUG: 跳过空值字段: {', '.join(skipped_fields)}")
    
    return cmd

def run_inference(explain_lines):
    """在新的命令行窗口中运行推理"""
    cmd_list = build_run_command()
    
    # 如果没有有效字段，不执行命令
    if len(cmd_list) <= 2:  # 只有python和脚本名
        explain_lines.append("错误: 没有有效的参数配置")
        return
    
    # 在调试模式下显示完整的命令构建过程
    if DEBUG_MODE:
        explain_lines.append(f"构建命令参数:")
        explain_lines.append(f"  基础命令: {cmd_list[0]} {cmd_list[1]}")
        
        # 显示每个参数
        i = 2
        while i < len(cmd_list):
            if i + 1 < len(cmd_list):
                explain_lines.append(f"  {cmd_list[i]} {cmd_list[i+1]}")
                i += 2
            else:
                explain_lines.append(f"  {cmd_list[i]}")
                i += 1
    
    cmd_str = " ".join(shlex.quote(arg) for arg in cmd_list)
    explain_lines.append(f"运行命令: {cmd_str}")
    
    try:
        if sys.platform.startswith("win"):
            # Windows: 使用start命令在新窗口运行
            full_cmd = ["cmd", "/c", "start", "cmd", "/k"] + cmd_list
            proc = subprocess.Popen(
                full_cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            pid = proc.pid
            
        else:
            # Linux/macOS: 尝试多种终端模拟器
            term_emulators = [
                "x-terminal-emulator", "gnome-terminal", "konsole",
                "xfce4-terminal", "terminator", "urxvt", "xterm"
            ]
            
            proc = None
            pid = None
            
            for term in term_emulators:
                try:
                    subprocess.run(["which", term], 
                                 check=False, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
                    
                    term_cmd = [term, "-e", "bash", "-c"]
                    bash_cmd = f"{cmd_str}; echo '按Enter键退出...'; read"
                    term_cmd.append(bash_cmd)
                    
                    proc = subprocess.Popen(term_cmd)
                    pid = proc.pid
                    break
                except (OSError, subprocess.SubprocessError):
                    continue
            
            # 回退方案
            if proc is None:
                proc = subprocess.Popen(cmd_list)
                pid = proc.pid
        
        # 添加到进程管理器
        process_id = process_manager.add_process(pid, cmd_str, proc)
        explain_lines.append(f"{LANGS[CURRENT_LANG]['process_created']} (ID: {process_id}, PID: {pid})")
        
        # 启动监控线程
        threading.Thread(
            target=monitor_process,
            args=(pid, process_id),
            daemon=True
        ).start()
        
    except Exception as e:
        explain_lines.append(f"{LANGS[CURRENT_LANG]['process_error']}: {str(e)}")

def monitor_process(pid, process_id):
    """监控进程状态"""
    # 查找进程对象
    proc_info = process_manager.get_process(process_id)
    if not proc_info or not proc_info["proc_obj"]:
        return
    
    proc = proc_info["proc_obj"]
    
    try:
        # 等待进程结束
        return_code = proc.wait()
        
        # 更新状态
        if return_code == 0:
            status = "completed"
        elif return_code == -signal.SIGTERM:
            status = "killed"
        else:
            status = "failed"
        
        process_manager.update_status(pid, status, return_code)
        
        # 定期清理已完成进程
        process_manager.cleanup_finished()
        
    except Exception:
        # 如果进程已经结束或无法等待
        process_manager.update_status(pid, "failed")

# ============================================================
# 主程序 - 重构版
# ============================================================

def main(stdscr):
    global CURRENT_SCREEN, CURRENT_LANG, DEBUG_MODE
    
    try:
        curses.curs_set(1)
        stdscr.keypad(True)
        curses.use_default_colors()
        
        # 初始化颜色
        try:
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        except:
            pass
        
        load_cache()
        
        # 初始化状态管理器
        state = TUIState()
        explain_lines = []
        
        while True:
            stdscr.clear()
            lang = LANGS[CURRENT_LANG]
            h, w = stdscr.getmaxyx()
            
            # =====================================================
            # 安全绘制Header
            # =====================================================
            debug_status = " [调试模式]" if DEBUG_MODE else ""
            header_text = f"=== MVSEP TUI - {SCREENS[CURRENT_SCREEN]['name']}{debug_status} ==="
            safe_addstr(stdscr, 0, 2, header_text)
            safe_addstr(stdscr, 1, 2, lang["help_bar"])
            
            # 获取可见字段
            visible_fields = get_current_fields()
            
            # 确保当前索引有效
            state.ensure_valid_index(visible_fields)
            
            # Fields显示
            safe_addstr(stdscr, 3, 2, lang["fields"])
            max_fields = min(len(visible_fields), h - 15)
            
            # 使用安全绘制函数
            safe_draw_fields(stdscr, 4, visible_fields, state.current_visible_index, state.view_mode)
            
            # EDIT模式显示
            if state.edit_mode:
                field = state.get_editing_field()
                if field:
                    edit_start_y = 4 + max_fields + 2
                    
                    # 绘制分隔线
                    safe_addhline(stdscr, edit_start_y, 0, "-", w)
                    safe_addstr(stdscr, edit_start_y + 1, 2, f"{lang['editing']} {field['name']}")
                    safe_addhline(stdscr, edit_start_y + 2, 0, "-", w)
                    
                    # 显示编辑缓冲区
                    edit_line = edit_start_y + 3
                    safe_draw_edit_buffer(stdscr, edit_line, 2, state.edit_buffer, state.edit_cursor_pos)
                    
                    # 预览区域
                    if state.preview_items and edit_line + 2 < h - 5:
                        safe_addhline(stdscr, edit_line + 1, 0, "-", w)
                        safe_addstr(stdscr, edit_line + 2, 2, lang["preview"])
                        
                        # 安全绘制预览
                        safe_draw_preview_column_major(
                            stdscr,
                            state.preview_items,
                            edit_line + 3,
                            h - edit_line - 8,
                            30,
                            state.preview_selected_index
                        )
            
            # HELP模式显示
            elif state.help_mode:
                help_start = 4 + max_fields + 2
                safe_addhline(stdscr, help_start, 0, "-", w)
                safe_addstr(stdscr, help_start + 1, 2, lang["help_title"])
                safe_addhline(stdscr, help_start + 2, 0, "-", w)
                
                for i, line in enumerate(HELP_TEXT):
                    if help_start + 3 + i < h - 5:
                        safe_addstr(stdscr, help_start + 3 + i, 4, line)
            
            # 进程列表显示（仅推理界面）
            elif state.view_mode and CURRENT_SCREEN == "inference":
                process_start_y = 4 + max_fields + 2
                if process_start_y < h - 10:
                    safe_addhline(stdscr, process_start_y, 0, "-", w)
                    safe_addstr(stdscr, process_start_y + 1, 2, lang["processes"])
                    safe_addhline(stdscr, process_start_y + 2, 0, "-", w)
                    
                    safe_draw_process_list(
                        stdscr,
                        process_start_y + 3,
                        h - process_start_y - 8,
                        w,
                        state.selected_process_id
                    )
            
            # 命令栏显示
            safe_addhline(stdscr, h - 3, 0, "-", w)
            stdscr.move(h - 2, 0)
            stdscr.clrtoeol()
            
            if state.command_mode:
                safe_addstr(stdscr, h - 2, 2, ":" + state.command_buffer)
            else:
                safe_addstr(stdscr, h - 2, 2, lang["cmd_prompt"])
            
            # 解释栏和调试状态
            safe_draw_explain_bar(stdscr, h - 2, w, explain_lines)
            
            if DEBUG_MODE:
                debug_text = f"Debug=ON Screen={CURRENT_SCREEN}"
                safe_addstr(stdscr, h - 2, w - len(debug_text) - 2, debug_text, curses.A_DIM)
            
            stdscr.refresh()

            # =====================================================
            # 安全获取按键（处理KeyboardInterrupt）
            # =====================================================
            try:
                key = stdscr.getch()
            except KeyboardInterrupt:
                # Ctrl+C: 静默退出
                key = 3  # ASCII码3对应Ctrl+C
                # 如果是在命令模式下，清除命令缓冲区
                if state.command_mode:
                    state.command_buffer = ""
                    state.exit_command_mode()
                else:
                    # 否则触发退出流程
                    key = ord('q')  # 模拟:q命令
            
            # =====================================================
            # 输入处理逻辑
            # =====================================================
            
            # 全局快捷键
            if key == 27:  # ESC
                if state.help_mode:
                    state.help_mode = False
                    state.view_mode = True
                elif state.edit_mode:
                    state.exit_edit_mode()
                elif state.command_mode:
                    state.exit_command_mode()
                elif state.process_selection_mode:
                    state.toggle_process_selection([])
                else:
                    # ESC在VIEW模式下无操作
                    pass
                continue

            # 处理Ctrl+C (ASCII 3) - 退出程序
            if key == 3:  # Ctrl+C
                # 清理所有进程
                killed = process_manager.kill_all()
                if killed > 0:
                    explain_lines.append(f"已终止{killed}个进程")
                # 设置退出标志
                break

            if key == 4:  # Ctrl+D
                DEBUG_MODE = not DEBUG_MODE
                if DEBUG_MODE:
                    explain_lines.append("调试模式已开启：显示所有字段")
                else:
                    explain_lines.append("调试模式已关闭：只显示可见字段")
                # 更新可见字段列表后，调整当前索引
                visible_fields = get_current_fields()
                state.ensure_valid_index(visible_fields)
                continue
            
            if key == 21:  # Ctrl+U
                if state.edit_mode:
                    state.edit_buffer = ""
                    state.edit_cursor_pos = 0
                elif state.command_mode:
                    state.command_buffer = ""
                continue
            
            if key == curses.KEY_F2:  # F2切换界面
                if CURRENT_SCREEN == "inference":
                    CURRENT_SCREEN = "train"
                else:
                    CURRENT_SCREEN = "inference"
                state = TUIState()  # 重置所有状态
                explain_lines.append(f"切换到{SCREENS[CURRENT_SCREEN]['name']}")
                continue
            
            # 命令模式处理
            if state.command_mode:
                if key in (10, 13):  # Enter
                    parts = shlex.split(state.command_buffer)
                    explain_lines.clear()
                    
                    if not parts:
                        state.exit_command_mode()
                        continue
                    
                    cmd, *args = parts
                    if cmd == "q":
                        # 退出前终止所有进程
                        if graceful_exit(state, explain_lines, confirm=False):
                            break
                    elif cmd == "save":
                        if args:
                            save_as(args[0])
                            explain_lines.append(f"配置已保存到 {args[0]}")
                        else:
                            save_cache()
                            explain_lines.append("配置已保存到缓存")
                    elif cmd == "import":
                        if args:
                            import_fields(args[0])
                            explain_lines.append(f"配置已从 {args[0]} 导入")
                        else:
                            explain_lines.append("请指定导入文件路径")
                    elif cmd == "language":
                        if args and args[0] in LANGS:
                            CURRENT_LANG = args[0]
                            explain_lines.append(f"语言切换为 {args[0]}")
                        else:
                            explain_lines.append(f"可用语言: {', '.join(LANGS.keys())}")
                    elif cmd == "run":
                        # 运行当前界面的命令
                        threading.Thread(
                            target=run_inference, 
                            args=(explain_lines,), 
                            daemon=True
                        ).start()
                        explain_lines.append("启动进程...")
                    elif cmd == "kill":
                        if args:
                            if args[0] == "all":
                                killed = process_manager.kill_all()
                                explain_lines.append(f"{lang['kill_all_success']} ({killed}个进程)")
                            else:
                                try:
                                    pid_or_id = int(args[0])
                                    if process_manager.kill_process(pid_or_id):
                                        explain_lines.append(f"{lang['kill_success']} {args[0]}")
                                    else:
                                        explain_lines.append(f"{lang['kill_error']} {args[0]}")
                                except ValueError:
                                    explain_lines.append("参数错误: 需要PID或ID数字")
                        else:
                            explain_lines.append("用法: :kill <pid/id> 或 :kill all")
                    elif cmd == "ps":
                        # 显示进程状态
                        processes = process_manager.get_all_processes()
                        if processes:
                            explain_lines.append(f"当前有{len(processes)}个进程")
                            for p in processes[-3:]:  # 显示最近3个
                                explain_lines.append(f"  ID:{p['id']} PID:{p['pid']} {p['status']}")
                        else:
                            explain_lines.append(lang["no_process"])
                    elif cmd == "help":
                        state.previous_mode = "COMMAND"
                        state.help_mode = True
                    else:
                        explain_lines.append("未知命令")
                    
                    state.command_buffer = ""
                    if not state.help_mode:
                        state.exit_command_mode()
                    continue
                
                elif key in (curses.KEY_BACKSPACE, 127):
                    state.command_buffer = state.command_buffer[:-1]
                elif 32 <= key <= 126:
                    state.command_buffer += chr(key)
                
                # VIEW模式处理
                if state.view_mode:
                    # 确保当前索引有效
                    state.ensure_valid_index(visible_fields)
                    
                    if key == ord(":"):
                        state.enter_command_mode()
                    elif key == curses.KEY_UP:
                        if state.process_selection_mode and CURRENT_SCREEN == "inference":
                            # 进程列表导航
                            processes = process_manager.get_all_processes()
                            if processes and state.selected_process_id:
                                current_index = -1
                                for i, p in enumerate(processes):
                                    if p["id"] == state.selected_process_id:
                                        current_index = i
                                        break
                                if current_index > 0:
                                    state.selected_process_id = processes[current_index - 1]["id"]
                        elif state.current_visible_index > 0:
                            state.current_visible_index -= 1
                    elif key == curses.KEY_DOWN:
                        if state.process_selection_mode and CURRENT_SCREEN == "inference":
                            # 进程列表导航
                            processes = process_manager.get_all_processes()
                            if processes and state.selected_process_id:
                                current_index = -1
                                for i, p in enumerate(processes):
                                    if p["id"] == state.selected_process_id:
                                        current_index = i
                                        break
                                if current_index < len(processes) - 1:
                                    state.selected_process_id = processes[current_index + 1]["id"]
                        elif state.current_visible_index < len(visible_fields) - 1:
                            state.current_visible_index += 1
                    elif key in (10, 13):  # Enter
                        if state.process_selection_mode and CURRENT_SCREEN == "inference":
                            # 查看进程详情
                            proc = process_manager.get_process(state.selected_process_id)
                            if proc:
                                explain_lines.clear()
                                explain_lines.append(f"进程 {proc['id']} (PID: {proc['pid']})")
                                explain_lines.append(f"状态: {proc['status']}")
                                explain_lines.append(f"命令: {proc['cmd'][:w-4]}")
                        else:
                            # 进入编辑模式
                            current_field = get_current_field_for_view(state)
                            if current_field:  # 移除了 and not current_process 条件，因为变量未定义
                                state.enter_edit_mode(current_field["id"], current_field["value"])
                                # 更新预览
                                field = state.get_editing_field()
                                EditSystem.update_preview(state, field)
                    elif key == ord("k") and state.process_selection_mode and CURRENT_SCREEN == "inference":
                        # 终止选中的进程
                        if state.selected_process_id and process_manager.kill_process(state.selected_process_id):
                            explain_lines.append(f"{lang['kill_success']} {state.selected_process_id}")
                        else:
                            explain_lines.append(f"{lang['kill_error']} {state.selected_process_id}")
                    elif key == ord(" ") and CURRENT_SCREEN == "inference":
                        # 切换进程选择模式
                        processes = process_manager.get_all_processes()
                        state.toggle_process_selection(processes)
                
                # EDIT模式处理
                if state.edit_mode:
                    field = state.get_editing_field()
                    if not field:
                        state.exit_edit_mode()
                        continue
                    
                    # 更新预览
                    EditSystem.update_preview(state, field)
                    
                    if key == curses.KEY_LEFT and state.edit_cursor_pos > 0:
                        state.edit_cursor_pos -= 1
                    elif key == curses.KEY_RIGHT and state.edit_cursor_pos < len(state.edit_buffer):
                        state.edit_cursor_pos += 1
                    elif key == curses.KEY_UP and state.preview_items:
                        state.preview_selected_index = max(0, state.preview_selected_index - 1)
                    elif key == curses.KEY_DOWN and state.preview_items:
                        state.preview_selected_index = min(len(state.preview_items) - 1, state.preview_selected_index + 1)
                    elif key in (curses.KEY_BACKSPACE, 127):
                        EditSystem.handle_backspace(state)
                        EditSystem.update_preview(state, field)
                    elif key == 9 and state.preview_items:  # Tab补全
                        EditSystem.handle_tab_completion(state, field)
                        EditSystem.update_preview(state, field)
                    elif key in (10, 13):  # Enter确认
                        if EditSystem.handle_enter_confirmation(state):
                            # 保存成功后，如果字段值为空，添加到跳过列表
                            field = state.get_editing_field()
                            if field and is_empty_field_value(field["value"], field["type"]):
                                if DEBUG_MODE:
                                    explain_lines.append(f"字段 '{field['name']}' 已清空，将不会包含在命令中")
                            state.exit_edit_mode()
                    elif 32 <= key <= 126:
                        EditSystem.handle_character_input(state, chr(key))
                        EditSystem.update_preview(state, field)
                    
                    # 确保编辑光标位置有效
                    state.ensure_valid_edit_cursor()

    except KeyboardInterrupt:
        # 额外捕获，确保在任何地方按Ctrl+C都能静默退出
        pass
    
    finally:
        # 确保curses正确结束
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    curses.wrapper(main)