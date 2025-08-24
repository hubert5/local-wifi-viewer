import tkinter as tk
from tkinter import ttk, messagebox
import subprocess, ctypes
from concurrent.futures import ThreadPoolExecutor

class WiFiViewer:
    def __init__(self, root):
        self.root = root
        self.VERSION = "1.1.0"
        self.root.title(f"本机WiFi密码查看工具 v{self.VERSION}")
        self.wifi_data = []
        self.hint_text = "💡 提示：[双击]复制WiFi密码 | [右键]删除WiFi"
        # 屏幕缩放因子
        self.sf = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100

        # 窗口配置
        self._setup_window()
        
        # 创建UI元素
        self._create_ui()
        
        # 初始化加载WiFi信息
        self.status_var.set("正在获取WiFi信息...")
        self.root.after(100, self.load_wifi_info)

    def _setup_window(self):
        """设置窗口基本属性"""
        try: # 启用高DPI感知（仅适用Windows）
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            pass

        # 设置窗口缩放
        self.root.tk.call('tk', 'scaling', self.sf*1.33)

        w, h = int(450*self.sf), int(600*self.sf)
        screenw = self.root.winfo_screenwidth()*self.sf
        screenh = self.root.winfo_screenheight()*self.sf
        x, y = int((screenw - w) / 2), int((screenh - h) / 2)

        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.attributes('-topmost', True) # 置顶
        try:
            self.root.iconbitmap("wifi.ico") # 窗口图标
        except:
            pass

    def _create_ui(self):
        """创建用户界面元素"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 查询框框架
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X)

        # 搜索输入框
        self.entry_search = ttk.Entry(search_frame)
        self.entry_search.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))

        self.entry_search.insert(0, "输入WiFi名称进行搜索")
        self.entry_search.configure(foreground='grey')
        self.entry_search.bind("<FocusIn>", self.on_search_focus_in)
        self.entry_search.bind("<FocusOut>", self.on_search_focus_out)
        self.entry_search.bind("<Return>", self.search_wifi)

        # 搜索按钮
        search_btn = ttk.Button(search_frame, text="搜索", command=self.search_wifi)
        search_btn.pack(side=tk.RIGHT)

        # 状态提示栏
        self.status_var = tk.StringVar()
        self.status_var.set(self.hint_text)
        status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(side=tk.TOP, fill=tk.X, pady=int(5*self.sf))

        # 表格框架
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # 创建Treeview表格
        style = ttk.Style()
        style.configure("PViewStyle.Treeview",
                        headerheight=int(20*self.sf),
                        rowheight=int(20*self.sf))
        self.tree = ttk.Treeview(tree_frame, columns=('列1', '列2'), 
                                 style="PViewStyle.Treeview",
                                 show='headings', selectmode='browse')
        self.tree.heading('列1', text='WiFi名称')
        self.tree.heading('列2', text='WiFi密码')
        self.tree.column('列1', width=200, anchor=tk.W)
        self.tree.column('列2', width=200, anchor=tk.W)

        # 滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件
        self.tree.bind("<Double-1>", self.copy_password_by_double_click)

        # 右键菜单
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="复制wifi名称+密码", command=self.callback_copy)
        self.menu.add_command(label="删除此wifi", command=self.callback_delete)
        self.tree.bind("<Button-3>", self.popup)

    def fetch_password(self, wifi) -> tuple[str, str] | None:
        """获取单个WiFi的密码"""
        results = subprocess.run(
            ['netsh', 'wlan', 'show', 'profile', wifi, 'key=clear'],
            capture_output=True
        ).stdout.decode('utf-8', errors='ignore').split('\n')
        
        password_lines = [line for line in results if "关键内容" in line or "Key Content" in line]

        if password_lines:
            try:
                password = password_lines[0].split(':')[1][1:-1]
            except:
                password = "无法解析密码"
            return (wifi, password)
        return None

    def get_current_wifi(self) -> str | None:
        """获取当前连接的WiFi名称"""
        try:
            results = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True
            ).stdout.decode('utf-8', errors='ignore').split('\n')
            return [line for line in results if "SSID" in line][0].split(':')[1][1:-1]
        except:
            return None

    def get_wifi_info(self) -> list[tuple[str, str]] | None:
        """获取本机连接过的WiFi名称和密码（过滤无密码WiFi）"""
        try:
            output = subprocess.run(
                ['netsh', 'wlan', 'show', 'profiles'],
                capture_output=True
            ).stdout.decode('utf-8', errors='ignore').split('\n')
            
            wifis = [line.split(':')[1][1:-1] for line in output if "所有用户配置文件" in line]

            with ThreadPoolExecutor() as executor:
                wifi_data = [item for item in executor.map(self.fetch_password, wifis) if item is not None]
            
            return wifi_data
        except Exception as e:
            messagebox.showerror("错误", f"获取WiFi信息失败：{str(e)}")
            return None

    def delete_wifi_profile(self, wifi_name: str) -> str:
        """删除指定WiFi配置文件"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'delete', 'profile', f'name={wifi_name}'],
                capture_output=True
            ).stdout.decode('utf-8', errors='ignore')
            return result
        except:
            return f"删除WiFi '{wifi_name}' 失败"

    def load_wifi_info(self):
        """加载WiFi信息到表格"""
        try:
            current_wifi_name = self.get_current_wifi()
            current_wifi = self.fetch_password(current_wifi_name) if current_wifi_name else None
            self.wifi_data = self.get_wifi_info() or []
            
            # 排序并置顶当前连接的WiFi
            self.wifi_data.sort(key=lambda x: x[0].lower())
            if current_wifi in self.wifi_data:
                current_wifi_new = (current_wifi[0] + "【当前WiFi】", current_wifi[1])
                self.wifi_data = [current_wifi_new] + [x for x in self.wifi_data if x != current_wifi]

            # 加载数据到表格
            for name, pwd in self.wifi_data:
                self.tree.insert('', 'end', values=(name, pwd))
        except Exception as e:
            messagebox.showerror("错误", f"加载WiFi信息失败：{str(e)}")
        finally:
            self.status_var.set(self.hint_text)

    def search_wifi(self, event=None):
        """根据WiFi名称查询"""
        filter_keyword = self.entry_search.get()

        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 显示过滤结果
        if filter_keyword in ("输入WiFi名称进行搜索", ""):
            for name, pwd in self.wifi_data:
                self.tree.insert('', 'end', values=(name, pwd))
        else:
            filter_keyword = filter_keyword.lower().strip()
            for name, pwd in self.wifi_data:
                if filter_keyword in name.lower():
                    self.tree.insert('', 'end', values=(name, pwd))

    def copy_password_by_double_click(self, event=None):
        """双击复制选中WiFi的密码"""
        selected = self.tree.selection()
        if selected:
            wifi_name, password = self.tree.item(selected[0], 'values')
            self.root.clipboard_clear()
            self.root.clipboard_append(password)
            self.status_var.set(f"已复制 '{wifi_name}' 的密码到剪贴板")
            self.root.after(2000, lambda: self.status_var.set(self.hint_text))

    def on_search_focus_in(self, event=None):
        """搜索框获得焦点时"""
        if self.entry_search.get() == "输入WiFi名称进行搜索":
            self.entry_search.delete(0, tk.END)
            self.entry_search.configure(foreground='black')

    def on_search_focus_out(self, event=None):
        """搜索框失去焦点时"""
        if self.entry_search.get() == "":
            self.entry_search.insert(0, "输入WiFi名称进行搜索")
            self.entry_search.configure(foreground='grey')

    def callback_copy(self):
        """复制密码和名称"""
        selected = self.tree.selection()
        if selected:
            wifi_name, password = self.tree.item(selected[0], 'values')
            self.root.clipboard_clear()
            self.root.clipboard_append(f"WiFi名称：{wifi_name}\nWiFi密码：{password}")
            self.status_var.set(f"已复制 '{wifi_name}' 的密码和名称到剪贴板")
            self.root.after(2000, lambda: self.status_var.set(self.hint_text))

    def callback_delete(self):
        """删除选中WiFi"""
        selected = self.tree.selection()
        if selected:
            selected_item = selected[0]
            wifi_name = self.tree.item(selected_item, 'values')[0].replace("【当前连接的WiFi】", "")
            result = self.delete_wifi_profile(wifi_name)
            if "删除" in result or "deleted" in result.lower():
                self.tree.delete(selected_item)
                self.status_var.set(f"已删除WiFi '{wifi_name}' 的配置文件")
                self.root.after(2000, lambda: self.status_var.set(self.hint_text))
            else:
                messagebox.showerror("删除失败", f"删除WiFi '{wifi_name}' 的配置文件失败：{result}")

    def popup(self, event):
        """右键菜单"""
        self.menu.post(event.x_root, event.y_root)

if __name__ == "__main__":
    root = tk.Tk()
    app = WiFiViewer(root)
    root.mainloop()