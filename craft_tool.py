import time
import random
import threading
import os
import pyautogui
import pyperclip
import keyboard
import tkinter as tk
from tkinter import messagebox, StringVar

import pystray
from PIL import Image, ImageDraw

# ==================== 默认配置（已按你的坐标修改） ====================
DEFAULT_CONFIG = {
    # 通货坐标
    "ALT_POS": "150,360",          # 改造石坐标
    "CHANCE_POS": "300,360",       # 机会石坐标
    "SCOUR_POS": "580,530",        # 重铸石坐标
    # 装备坐标列表，多个坐标用分号分隔
    "EQUIP_POS_LIST": "440,600",
    # 是否使用重铸石（仅机会石模式有效）
    "USE_SCOUR": "true",
    # 传奇标识关键词（仅机会石模式有效）
    "UNIQUE_KEYWORD": "传奇",
    "STOP_ON_UNIQUE": "true",
    # 目标关键词（仅改造石模式有效）
    "KEYWORDS": "最大生命,火焰抗性,攻击速度,暴击率",
    # 最大尝试次数
    "MAX_ATTEMPTS": "1000",
    # 延迟
    "CLICK_DELAY": "0.05",
    "HOVER_DELAY": "0.1",
    # 快捷键
    "START_HOTKEY": "F6",
    "STOP_HOTKEY": "F7",
    "EXIT_HOTKEY": "F8",
    # 默认模式：alt 或 chance
    "MODE": "alt",
}

CONFIG_FILE = "config.txt"

def load_config():
    config = DEFAULT_CONFIG.copy()
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("# 洗装备工具配置文件\n")
            f.write("# 每行一个配置项，格式：键=值\n")
            f.write("# 装备坐标列表用分号分隔，例如：(440,600);(500,600)\n")
            f.write("# USE_SCOUR 为 true 时先重铸再机会石，false 时直接机会石\n")
            f.write("# UNIQUE_KEYWORD 是传奇标识文字，国服“传奇”，国际服“Unique”\n")
            f.write("# MODE 可选 alt（改造石）或 chance（机会石+重铸石）\n")
            f.write("# 关键词用英文逗号分隔（仅改造石模式使用）\n\n")
            for key, value in DEFAULT_CONFIG.items():
                f.write(f"{key}={value}\n")
        return config
    else:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key in config:
                        config[key] = value
        return config

def parse_coord(s):
    parts = s.split(",")
    return (int(parts[0].strip()), int(parts[1].strip()))

def parse_coord_list(s):
    coords = []
    for item in s.split(";"):
        item = item.strip().strip("()")
        if item:
            coords.append(parse_coord(item))
    return coords

def parse_keywords(s):
    return [kw.strip() for kw in s.split(",") if kw.strip()]

cfg = load_config()
ALT_POS = parse_coord(cfg["ALT_POS"])
CHANCE_POS = parse_coord(cfg["CHANCE_POS"])
SCOUR_POS = parse_coord(cfg["SCOUR_POS"])
EQUIP_POS_LIST = parse_coord_list(cfg["EQUIP_POS_LIST"])
USE_SCOUR = cfg["USE_SCOUR"].lower() == "true"
UNIQUE_KEYWORD = cfg["UNIQUE_KEYWORD"]
STOP_ON_UNIQUE = cfg["STOP_ON_UNIQUE"].lower() == "true"
KEYWORDS = parse_keywords(cfg["KEYWORDS"])
MAX_ATTEMPTS = int(cfg["MAX_ATTEMPTS"])
CLICK_DELAY = float(cfg["CLICK_DELAY"])
HOVER_DELAY = float(cfg["HOVER_DELAY"])
START_HOTKEY = cfg["START_HOTKEY"]
STOP_HOTKEY = cfg["STOP_HOTKEY"]
EXIT_HOTKEY = cfg["EXIT_HOTKEY"]
MODE = cfg.get("MODE", "alt")

pyautogui.FAILSAFE = True
start_event = threading.Event()
stop_event = threading.Event()
exit_event = threading.Event()

root = None
status_label = None
keyword_entry = None
mode_var = None

def safe_click(pos, button='left'):
    x, y = pos
    pyautogui.moveTo(x + random.randint(-2, 2), y + random.randint(-2, 2), duration=0.03)
    time.sleep(random.uniform(0.02, 0.05))
    pyautogui.click(button=button)
    time.sleep(CLICK_DELAY)

