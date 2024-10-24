import streamlit as st
from PIL import Image, ImageDraw
import json
import anthropic
import os
import base64
from io import BytesIO

class InteractiveNotepad:
    def __init__(self):
        self.blocks = []
        self.create_widgets()

    def create_widgets(self):
        st.title("Interactive Notepad")
        
        st.sidebar.title("Add Blocks")
        if st.sidebar.button("Add Text Block"):
            self.add_text_block()
        if st.sidebar.button("Add Drawing Block"):
            self.add_drawing_block()
        if st.sidebar.button("Add Claude API Block"):
            self.add_claude_block()
        
        if st.sidebar.button("Save Notepad"):
            self.save_notepad()
        if st.sidebar.button("Load Notepad"):
            self.load_notepad()

        for block in self.blocks:
            block.render()

    def add_text_block(self):
        self.blocks.append(TextBlock(self))

    def add_drawing_block(self):
        self.blocks.append(DrawingBlock(self))

    def add_claude_block(self):
        self.blocks.append(ClaudeBlock(self))

    def save_notepad(self):
        data = [block.get_data() for block in self.blocks if block.get_data()]
        json_data = json.dumps(data)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name="notepad.json",
            mime="application/json"
        )

    def load_notepad(self):
        uploaded_file = st.file_uploader("Choose a JSON file", type="json")
        if uploaded_file is not None:
            data = json.load(uploaded_file)
            self.blocks = []
            for block_data in data:
                if block_data['type'] == 'text':
                    block = TextBlock(self)
                elif block_data['type'] == 'drawing':
                    block = DrawingBlock(self)
                elif block_data['type'] == 'claude':
                    block = ClaudeBlock(self)
                block.set_data(block_data)
                self.blocks.append(block)
            st.experimental_rerun()

class TextBlock:
    def __init__(self, notepad):
        self.notepad = notepad
        self.content = ""

    def render(self):
        self.content = st.text_area("Text Block", value=self.content, height=150)
        if st.button("Delete Text Block", key=f"delete_text_{id(self)}"):
            self.notepad.blocks.remove(self)
            st.experimental_rerun()

    def get_data(self):
        return {
            'type': 'text',
            'content': self.content
        }

    def set_data(self, data):
        self.content = data['content']

class DrawingBlock:
    def __init__(self, notepad):
        self.notepad = notepad
        self.image = Image.new('RGB', (400, 200), '#3e3e3e')
        self.draw = ImageDraw.Draw(self.image)

    def render(self):
        canvas = st.empty()
        canvas.image(self.image, use_column_width=True)
        
        # Note: Streamlit doesn't support real-time drawing.
        # We'll use a button to simulate drawing a line for demonstration.
        if st.button("Draw Line", key=f"draw_{id(self)}"):
            self.draw.line([0, 0, 400, 200], fill='#ffffff', width=2)
            canvas.image(self.image, use_column_width=True)
        
        if st.button("Clear", key=f"clear_{id(self)}"):
            self.image = Image.new('RGB', (400, 200), '#3e3e3e')
            self.draw = ImageDraw.Draw(self.image)
            canvas.image(self.image, use_column_width=True)
        
        if st.button("Delete Drawing Block", key=f"delete_drawing_{id(self)}"):
            self.notepad.blocks.remove(self)
            st.experimental_rerun()

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

class ClaudeBlock:
    def __init__(self, notepad):
        self.notepad = notepad
        self.prompt = ""
        self.response = ""

    def render(self):
        self.prompt = st.text_input("Enter prompt", value=self.prompt)
        if st.button("Submit", key=f"submit_{id(self)}"):
            self.submit_prompt()
        st.text_area("Response", value=self.response, height=150)
        if st.button("Delete Claude Block", key=f"delete_claude_{id(self)}"):
            self.notepad.blocks.remove(self)
            st.experimental_rerun()

    def submit_prompt(self):
        try:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("API key not found. Please set the ANTHROPIC_API_KEY environment variable.")
            
            client = anthropic.Client(api_key=api_key)
            response = client.messages.create(
                model="claude-3-opus-20240229",
                messages=[{"role": "user", "content": self.prompt}],
                max_tokens=1000
            )
            self.response = response.content[0].text
        except Exception as e:
            st.error(f"Error: {str(e)}")

    def get_data(self):
        return {
            'type': 'claude',
            'prompt': self.prompt,
            'response': self.response
        }

    def set_data(self, data):
        self.prompt = data['prompt']
        self.response = data['response']

if __name__ == "__main__":
    app = InteractiveNotepad()