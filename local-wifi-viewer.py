'''打包语句
pyinstaller -F -w -i wifi.ico 本地WiFi密码查看器.py
pyinstaller -F --hide-console hide-early -i wifi.ico 本地WiFi密码查看器.py
pyinstaller --hide-console hide-early -i wifi.ico 本地WiFi密码查看器.py
'''
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from concurrent.futures import ThreadPoolExecutor
import time

def fetch_password(wifi) -> tuple[str, str] | None:
    """获取单个WiFi的密码"""
    results = subprocess.run(
        ['netsh', 'wlan', 'show', 'profile', wifi, 'key=clear'],
        capture_output=True
    ).stdout.decode('utf-8', errors='ignore').split('\n')
    
    # 提取包含密码的行（排除"无密码"的）
    password_lines = [line for line in results if "关键内容" in line or "Key Content" in line]
    # password_lines=['    关键内容            : 88888888\r']
    if password_lines:
        try:
            password = password_lines[0].split(':')[1][1:-1]
        except:
            password = "无法解析密码"
        return (wifi, password)
    else:
        return None  # 无密码的WiFi不保留

def get_current_wifi() -> str | None:
    """获取当前连接的WiFi名称"""
    try:
        results = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True
        ).stdout.decode('utf-8', errors='ignore').split('\n')
        # 提取WiFi名称
        return [line for line in results if "SSID" in line][0].split(':')[1][1:-1]
    except:
        return None
    
def get_wifi_info() -> list[tuple[str, str]] | None:

    """获取本机连接过的WiFi名称和密码（过滤无密码WiFi）"""
    try:
        # 获取所有WiFi配置文件
        output = subprocess.run(
            ['netsh', 'wlan', 'show', 'profiles'],
            capture_output=True
            ).stdout.decode('utf-8', errors='ignore').split('\n')
        
        # 提取WiFi名称
        wifis = [line.split(':')[1][1:-1] for line in output if "所有用户配置文件" in line]

        # 用线程池并行获取所有WiFi的密码
        with ThreadPoolExecutor() as executor:
            # 并行执行并收集结果，过滤掉无密码的WiFi
            wifi_data = [item for item in executor.map(fetch_password, wifis) if item is not None]
        
        
        return wifi_data
    except Exception as e:
        messagebox.showerror("错误", f"获取WiFi信息失败：{str(e)}")
        return None

def delete_wifi_profile(wifi_name: str) -> str:
    """删除指定WiFi配置文件"""
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'delete', 'profile', f'name={wifi_name}'],
            capture_output=True
        ).stdout.decode('utf-8', errors='ignore')
        return result
        # 已从接口“WLAN”中删除配置文件“{wifi_name}”。
        # 任何接口上都找不到配置文件“{wifi_name}”。  
    except Exception as e:
        return f"删除WiFi '{wifi_name}' 失败"

def load_wifi_info(event=None):
    """加载WiFi信息到表格"""
    try:
        # 使用全局变量wifi_data
        global wifi_data
        # time.sleep(1)
        current_wifi_name = get_current_wifi()
        current_wifi = fetch_password(current_wifi_name)
        wifi_data = get_wifi_info()
        # 按WiFi名称排序（不区分大小写）
        wifi_data.sort(key=lambda x: x[0].lower())
        # 找到元素索引
        if current_wifi is not None:
            current_wifi_new = (current_wifi[0]+"【当前连接的WiFi】",current_wifi[1])
            wifi_data = [current_wifi_new] + [x for x in wifi_data if x != current_wifi]

        # 将WiFi数据加载到表格
        for name, pwd in wifi_data:
            tree.insert('','end', values=(name, pwd))
    except:
        pass
    status_var.set(hint_text) # 还原为提示文本

# 搜索WiFi
def search_wifi(event=None):
    """根据WiFi名称查询，支持事件参数用于绑定Enter键"""
    filter_keyword = entry_search.get()

    # 使用全局变量wifi_data
    global wifi_data

    # 清空表格
    for item in tree.get_children():
        tree.delete(item)

    # 如果没有过滤关键词，显示所有
    if filter_keyword == "输入WiFi名称进行搜索" or filter_keyword == "":
        for name, pwd in wifi_data:
            tree.insert('', 'end', values=(name, pwd))
    # 如果有过滤关键词，则只显示匹配的项
    elif filter_keyword:
        filter_keyword = filter_keyword.lower().strip()
        for name, pwd in wifi_data:
            if filter_keyword in name.lower():
                tree.insert('', 'end', values=(name, pwd))

# 双击复制选中WiFi的密码
def copy_password_by_double_click(event):
    selected = tree.selection()
    if selected:
        selected_item = selected[0]
        password = tree.item(selected_item, 'values')[1]
        wifi_name = tree.item(selected_item, 'values')[0]
        root.clipboard_clear()
        root.clipboard_append(password)
        # 显示提示信息
        status_var.set(f"已复制 '{wifi_name}' 的密码到剪贴板")
        root.after(2000, lambda: status_var.set(hint_text))  # 2秒后还原为提示文本