def apply_currency(currency_pos, equip_pos):
    safe_click(currency_pos, button='right')
    time.sleep(0.1)
    safe_click(equip_pos, button='left')
    time.sleep(HOVER_DELAY)

def get_item_text(equip_pos):
    pyautogui.moveTo(equip_pos[0], equip_pos[1], duration=0.03)
    time.sleep(0.02)
    pyperclip.copy('')
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.05)
    return pyperclip.paste()

def check_keywords(text):
    """检查文本中是否包含任意关键词（仅改造石模式使用）"""
    clean_text = ''.join(text.split())
    for kw in KEYWORDS:
        clean_kw = ''.join(kw.split())
        if clean_kw in clean_text:
            return True, kw
    return False, None

def is_unique_item(text):
    """检查物品是否为传奇（仅机会石模式使用）"""
    clean_text = ''.join(text.split())
    return UNIQUE_KEYWORD in clean_text

def write_log(msg):
    with open('craft_log.txt', 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

# ==================== 两种模式的装备处理函数 ====================
def process_equip_alt(equip_pos):
    """改造石模式：仅使用改造石，检测关键词"""
    attempts = 0
    while attempts < MAX_ATTEMPTS and not stop_event.is_set() and not exit_event.is_set():
        apply_currency(ALT_POS, equip_pos)
        text = get_item_text(equip_pos)
        found, kw = check_keywords(text)
        write_log(f"改造石 装备 {equip_pos} 第 {attempts+1} 次，物品信息：\n{text}\n")
        if found:
            write_log(f"✅ 装备 {equip_pos} 命中关键词：{kw}")
            return 'found'
        attempts += 1
        time.sleep(random.uniform(0.05, 0.1))
    if stop_event.is_set() or exit_event.is_set():
        return 'stopped'
    return 'max_attempts'

def process_equip_chance(equip_pos):
    """机会石模式：可先重铸，使用机会石，只检测传奇，不检测关键词"""
    attempts = 0
    while attempts < MAX_ATTEMPTS and not stop_event.is_set() and not exit_event.is_set():
        if USE_SCOUR:
            apply_currency(SCOUR_POS, equip_pos)
            time.sleep(0.05)
        apply_currency(CHANCE_POS, equip_pos)
        text = get_item_text(equip_pos)

        # 只检测传奇
        if STOP_ON_UNIQUE and is_unique_item(text):
            write_log(f"装备 {equip_pos} 检测到传奇，停止处理")
            return 'unique'

        # 记录日志，但不检测关键词
        write_log(f"机会石 装备 {equip_pos} 第 {attempts+1} 次，物品信息：\n{text}\n")
        attempts += 1
        time.sleep(random.uniform(0.05, 0.1))
    if stop_event.is_set() or exit_event.is_set():
        return 'stopped'
    return 'max_attempts'

# ==================== 主循环 ====================
def craft_loop():
    while not exit_event.is_set():
        start_event.wait()
        start_event.clear()
        stop_event.clear()
        for idx, equip_pos in enumerate(EQUIP_POS_LIST):
            if stop_event.is_set() or exit_event.is_set():
                break
            write_log(f"开始处理装备 {idx+1}/{len(EQUIP_POS_LIST)}，坐标：{equip_pos}")
            root.after(0, update_status, f"正在处理装备 {idx+1}/{len(EQUIP_POS_LIST)}...")

            if MODE == 'alt':
                result = process_equip_alt(equip_pos)
            else:
                result = process_equip_chance(equip_pos)

            if result == 'found':
                # 仅改造石模式会进入这个分支
                root.after(0, lambda p=equip_pos: messagebox.showinfo("洗装备工具", f"装备 {p} 已找到目标词条"))
                break
            elif result == 'unique':
                # 机会石模式检测到传奇：弹“恭喜成功！”
                root.after(0, lambda: messagebox.showinfo("恭喜成功！", "恭喜成功！"))
                break
            elif result == 'max_attempts':
                # 达到最大次数不弹窗，只写日志，继续下一个装备
                write_log(f"装备 {equip_pos} 达到最大尝试次数，未找到目标，继续下一个")
            elif result == 'stopped':
                break

        # 取消“所有装备处理完成”弹窗
        # if not stop_event.is_set() and not exit_event.is_set():
        #     root.after(0, lambda: messagebox.showinfo("洗装备工具", "所有装备处理完成"))
        root.after(0, update_status, "就绪")

def update_status(text):
    if status_label:
        status_label.config(text=text)

# ==================== 界面与热键 ====================
def start_craft_from_ui():
    global KEYWORDS, MODE
    keywords_str = keyword_entry.get().strip()
    if not keywords_str:
        messagebox.showwarning("提示", "请输入关键词")
        return
    KEYWORDS = parse_keywords(keywords_str)
    MODE = mode_var.get()   # 点击按钮时获取模式
    update_status("运行中...")
    print(f"开始，模式：{MODE}，关键词：{KEYWORDS}")
    start_event.set()

def start_craft_hotkey():
    global MODE
    MODE = mode_var.get()   # 热键启动时也获取模式
    if not start_event.is_set():
        update_status("运行中...")
        print(f"热键开始，模式：{MODE}，关键词：{KEYWORDS}")
        start_event.set()

def stop_craft():
    print("收到停止指令")
    stop_event.set()

def exit_program():
    print("退出程序")
    exit_event.set()
    stop_event.set()
    start_event.set()
    if root:
        root.quit()
        root.destroy()
    os._exit(0)

# ==================== 托盘图标 ====================
def create_image():
    img = Image.new('RGB', (64, 64), color=(60, 60, 60))
    d = ImageDraw.Draw(img)
    d.rectangle([16, 16, 48, 48], fill=(200, 150, 50))
    d.text((28, 28), "C", fill=(0, 0, 0))
    return img

def show_window():
    if root:
        root.deiconify()

def hide_window():
    if root:
        root.withdraw()

def setup_tray():
    menu = pystray.Menu(
        pystray.MenuItem("显示窗口", show_window),
        pystray.MenuItem("开始 (F6)", start_craft_hotkey),
        pystray.MenuItem("停止 (F7)", stop_craft),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", exit_program)
    )
    icon = pystray.Icon("craft_tool", create_image(), "洗装备工具", menu)
    return icon

def main():
    global root, status_label, keyword_entry, mode_var, MODE

    root = tk.Tk()
    root.title("洗装备工具（改造石 / 机会石+重铸石）")
    root.geometry("400x250")
    root.resizable(False, False)

    # 模式选择单选按钮
    mode_var = StringVar(value=MODE)
    def on_mode_change(*args):
        global MODE
        MODE = mode_var.get()
        print(f"模式切换为：{MODE}")
    mode_var.trace_add('write', on_mode_change)

    mode_frame = tk.Frame(root)
    mode_frame.pack(pady=(10,5))
    tk.Label(mode_frame, text="选择模式：").pack(side=tk.LEFT)
    tk.Radiobutton(mode_frame, text="改造石", variable=mode_var, value="alt").pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(mode_frame, text="机会石+重铸石", variable=mode_var, value="chance").pack(side=tk.LEFT, padx=5)

    # 关键词输入（仅在改造石模式下使用）
    tk.Label(root, text="目标词条（用英文逗号分隔，仅改造石模式）:").pack(pady=(5,5))
    keyword_entry = tk.Entry(root, width=40)
    keyword_entry.insert(0, cfg["KEYWORDS"])
    keyword_entry.pack(pady=(0,10))

    # 按钮行
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="开始 (F6)", width=12, command=start_craft_from_ui).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="停止 (F7)", width=12, command=stop_craft).grid(row=0, column=1, padx=5)
    tk.Button(btn_frame, text="退出 (F8)", width=12, command=exit_program).grid(row=0, column=2, padx=5)

    # 状态标签
    status_label = tk.Label(root, text="就绪", fg="blue")
    status_label.pack(pady=(10,0))

    root.protocol('WM_DELETE_WINDOW', hide_window)

    keyboard.add_hotkey(START_HOTKEY, start_craft_hotkey)
    keyboard.add_hotkey(STOP_HOTKEY, stop_craft)
    keyboard.add_hotkey(EXIT_HOTKEY, exit_program)

    print(f"洗装备工具已启动，初始模式：{MODE}，关键词：{KEYWORDS}")
    print(f"按 {START_HOTKEY} 开始，按 {STOP_HOTKEY} 停止，按 {EXIT_HOTKEY} 退出")

    t = threading.Thread(target=craft_loop, daemon=True)
    t.start()

    tray_icon = setup_tray()
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

    root.mainloop()

if __name__ == '__main__':
    main()
