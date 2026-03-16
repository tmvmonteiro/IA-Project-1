import tkinter as tk

class Window:
    def __init__(self, on_click_callback):
        self.root = tk.Tk()
        self.root.title("Lights Out")
        self.root.resizable(False, False)
        
        self.on_click_callback = on_click_callback # Function passed from main
        self.state = "game"
        
        self.container = tk.Frame(self.root)
        self.container.pack(padx=10, pady=10)

    def draw(self, matrix):
        """
        Takes a matrix and renders it.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

        if self.state == "game":
            for r in range(matrix.shape[0]):
                for c in range(matrix.shape[1]):
                    color = "black" if matrix[r, c] == 1 else "white"
                    btn = tk.Button(
                        self.container,
                        width=4,
                        height=2,
                        bg=color,
                        # When clicked, call the callback provided by main
                        command=lambda row=r, col=c: self.on_click_callback(row, col)
                    )
                    btn.grid(row=r, column=c)

    def run(self):
        self.root.mainloop()