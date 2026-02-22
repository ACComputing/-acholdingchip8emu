#!/usr/bin/env python3
"""
Cat's Chip 8 Emu 0.1
[C] AC HOLDINGS 1999-2026
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import time
import random
import array

# Chip-8 specification constants
SCREEN_WIDTH = 64
SCREEN_HEIGHT = 32
PIXEL_SIZE = 10          # scale factor for display
MEMORY_SIZE = 4096
PROGRAM_START = 0x200
NUM_REGS = 16
STACK_SIZE = 16
FONTSET = [
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80   # F
]

class Chip8:
    def __init__(self):
        self.memory = array.array('B', [0]) * MEMORY_SIZE
        self.V = [0] * NUM_REGS          # general purpose registers
        self.I = 0                        # index register
        self.pc = PROGRAM_START            # program counter
        self.stack = [0] * STACK_SIZE
        self.sp = -1                       # stack pointer
        self.delay_timer = 0
        self.sound_timer = 0
        self.display = [[0] * SCREEN_WIDTH for _ in range(SCREEN_HEIGHT)]
        self.keys = [0] * 16               # key states (0=up, 1=down)
        self.draw_flag = False              # set when screen needs redraw
        self.halted = False                  # for debugging, not used here

        # Load fontset into memory (0x000-0x1FF is interpreter area)
        for i, byte in enumerate(FONTSET):
            self.memory[i] = byte

    def load_rom(self, rom_data):
        """Load binary ROM data into memory starting at 0x200."""
        for i, byte in enumerate(rom_data):
            self.memory[PROGRAM_START + i] = byte
        self.pc = PROGRAM_START

    def emulate_cycle(self):
        """Execute one Chip-8 instruction."""
        # Fetch opcode (two bytes)
        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2

        # Decode and execute
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F
        nn = opcode & 0x00FF
        nnn = opcode & 0x0FFF

        if opcode == 0x00E0:  # CLS
            self.display = [[0] * SCREEN_WIDTH for _ in range(SCREEN_HEIGHT)]
            self.draw_flag = True
        elif opcode == 0x00EE:  # RET
            self.sp -= 1
            self.pc = self.stack[self.sp + 1]
        elif (opcode & 0xF000) == 0x1000:  # JP addr
            self.pc = nnn
        elif (opcode & 0xF000) == 0x2000:  # CALL addr
            self.sp += 1
            self.stack[self.sp] = self.pc
            self.pc = nnn
        elif (opcode & 0xF000) == 0x3000:  # SE Vx, byte
            if self.V[x] == nn:
                self.pc += 2
        elif (opcode & 0xF000) == 0x4000:  # SNE Vx, byte
            if self.V[x] != nn:
                self.pc += 2
        elif (opcode & 0xF000) == 0x5000 and (opcode & 0x000F) == 0x0:  # SE Vx, Vy
            if self.V[x] == self.V[y]:
                self.pc += 2
        elif (opcode & 0xF000) == 0x6000:  # LD Vx, byte
            self.V[x] = nn
        elif (opcode & 0xF000) == 0x7000:  # ADD Vx, byte
            self.V[x] = (self.V[x] + nn) & 0xFF
        elif (opcode & 0xF000) == 0x8000:
            if (opcode & 0x000F) == 0x0:  # LD Vx, Vy
                self.V[x] = self.V[y]
            elif (opcode & 0x000F) == 0x1:  # OR Vx, Vy
                self.V[x] |= self.V[y]
            elif (opcode & 0x000F) == 0x2:  # AND Vx, Vy
                self.V[x] &= self.V[y]
            elif (opcode & 0x000F) == 0x3:  # XOR Vx, Vy
                self.V[x] ^= self.V[y]
            elif (opcode & 0x000F) == 0x4:  # ADD Vx, Vy (with carry)
                total = self.V[x] + self.V[y]
                self.V[0xF] = 1 if total > 0xFF else 0
                self.V[x] = total & 0xFF
            elif (opcode & 0x000F) == 0x5:  # SUB Vx, Vy
                self.V[0xF] = 1 if self.V[x] > self.V[y] else 0
                self.V[x] = (self.V[x] - self.V[y]) & 0xFF
            elif (opcode & 0x000F) == 0x6:  # SHR Vx {, Vy}
                # Note: Vy is used but often ignored; most implementations do Vx >>= 1, VF = old LSB
                lsb = self.V[x] & 0x1
                self.V[x] >>= 1
                self.V[0xF] = lsb
            elif (opcode & 0x000F) == 0x7:  # SUBN Vx, Vy
                self.V[0xF] = 1 if self.V[y] > self.V[x] else 0
                self.V[x] = (self.V[y] - self.V[x]) & 0xFF
            elif (opcode & 0x000F) == 0xE:  # SHL Vx {, Vy}
                msb = (self.V[x] & 0x80) >> 7
                self.V[x] = (self.V[x] << 1) & 0xFF
                self.V[0xF] = msb
        elif (opcode & 0xF000) == 0x9000 and (opcode & 0x000F) == 0x0:  # SNE Vx, Vy
            if self.V[x] != self.V[y]:
                self.pc += 2
        elif (opcode & 0xF000) == 0xA000:  # LD I, addr
            self.I = nnn
        elif (opcode & 0xF000) == 0xB000:  # JP V0, addr
            self.pc = nnn + self.V[0]
        elif (opcode & 0xF000) == 0xC000:  # RND Vx, byte
            self.V[x] = random.getrandbits(8) & nn
        elif (opcode & 0xF000) == 0xD000:  # DRW Vx, Vy, nibble
            # Draw sprite
            x_coord = self.V[x] % SCREEN_WIDTH
            y_coord = self.V[y] % SCREEN_HEIGHT
            self.V[0xF] = 0
            for row in range(n):
                if y_coord + row >= SCREEN_HEIGHT:
                    break
                sprite_byte = self.memory[self.I + row]
                for col in range(8):
                    if x_coord + col >= SCREEN_WIDTH:
                        break
                    pixel = (sprite_byte >> (7 - col)) & 0x1
                    if pixel:
                        if self.display[y_coord + row][x_coord + col] == 1:
                            self.V[0xF] = 1
                        self.display[y_coord + row][x_coord + col] ^= 1
            self.draw_flag = True
        elif (opcode & 0xF000) == 0xE000:
            if nn == 0x9E:  # SKP Vx
                if self.keys[self.V[x]]:
                    self.pc += 2
            elif nn == 0xA1:  # SKNP Vx
                if not self.keys[self.V[x]]:
                    self.pc += 2
        elif (opcode & 0xF000) == 0xF000:
            if nn == 0x07:  # LD Vx, DT
                self.V[x] = self.delay_timer
            elif nn == 0x0A:  # LD Vx, K
                # Wait for a key press
                pressed = False
                for i in range(16):
                    if self.keys[i]:
                        self.V[x] = i
                        pressed = True
                        break
                if not pressed:
                    # No key pressed, repeat this instruction
                    self.pc -= 2
            elif nn == 0x15:  # LD DT, Vx
                self.delay_timer = self.V[x]
            elif nn == 0x18:  # LD ST, Vx
                self.sound_timer = self.V[x]
            elif nn == 0x1E:  # ADD I, Vx
                self.I += self.V[x]
                # Chip-8 used to limit I to 12 bits, but modern programs don't rely on it
                self.I &= 0xFFFF  # keep within memory range
            elif nn == 0x29:  # LD F, Vx (sprite location)
                # Each font sprite is 5 bytes starting at font_addr = Vx * 5
                self.I = self.V[x] * 5
            elif nn == 0x33:  # LD B, Vx (BCD)
                self.memory[self.I] = self.V[x] // 100
                self.memory[self.I + 1] = (self.V[x] // 10) % 10
                self.memory[self.I + 2] = self.V[x] % 10
            elif nn == 0x55:  # LD [I], Vx (store registers V0..Vx)
                for i in range(x + 1):
                    self.memory[self.I + i] = self.V[i]
            elif nn == 0x65:  # LD Vx, [I] (load registers V0..Vx)
                for i in range(x + 1):
                    self.V[i] = self.memory[self.I + i]

        # Update timers
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
            # Beep if sound_timer > 0 – can be implemented with a simple beep

    def reset(self):
        """Reset the emulator state."""
        self.__init__()


class Chip8Emu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cat's Chip 8 Emu 0.1 [C] AC HOLDINGS 1999-2026")
        self.resizable(False, False)

        self.chip8 = Chip8()
        self.running = False
        self.emu_speed = 10  # milliseconds between cycles (approx 1000/60 = 16ms for 60Hz, but we run multiple cycles)

        # Build GUI
        self.create_menu()
        self.create_display()
        self.create_statusbar()

        # Bind keyboard
        self.bind("<KeyPress>", self.key_press)
        self.bind("<KeyRelease>", self.key_release)
        # Ensure keys are captured even when focus is on menu
        self.focus_set()

        # Emulation loop control
        self.after_id = None

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load ROM...", command=self.load_rom, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        # Emulation menu
        emu_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Emulation", menu=emu_menu)
        emu_menu.add_command(label="Start", command=self.start_emu, accelerator="F5")
        emu_menu.add_command(label="Pause", command=self.pause_emu, accelerator="F6")
        emu_menu.add_command(label="Reset", command=self.reset_emu, accelerator="F7")

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Keyboard shortcuts
        self.bind_all("<Control-o>", lambda e: self.load_rom())
        self.bind_all("<F5>", lambda e: self.start_emu())
        self.bind_all("<F6>", lambda e: self.pause_emu())
        self.bind_all("<F7>", lambda e: self.reset_emu())

    def create_display(self):
        # Canvas for Chip-8 screen
        self.canvas = tk.Canvas(
            self,
            width=SCREEN_WIDTH * PIXEL_SIZE,
            height=SCREEN_HEIGHT * PIXEL_SIZE,
            bg='black'
        )
        self.canvas.pack(padx=5, pady=5)

        # Pre-create rectangles for faster drawing (optional)
        self.rects = {}
        for y in range(SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                x1 = x * PIXEL_SIZE
                y1 = y * PIXEL_SIZE
                x2 = x1 + PIXEL_SIZE
                y2 = y1 + PIXEL_SIZE
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill='black', outline='')
                self.rects[(x, y)] = rect

    def create_statusbar(self):
        self.status = tk.Label(self, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def draw_screen(self):
        """Update canvas rectangles based on chip8.display."""
        for y in range(SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                color = 'white' if self.chip8.display[y][x] else 'black'
                self.canvas.itemconfig(self.rects[(x, y)], fill=color)
        self.chip8.draw_flag = False

    def key_press(self, event):
        # Map PC keys to Chip-8 keys (0-9, A-F)
        mapping = {
            '1': 0x1, '2': 0x2, '3': 0x3, '4': 0xC,
            'q': 0x4, 'w': 0x5, 'e': 0x6, 'r': 0xD,
            'a': 0x7, 's': 0x8, 'd': 0x9, 'f': 0xE,
            'z': 0xA, 'x': 0x0, 'c': 0xB, 'v': 0xF
        }
        if event.char in mapping:
            self.chip8.keys[mapping[event.char]] = 1

    def key_release(self, event):
        mapping = {
            '1': 0x1, '2': 0x2, '3': 0x3, '4': 0xC,
            'q': 0x4, 'w': 0x5, 'e': 0x6, 'r': 0xD,
            'a': 0x7, 's': 0x8, 'd': 0x9, 'f': 0xE,
            'z': 0xA, 'x': 0x0, 'c': 0xB, 'v': 0xF
        }
        if event.char in mapping:
            self.chip8.keys[mapping[event.char]] = 0

    def load_rom(self):
        filename = filedialog.askopenfilename(
            title="Select a Chip-8 ROM",
            filetypes=[("ROM files", "*.ch8 *.rom *.bin"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, "rb") as f:
                    rom_data = f.read()
                self.chip8.reset()
                self.chip8.load_rom(rom_data)
                self.status.config(text=f"Loaded: {filename}")
                self.draw_screen()
            except Exception as e:
                messagebox.showerror("Error", f"Could not load ROM:\n{e}")

    def start_emu(self):
        if not self.running:
            self.running = True
            self.status.config(text="Running")
            self.emulate()

    def pause_emu(self):
        self.running = False
        self.status.config(text="Paused")
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

    def reset_emu(self):
        self.pause_emu()
        self.chip8.reset()
        self.draw_screen()
        self.status.config(text="Reset")

    def emulate(self):
        if not self.running:
            return

        # Run a few cycles per frame (usually ~10 for Chip-8)
        for _ in range(10):
            self.chip8.emulate_cycle()

        # Redraw if needed
        if self.chip8.draw_flag:
            self.draw_screen()

        self.after_id = self.after(self.emu_speed, self.emulate)

    def show_about(self):
        about_text = (
            "Cat's Chip 8 Emu 0.1\n"
            "[C] AC HOLDINGS 1999-2026\n\n"
            "A simple Chip-8 emulator written in Python with Tkinter.\n"
            "Keyboard layout: 1-4, Q-R, A-F, Z-V (mapped to hex 0-F)\n"
            "Menu shortcuts: Ctrl+O (Load), F5 (Start), F6 (Pause), F7 (Reset)"
        )
        messagebox.showinfo("About", about_text)


if __name__ == "__main__":
    app = Chip8Emu()
    app.mainloop()
