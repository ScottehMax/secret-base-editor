import tkinter as tk


BUTTON_COLORS = {
    "normal": ["#e1e1e1", "#adadad", "#000000"],
    "hover": ["#e5f1fb", "#0078d7", "#000000"],
    "pressed": ["#cce4f7", "#005499", "#000000"],
    "disabled": ["#cccccc", "#bfbfbf", "#6d6d6d"]
}

class CanvasButton(tk.Canvas):
    """A button that can be drawn on a canvas.

    Args:
        parent (tk.Tk): The parent window.
        x (int): The x-coordinate of the button.
        y (int): The y-coordinate of the button.
        size (int): The size of the button.
        color (str): The color of the button.
        btn_type (str): The type of button to create. Either "image" or "text".
        btn_content (str): The content of the button. Either an image path or text.
        command (function): The function to call when the button is clicked.
        **kwargs: Arbitrary keyword arguments.
    """
    def __init__(self, parent, width, height, btn_type, btn_content, command=None, **kwargs):
        super().__init__(parent, width=width, height=height, borderwidth=0, highlightthickness=0, **kwargs)
        self.parent = parent
        self.width = width
        self.height = height
        self.btn_type = btn_type
        self.btn_content = btn_content
        self.command = command

        if self.btn_type == "image":
            self.btn_image = tk.PhotoImage(file=self.btn_content)

        self.command = None
        self.state = "normal"
        self.is_pressed = False
        self.create_button()
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._on_hover)
        self.bind("<Leave>", self._on_hover)
        self.draw()

    def is_hovered(self, event):
        """Check if the mouse is hovering over the button.

        Args:
            event (tk.Event): The event object.

        Returns:
            bool: True if the mouse is hovering over the button, False otherwise.
        """
        x, y = event.x, event.y
        return 0 < x < self.width and 0 < y < self.height

    def _on_press(self, event):
        self.is_pressed = True
        self._on_hover(event)
        self.draw()

    def _on_release(self, event):
        self.is_pressed = False
        self._on_hover(event)

        if self.state != "disabled" and self.command is not None and self.is_hovered(event):
            self.command()

        self.draw()

    def _on_hover(self, event):
        if self.state == "disabled":
            return
        if self.is_hovered(event):
            if self.is_pressed:
                self.state = "pressed"
            else:
                self.state = "hover"
        else:
            if self.is_pressed:
                self.state = "hover"
            else:
                self.state = "normal"
        self.draw()

    def create_button(self):
        """Create the button on the canvas."""
        normal_colors = BUTTON_COLORS["normal"]
        self.rect = self.create_rectangle(0, 0, self.width-1, self.height-1, fill=normal_colors[0], outline=normal_colors[1], tags="button")
        if self.btn_type == "image":
            self.image = self.create_image(self.width / 2, self.height / 2, image=self.btn_image)
        elif self.btn_type == "text":
            self.text = self.create_text(self.width / 2, self.height / 2, text=self.btn_content, fill='black')

    def set_image(self, image_path):
        """Set the image of the button.

        Args:
            image_path (str): The path to the image to set.
        """
        self.btn_image = tk.PhotoImage(file=image_path)
        self.itemconfig(self.image, image=self.btn_image)

    def draw(self):
        """Draw the button based on the current state."""
        colors = BUTTON_COLORS[self.state]
        self.itemconfig(self.rect, fill=colors[0])
        self.itemconfig(self.rect, outline=colors[1])
        if self.btn_type == "text":
            self.itemconfig(self.text, fill=colors[2])


            


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("500x200")

    button = CanvasButton(root, 50, 50, "text", "ok")
    button.pack()

    def disable():
        button.state = "disabled"
        button.draw()

    button.command = disable

    root.mainloop()
