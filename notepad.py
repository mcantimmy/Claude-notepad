import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageDraw, ImageTk
import json
import anthropic
import os
import base64
from io import BytesIO

class InteractiveNotepad:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Notepad")
        self.root.geometry("800x600")  # Set default window size to 800x600 pixels
        self.blocks = []
        self.create_widgets()

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # In the create_widgets method:
        self.root.bind('<MouseWheel>', self.on_mousewheel)       # For Windows
        self.root.bind('<Button-4>', self.on_mousewheel)         # For Linux
        self.root.bind('<Button-5>', self.on_mousewheel)         # For Linux
        self.root.bind('<Control-MouseWheel>', self.on_zoom)     # Zoom with Ctrl + Mouse Wheel


        self.frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.frame, anchor='nw')

        self.root.bind('<Button-3>', self.show_context_menu)

        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_notepad)
        file_menu.add_command(label="Save", command=self.save_notepad)
        file_menu.add_command(label="Load", command=self.load_notepad)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Add Text Block", command=self.add_text_block)
        edit_menu.add_command(label="Add Drawing Block", command=self.add_drawing_block)
        edit_menu.add_command(label="Add Claude API Block", command=self.add_claude_block)

        self.status_bar = ttk.Label(self.root, text="Ready", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    # Updated on_mousewheel method:
    def on_mousewheel(self, event):
        if event.delta:
            # Windows
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            # Linux
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

    # New on_zoom method:
    def on_zoom(self, event):
        scale = 1.001 ** event.delta
        self.canvas.scale("all", event.x, event.y, scale, scale)
        self.on_canvas_configure(event)

    def show_context_menu(self, event):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Add Text Block", command=self.add_text_block)
        context_menu.add_command(label="Add Drawing Block", command=self.add_drawing_block)
        context_menu.add_command(label="Add Claude API Block", command=self.add_claude_block)
        context_menu.tk_popup(event.x_root, event.y_root)

    def add_text_block(self):
        block = TextBlock(self.frame, self)
        self.blocks.append(block)
        self.update_canvas()

    def add_drawing_block(self):
        block = DrawingBlock(self.frame, self)
        self.blocks.append(block)
        self.update_canvas()

    def add_claude_block(self):
        block = ClaudeBlock(self.frame, self)
        self.blocks.append(block)
        self.update_canvas()

    def update_canvas(self):
        self.frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def new_notepad(self):
        if messagebox.askyesno("New Notepad", "Are you sure you want to create a new notepad? Unsaved changes will be lost."):
            for block in self.blocks:
                block.destroy()
            self.blocks.clear()
            self.update_canvas()

    def save_notepad(self):
        data = []
        for block in self.blocks:
            block_data = block.get_data()
            if block_data:
                data.append(block_data)

        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f)
                self.status_bar.config(text=f"Saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    def load_notepad(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                for block in self.blocks:
                    block.destroy()
                self.blocks.clear()

                for block_data in data:
                    if block_data['type'] == 'text':
                        block = TextBlock(self.frame, self)
                        block.set_data(block_data)
                    elif block_data['type'] == 'drawing':
                        block = DrawingBlock(self.frame, self)
                        block.set_data(block_data)
                    elif block_data['type'] == 'claude':
                        block = ClaudeBlock(self.frame, self)
                        block.set_data(block_data)
                    self.blocks.append(block)

                self.update_canvas()
                self.status_bar.config(text=f"Loaded from {file_path}")
            except Exception as e:
                messagebox.showerror("Load Error", str(e))

    def on_closing(self):
        if messagebox.askyesno("Quit", "Do you want to quit?"):
            self.root.quit()

class TextBlock:
    def __init__(self, parent, notepad):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        self.notepad = notepad

        self.text = tk.Text(self.frame, height=5, wrap=tk.WORD)
        self.text.pack(fill=tk.X)

        self.delete_button = ttk.Button(self.frame, text="Delete", command=self.delete)
        self.delete_button.pack(side=tk.RIGHT)

    def get_data(self):
        return {
            'type': 'text',
            'content': self.text.get('1.0', tk.END)
        }

    def set_data(self, data):
        self.text.delete('1.0', tk.END)
        self.text.insert('1.0', data['content'])

    def delete(self):
        self.notepad.blocks.remove(self)
        self.frame.destroy()
        self.notepad.update_canvas()

    def destroy(self):
        self.frame.destroy()

class DrawingBlock:
    def __init__(self, parent, notepad):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        self.notepad = notepad

        self.canvas = tk.Canvas(self.frame, width=400, height=200, bg='white')
        self.canvas.pack()

        self.image = Image.new('RGB', (400, 200), 'white')
        self.draw = ImageDraw.Draw(self.image)

        self.canvas.bind('<B1-Motion>', self.paint)
        self.canvas.bind('<ButtonRelease-1>', self.reset)

        self.delete_button = ttk.Button(self.frame, text="Delete", command=self.delete)
        self.delete_button.pack(side=tk.RIGHT)

        self.clear_button = ttk.Button(self.frame, text="Clear", command=self.clear)
        self.clear_button.pack(side=tk.RIGHT)

        self.last_x = None
        self.last_y = None

        # Create an initial blank image on the canvas
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

    def paint(self, event):
        if self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, fill='black', width=2, smooth=tk.TRUE, splinesteps=36)
            self.draw.line([self.last_x, self.last_y, event.x, event.y], fill='black', width=2)
        self.last_x = event.x
        self.last_y = event.y
        self.update_image()

    def reset(self, event):
        self.last_x = None
        self.last_y = None

    def clear(self):
        self.canvas.delete('all')
        self.image = Image.new('RGB', (400, 200), 'white')
        self.draw = ImageDraw.Draw(self.image)
        self.update_image()

    def update_image(self):
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

    def get_data(self):
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        return {
            'type': 'drawing',
            'content': base64.b64encode(buffer.getvalue()).decode()
        }

    def set_data(self, data):
        image_data = base64.b64decode(data['content'])
        self.image = Image.open(BytesIO(image_data))
        self.draw = ImageDraw.Draw(self.image)
        self.update_image()

    def delete(self):
        self.notepad.blocks.remove(self)
        self.frame.destroy()
        self.notepad.update_canvas()

    def destroy(self):
        self.frame.destroy()

