import tkinter as tk
from tkinter import filedialog, colorchooser, simpledialog, ttk
from PIL import ImageGrab, ImageTk, Image, ImageDraw, ImageFont
import pyautogui
import traceback
import sys
import os

class ScreenshotToolPro:
    def __init__(self, master):
        self.master = master
        self.master.title("截屏工具 Pro")
        self.master.geometry("1000x600")
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.setup_ui()
        
        self.screenshots = []
        self.current_index = -1
        self.start_x = None
        self.start_y = None
        self.current_tool = "select"
        self.current_color = "#FF0000"
        self.draw_objects = []
        self.undo_stack = []
        self.redo_stack = []
        self.current_screenshot = None  # 添加这行来跟踪当前截图
        self.selected_object = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.temp_object = None
        self.font = self.get_font()

    def setup_ui(self):
        self.toolbar = ttk.Frame(self.master, padding="5 5 5 5")
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.capture_button = ttk.Button(self.toolbar, text="Capture", command=self.capture_screen, style='Accent.TButton')
        self.capture_button.pack(side=tk.LEFT, padx=5)

        self.new_capture_button = ttk.Button(self.toolbar, text="New Capture", command=self.new_capture, style='Accent.TButton')
        self.new_capture_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(self.toolbar, text="Save All", command=self.save_all_screenshots, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.tool_var = tk.StringVar(value="select")
        tools = [("Select", "select"), ("Arrow", "arrow"), ("Rectangle", "rectangle"), ("Text", "text")]
        for text, mode in tools:
            ttk.Radiobutton(self.toolbar, text=text, variable=self.tool_var, value=mode, command=self.change_tool).pack(side=tk.LEFT, padx=5)

        self.color_button = ttk.Button(self.toolbar, text="Color", command=self.choose_color)
        self.color_button.pack(side=tk.LEFT, padx=5)

        self.undo_button = ttk.Button(self.toolbar, text="Undo", command=self.undo, state=tk.DISABLED)
        self.undo_button.pack(side=tk.LEFT, padx=5)

        self.redo_button = ttk.Button(self.toolbar, text="Redo", command=self.redo, state=tk.DISABLED)
        self.redo_button.pack(side=tk.LEFT, padx=5)

        # 主界面分为左右两部分
        self.main_paned = ttk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧为截图显示区域
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=3)

        self.canvas = tk.Canvas(self.left_frame, bg='white')
        
        # 添加垂直滚动条
        self.v_scrollbar = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加水平滚动条
        self.h_scrollbar = ttk.Scrollbar(self.left_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 配置画布使用滚动条
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # 绑定鼠标滚轮事件
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        # 右侧为缩略图列表
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=1)

        self.thumbnails_canvas = tk.Canvas(self.right_frame)
        self.thumbnails_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.thumbnails_scrollbar = ttk.Scrollbar(self.right_frame, orient=tk.VERTICAL, command=self.thumbnails_canvas.yview)
        self.thumbnails_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.thumbnails_canvas.configure(yscrollcommand=self.thumbnails_scrollbar.set)

        self.thumbnails_frame = ttk.Frame(self.thumbnails_canvas)
        self.thumbnails_canvas.create_window((0, 0), window=self.thumbnails_frame, anchor='nw')

        self.thumbnails_frame.bind("<Configure>", lambda e: self.thumbnails_canvas.configure(scrollregion=self.thumbnails_canvas.bbox("all")))

        self.master.bind("<Control-z>", lambda e: self.undo())
        self.master.bind("<Control-y>", lambda e: self.redo())

        # 设置样式
        self.style.configure('Accent.TButton', foreground='white', background='#007bff')
        self.style.map('Accent.TButton', background=[('active', '#0056b3')])

    def capture_screen(self):
        if not self.screenshots:
            self.master.iconify()
            self.master.after(100, self._perform_capture)
        else:
            self.display_merged_screenshots()

    def new_capture(self):
        if self.current_screenshot:
            self.screenshots.append(self.current_screenshot)
            self.add_thumbnail(self.current_screenshot, len(self.screenshots) - 1)
        self.current_screenshot = None
        self.master.iconify()
        self.master.after(100, self._perform_capture)

    def _perform_capture(self):
        self.master.withdraw()
        self.selection_window = tk.Toplevel(self.master)
        self.selection_window.attributes('-fullscreen', True, '-alpha', 0.3, '-topmost', True)
        self.selection_window.configure(cursor="cross")

        self.selection_canvas = tk.Canvas(self.selection_window, highlightthickness=0)
        self.selection_canvas.pack(fill=tk.BOTH, expand=True)

        self.selection_window.bind('<ButtonPress-1>', self.on_selection_press)
        self.selection_window.bind('<B1-Motion>', self.on_selection_drag)
        self.selection_window.bind('<ButtonRelease-1>', self.on_selection_release)

    def on_selection_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.selection_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_selection_drag(self, event):
        cur_x = event.x
        cur_y = event.y
        self.selection_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_selection_release(self, event):
        end_x = event.x
        end_y = event.y
        
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        screen_x1 = self.selection_window.winfo_rootx() + x1
        screen_y1 = self.selection_window.winfo_rooty() + y1
        screen_x2 = self.selection_window.winfo_rootx() + x2
        screen_y2 = self.selection_window.winfo_rooty() + y2
        
        self.selection_window.destroy()
        
        self.current_screenshot = ImageGrab.grab(bbox=(screen_x1, screen_y1, screen_x2, screen_y2))
        self.master.deiconify()
        self.display_merged_screenshots()
        self.update_thumbnail()
        self.save_button['state'] = tk.NORMAL
        self.new_capture_button['state'] = tk.NORMAL

    def display_merged_screenshots(self):
        self.canvas.delete("all")
        all_screenshots = self.screenshots + ([self.current_screenshot] if self.current_screenshot else [])
        
        if not all_screenshots:
            return

        total_height = sum(img.height for img in all_screenshots)
        max_width = max(img.width for img in all_screenshots)
        merged_image = Image.new('RGB', (max_width, total_height))

        y_offset = 0
        for img in all_screenshots:
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height

        photo = ImageTk.PhotoImage(merged_image)
        self.canvas.config(width=photo.width(), height=photo.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo, tags="merged_screenshot")
        self.canvas.image = photo
        
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.redraw_all_objects()

    def redraw_all_objects(self):
        for obj in self.draw_objects:
            self.redraw_object(obj)

    def redraw_object(self, obj):
        obj_type, _, index, coords, color, text = obj
        y_offset = sum(img.height for img in self.screenshots[:index])
        adjusted_coords = [coord + y_offset if i % 2 == 1 else coord for i, coord in enumerate(coords)]
        if obj_type == "arrow":
            self.canvas.create_line(adjusted_coords, arrow=tk.LAST, fill=color)
        elif obj_type == "rectangle":
            self.canvas.create_rectangle(adjusted_coords, outline=color)
        elif obj_type == "text":
            self.canvas.create_text(adjusted_coords, text=text, fill=color, font=("SimSun", 16))

    def update_thumbnail(self):
        # 清除所有现有的缩略图
        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()

        # 显示所有已保存的截图的缩略图
        for i, screenshot in enumerate(self.screenshots):
            self.add_thumbnail(screenshot, i)

        # 显示当前截图的缩略图（如果有）
        if self.current_screenshot:
            self.add_thumbnail(self.current_screenshot, len(self.screenshots))

    def add_thumbnail(self, screenshot, index):
        frame = ttk.Frame(self.thumbnails_frame)
        frame.pack(pady=5, padx=5, fill=tk.X)

        thumbnail = screenshot.copy()
        thumbnail.thumbnail((100, 100))
        photo = ImageTk.PhotoImage(thumbnail)

        label = ttk.Label(frame, image=photo)
        label.image = photo
        label.pack(side=tk.LEFT)
        
        label.bind("<Button-1>", lambda e, idx=index: self.select_screenshot(idx))

        delete_button = ttk.Button(frame, text="X", width=2, command=lambda idx=index: self.delete_screenshot(idx))
        delete_button.pack(side=tk.RIGHT)

        self.thumbnails_canvas.configure(scrollregion=self.thumbnails_canvas.bbox("all"))

    def select_screenshot(self, index):
        self.current_index = index
        self.display_merged_screenshots()
        
        screenshot_tag = f"screenshot_{index}"
        bbox = self.canvas.bbox(screenshot_tag)
        if bbox:
            y_position = bbox[1] / self.canvas.winfo_height()
            self.canvas.yview_moveto(y_position)
        else:
            print(f"Warning: Screenshot {index} not found on canvas")

        self.draw_objects = [obj for obj in self.draw_objects if obj[2] == index]
        self.undo_stack = []
        self.redo_stack = []
        self.update_undo_redo_buttons()

    def delete_screenshot(self, index):
        if index < len(self.screenshots):
            del self.screenshots[index]
        elif index == len(self.screenshots) and self.current_screenshot:
            self.current_screenshot = None
        
        self.update_thumbnail()
        self.display_merged_screenshots()
        self.save_button['state'] = tk.NORMAL if self.screenshots or self.current_screenshot else tk.DISABLED

    def save_all_screenshots(self):
        all_screenshots = self.screenshots + ([self.current_screenshot] if self.current_screenshot else [])
        if not all_screenshots:
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".jpg", 
                                                 filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png")])
        if not file_path:
            return

        merged_image = self.create_merged_image(all_screenshots)
        self.save_image(merged_image, file_path)
        print(f"Screenshots saved to {file_path}")

    def create_merged_image(self, screenshots):
        total_height = sum(img.height for img in screenshots)
        max_width = max(img.width for img in screenshots)
        merged_image = Image.new('RGB', (max_width, total_height))

        y_offset = 0
        for img in screenshots:
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height

        draw = ImageDraw.Draw(merged_image)
        for obj in self.draw_objects:
            self.apply_draw_object(draw, obj, screenshots)

        return merged_image

    def save_image(self, image, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        save_params = {'optimize': True}
        if file_extension in ['.jpg', '.jpeg']:
            save_params['quality'] = 90
        image.save(file_path, **save_params)

    def apply_draw_object(self, draw, obj, all_screenshots):
        obj_type, _, index, coords, color, text = obj
        total_height = sum(img.height for img in all_screenshots[:index])
        
        if obj_type in ["arrow", "rectangle"]:
            coords = [coord + (total_height if i % 2 else 0) for i, coord in enumerate(coords)]
        
        if obj_type == "arrow":
            start_x, start_y, end_x, end_y = coords
            draw.line((start_x, start_y, end_x, end_y), fill=color, width=2)
            arrow_head = [(end_x, end_y), 
                          (end_x-10, end_y-10), 
                          (end_x-10, end_y+10)]
            draw.polygon(arrow_head, fill=color)
        elif obj_type == "rectangle":
            draw.rectangle(coords, outline=color, width=2)
        elif obj_type == "text":
            x, y = coords
            y += total_height
            draw.text((x, y), text, fill=color, font=self.font)

    def change_tool(self):
        self.current_tool = self.tool_var.get()

    def choose_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.current_color = color

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.current_tool == "select":
            self.select_object(event)
        elif self.current_tool in ["arrow", "rectangle"]:
            self.temp_object = None

    def on_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.current_tool == "select" and self.selected_object is not None:
            self.move_selected_object(cur_x, cur_y)
        elif self.current_tool in ["arrow", "rectangle"]:
            self.draw_shape(cur_x, cur_y)

    def draw_shape(self, x, y):
        if self.temp_object:
            self.canvas.delete(self.temp_object)
        if self.current_tool == "arrow":
            self.temp_object = self.canvas.create_line(self.start_x, self.start_y, x, y, arrow=tk.LAST, fill=self.current_color)
        elif self.current_tool == "rectangle":
            x0, y0, x1, y1 = min(self.start_x, x), min(self.start_y, y), max(self.start_x, x), max(self.start_y, y)
            self.temp_object = self.canvas.create_rectangle(x0, y0, x1, y1, outline=self.current_color)

    def on_release(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        if self.current_tool == "arrow":
            self.finalize_arrow(cur_x, cur_y)
        elif self.current_tool == "rectangle":
            self.finalize_rectangle(cur_x, cur_y)
        elif self.current_tool == "text":
            self.add_text(cur_x, cur_y)
        elif self.current_tool == "select":
            self.selected_object = None
        self.temp_object = None

    def finalize_arrow(self, x, y):
        if self.temp_object:
            self.canvas.delete(self.temp_object)
        self.draw_objects.append(("arrow", None, self.current_index, (self.start_x, self.start_y, x, y), self.current_color, None))
        self.redraw_merged_screenshot()

    def finalize_rectangle(self, x, y):
        if self.temp_object:
            self.canvas.delete(self.temp_object)
        x0, y0 = self.start_x, self.start_y
        x1, y1 = x, y
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        self.draw_objects.append(("rectangle", None, self.current_index, (x0, y0, x1, y1), self.current_color, None))
        self.redraw_merged_screenshot()

    def redraw_merged_screenshot(self):
        self.canvas.delete("all")
        all_screenshots = self.screenshots + ([self.current_screenshot] if self.current_screenshot else [])
        
        if not all_screenshots:
            return

        total_height = sum(img.height for img in all_screenshots)
        max_width = max(img.width for img in all_screenshots)
        merged_image = Image.new('RGB', (max_width, total_height))

        y_offset = 0
        for img in all_screenshots:
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height

        photo = ImageTk.PhotoImage(merged_image)
        self.canvas.config(width=photo.width(), height=photo.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo, tags="merged_screenshot")
        self.canvas.image = photo
        
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.redraw_all_objects()

    def add_text(self, x, y):
        text = simpledialog.askstring("Input", "Enter text:")
        if text:
            coords = (x, y)
            self.draw_objects.append(("text", None, self.current_index, coords, self.current_color, text))
            self.redraw_object(self.draw_objects[-1])

    def undo(self):
        if self.draw_objects:
            self.redo_stack.append(self.draw_objects.copy())
            last_state = self.undo_stack.pop()
            for obj in self.draw_objects[len(last_state):]:
                self.canvas.delete(obj[1])
            self.draw_objects = last_state
            self.update_undo_redo_buttons()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.draw_objects.copy())
            next_state = self.redo_stack.pop()
            for obj in next_state[len(self.draw_objects):]:
                if obj[0] == "arrow":
                    coords = self.canvas.coords(obj[1])
                    arrow = self.canvas.create_line(coords, arrow=tk.LAST, fill=self.current_color)
                    self.draw_objects.append(("arrow", arrow, obj[2]))
                elif obj[0] == "rectangle":
                    coords = self.canvas.coords(obj[1])
                    rect = self.canvas.create_rectangle(coords, outline=self.current_color)
                    self.draw_objects.append(("rectangle", rect, obj[2]))
                elif obj[0] == "text":
                    coords = self.canvas.coords(obj[1])
                    text = self.canvas.itemcget(obj[1], "text")
                    t = self.canvas.create_text(coords, text=text, fill=self.current_color)
                    self.draw_objects.append(("text", t, obj[2]))
            self.update_undo_redo_buttons()

    def update_undo_redo_buttons(self):
        self.undo_button['state'] = tk.NORMAL if self.undo_stack else tk.DISABLED
        self.redo_button['state'] = tk.NORMAL if self.redo_stack else tk.DISABLED

    def select_object(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for i, obj in reversed(list(enumerate(self.draw_objects))):
            obj_type, _, index, coords, color, text = obj
            if obj_type == "arrow":
                if self.point_on_line(x, y, coords):
                    self.selected_object = i
                    self.drag_start_x = x
                    self.drag_start_y = y
                    return
            elif obj_type == "rectangle":
                if self.point_in_rectangle(x, y, coords):
                    self.selected_object = i
                    self.drag_start_x = x
                    self.drag_start_y = y
                    return
            elif obj_type == "text":
                if self.point_near_text(x, y, coords):
                    self.selected_object = i
                    self.drag_start_x = x
                    self.drag_start_y = y
                    return
        self.selected_object = None

    def move_selected_object(self, cur_x, cur_y):
        if self.selected_object is not None:
            dx = cur_x - self.drag_start_x
            dy = cur_y - self.drag_start_y
            obj = self.draw_objects[self.selected_object]
            obj_type, _, index, coords, color, text = obj
            if obj_type == "arrow":
                new_coords = (coords[0] + dx, coords[1] + dy, coords[2] + dx, coords[3] + dy)
            elif obj_type == "rectangle":
                new_coords = (coords[0] + dx, coords[1] + dy, coords[2] + dx, coords[3] + dy)
            elif obj_type == "text":
                new_coords = (coords[0] + dx, coords[1] + dy)
            self.draw_objects[self.selected_object] = (obj_type, None, index, new_coords, color, text)
            self.drag_start_x = cur_x
            self.drag_start_y = cur_y
            self.redraw_merged_screenshot()

    def point_on_line(self, x, y, coords):
        x1, y1, x2, y2 = coords
        distance = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / ((y2 - y1)**2 + (x2 - x1)**2)**0.5
        return distance < 5  # 5 像素的容差

    def point_in_rectangle(self, x, y, coords):
        x1, y1, x2, y2 = coords
        return x1 <= x <= x2 and y1 <= y <= y2

    def point_near_text(self, x, y, coords):
        text_x, text_y = coords
        return abs(x - text_x) < 10 and abs(y - text_y) < 10  # 10 像素的容差

    def get_font(self):
        # 尝试加载支持中文的字体
        font_paths = [
            "C:\\Windows\\Fonts\\simsun.ttc",  # 宋体
            "C:\\Windows\\Fonts\\msyh.ttc",    # 微软雅黑
            "/System/Library/Fonts/PingFang.ttc",  # macOS 上的苹方字体
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"  # Linux 上的 Droid Sans 字体
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, 16)
        # 如果找不到合适的字体，使用默认字体
        return ImageFont.load_default()

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ScreenshotToolPro(root)
        root.mainloop()
    except Exception as e:
        print(f"Unhandled error: {e}")
        traceback.print_exc()