# 搜索框获得焦点时
def on_search_focus_in(event):
    if entry_search.get() == "输入WiFi名称进行搜索":
        entry_search.delete(0, tk.END)
        entry_search.configure(foreground='black')

# 搜索框失去焦点时
def on_search_focus_out(event):
    if entry_search.get() == "":
        entry_search.insert(0, "输入WiFi名称进行搜索")
        entry_search.configure(foreground='grey')

# 复制密码和名称
def callback_copy(event=None):
    global root
    selected = tree.selection()
    if selected:
        selected_item = selected[0]
        password = tree.item(selected_item, 'values')[1]
        wifi_name = tree.item(selected_item, 'values')[0]
        root.clipboard_clear()
        root.clipboard_append(f"WiFi名称：{wifi_name}\nWiFi密码：{password}")
        # 显示提示信息
        status_var.set(f"已复制 '{wifi_name}' 的密码和名称到剪贴板")
        root.after(2000, lambda: status_var.set(hint_text))  # 2秒后还原为提示文本

# 删除选中WiFi
def callback_delete(event=None):
    global root
    selected = tree.selection()
    if selected:
        selected_item = selected[0]
        wifi_name = tree.item(selected_item, 'values')[0]
        result = delete_wifi_profile(wifi_name)
        if "删除" or "deleted" in result:
            # 从表格中删除选中项
            tree.delete(selected_item)
            # 显示删除成功提示
            status_var.set(f"已删除WiFi '{wifi_name}' 的配置文件")
            root.after(2000, lambda: status_var.set(hint_text))  # 2秒后还原为提示文本
        else:
            messagebox.showerror("删除失败", f"删除WiFi '{wifi_name}' 的配置文件失败：{result}")

# 弹出菜单（右键）
def popup(event):
    menu.post(event.x_root, event.y_root)   # post在指定的位置显示弹出菜单

def create_ui(root):
    global tree, status_var, entry_search, menu, hint_text
    
    # 创建主框架，添加内边距
    main_frame = ttk.Frame(root, padding="10 10 10 10") #左/上/右/下内边距
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 创建查询框框架
    search_frame = ttk.Frame(main_frame)
    search_frame.pack(fill=tk.X)

    # 搜索输入框
    entry_search = ttk.Entry(search_frame)
    entry_search.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
    entry_search.insert(0, "输入WiFi名称进行搜索")
    entry_search.configure(foreground='grey')

    entry_search.bind("<FocusIn>", on_search_focus_in)
    entry_search.bind("<FocusOut>", on_search_focus_out)
    entry_search.bind("<Return>", search_wifi)

    # 搜索按钮
    search_btn = ttk.Button(search_frame, text="搜索", command=search_wifi)
    search_btn.pack(side=tk.RIGHT)

    # 状态提示栏
    status_var = tk.StringVar()
    status_var.set(hint_text)
    status_label = ttk.Label(main_frame, textvariable=status_var, anchor=tk.W)
    status_label.pack(side=tk.TOP, fill=tk.X, pady=5) # 上下边距5

    # 创建表格框架
    tree_frame = ttk.Frame(main_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    # 创建Treeview表格
    tree = ttk.Treeview(tree_frame, columns=('WiFi名称', 'WiFi密码'), show='headings', selectmode='browse')
    tree.heading('WiFi名称', text='WiFi名称')
    tree.heading('WiFi密码', text='WiFi密码')

    # 设置列宽
    tree.column('WiFi名称', width=200, anchor=tk.W)
    tree.column('WiFi密码', width=200, anchor=tk.W)

    # 添加滚动条
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    # 布局表格和滚动条
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 绑定双击事件
    tree.bind("<Double-1>", copy_password_by_double_click)

    # 右键弹出菜单
    menu = tk.Menu(root,tearoff=False)
    menu.add_command(label="复制wifi名称+密码", command=callback_copy)
    menu.add_command(label="删除此wifi", command=callback_delete)
    tree.bind("<Button-3>", popup)

if __name__ == "__main__":   
    wifi_data = []
    global hint_text
    hint_text = "💡 提示：双击复制WiFi密码 | 右键可删除WiFi"
    # 创建主窗口
    root = tk.Tk()
    root.title("本机WiFi密码查看工具 v1.0")
    # 窗口居中
    w,h = 450,600
    screenw = root.winfo_screenwidth()
    screenh = root.winfo_screenheight()
    x = (screenw - w)/2
    y = (screenh - h)/2
    root.geometry(f"{w}x{h}+{x}+{y}") # 宽x高,距左上角+x+y
    root.attributes('-topmost', True) # 置顶
    root.iconbitmap("_internal\\wifi.ico") # 程序左上角图标
    # 创建UI界面
    create_ui(root)
    # 显示获取WiFi信息提示
    status_var.set("正在获取WiFi信息...")
    # 显示界面后，初始化加载WiFi信息（100毫秒后执行）
    root.after(100, load_wifi_info)

    root.mainloop()