class ClaudeBlock:
    def __init__(self, parent, notepad):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        self.notepad = notepad

        self.prompt_entry = ttk.Entry(self.frame)
        self.prompt_entry.pack(fill=tk.X)

        self.submit_button = ttk.Button(self.frame, text="Submit", command=self.submit_prompt)
        self.submit_button.pack()

        self.response_text = tk.Text(self.frame, height=10, wrap=tk.WORD)
        self.response_text.pack(fill=tk.X)

        self.delete_button = ttk.Button(self.frame, text="Delete", command=self.delete)
        self.delete_button.pack(side=tk.RIGHT)

    def submit_prompt(self):
        prompt = self.prompt_entry.get()
        if prompt:
            try:
                api_key = os.environ.get('ANTHROPIC_API_KEY')
                if not api_key:
                    raise ValueError("API key not found. Please set the ANTHROPIC_API_KEY environment variable.")
                
                client = anthropic.Client(api_key=api_key)
                response = client.messages.create(
                    model="claude-3-opus-20240229",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000
                )
                self.response_text.delete('1.0', tk.END)
                self.response_text.insert('1.0', response.content[0].text)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def get_data(self):
        return {
            'type': 'claude',
            'prompt': self.prompt_entry.get(),
            'response': self.response_text.get('1.0', tk.END)
        }

    def set_data(self, data):
        self.prompt_entry.delete(0, tk.END)
        self.prompt_entry.insert(0, data['prompt'])
        self.response_text.delete('1.0', tk.END)
        self.response_text.insert('1.0', data['response'])

    def delete(self):
        self.notepad.blocks.remove(self)
        self.frame.destroy()
        self.notepad.update_canvas()

    def destroy(self):
        self.frame.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveNotepad(root)
    root.mainloop()