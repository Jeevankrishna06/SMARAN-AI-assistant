import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import math

class PandaAnimationManager:
    def __init__(self, gui):
        self.gui = gui
        self.current_state = "idle"
        self.animation_loop_id = None
        self.fade_loop_id = None
        self.tick_count = 0
        self.current_display_image = None
        
    def transition_to_state(self, state):
        # Stop any active animation loop
        if self.animation_loop_id:
            self.gui.root.after_cancel(self.animation_loop_id)
            self.animation_loop_id = None
            
        # Reset float offset and label position immediately to normal
        self.gui.image_label.place(x=0, y=0, relx=0.5, rely=0.5, anchor="center")
        
        self.current_state = state
        
        # Determine image key for target state
        expr_key = "idle"
        if state == "listening":
            if getattr(self.gui, "is_music_active", False):
                expr_key = "music"
            else:
                expr_key = "listening"
        elif state == "thinking":
            expr_key = "thinking"
        elif state in ("speaking", "executing"):
            expr_key = "idle"
        elif state == "music":
            expr_key = "music"
        elif state == "error":
            expr_key = "error"
            
        # Start fade to target image
        self.fade_to_image(expr_key, lambda: self.start_animation_for_state(state))
        
    def fade_to_image(self, target_image_key, on_complete):
        # Cancel any active fade
        if self.fade_loop_id:
            self.gui.root.after_cancel(self.fade_loop_id)
            self.fade_loop_id = None
            
        target_img = self.gui.expressions.get(target_image_key)
        if not target_img:
            on_complete()
            return
            
        if not self.current_display_image:
            self.current_display_image = target_img
            self.gui.display_pil_image(target_img)
            on_complete()
            return
            
        # Start fade animation (10 steps over 300ms)
        self._run_fade(self.current_display_image, target_img, 0, 10, on_complete)
        
    def _run_fade(self, start_img, end_img, step, max_steps, on_complete):
        if step > max_steps:
            self.current_display_image = end_img
            on_complete()
            return
            
        alpha = step / float(max_steps)
        try:
            blended = Image.blend(start_img, end_img, alpha)
            self.gui.display_pil_image(blended)
            self.current_display_image = blended
        except Exception as e:
            self.gui.display_pil_image(end_img)
            self.current_display_image = end_img
            on_complete()
            return
            
        self.fade_loop_id = self.gui.root.after(30, lambda: self._run_fade(start_img, end_img, step + 1, max_steps, on_complete))
        
    def start_animation_for_state(self, state):
        self.tick_count = 0
        self._run_animation_loop()
        
    def _run_animation_loop(self):
        if not self.gui.animation_running:
            return
            
        tick_ms = 50
        self.tick_count += 1
        t = self.tick_count * 0.1
        
        expr_key = "idle"
        if self.current_state == "listening":
            if getattr(self.gui, "is_music_active", False):
                expr_key = "music"
            else:
                expr_key = "listening"
        elif self.current_state == "thinking":
            expr_key = "thinking"
        elif self.current_state in ("speaking", "executing"):
            expr_key = "idle"
        elif self.current_state == "music":
            expr_key = "music"
        elif self.current_state == "error":
            expr_key = "error"
            
        base_img = self.gui.expressions.get(expr_key)
        if not base_img:
            base_img = self.gui.expressions.get("idle")
        
        if not base_img:
            self.animation_loop_id = self.gui.root.after(tick_ms, self._run_animation_loop)
            return
            
        # Run state-based animation
        if self.current_state in ("idle", "quiet", "intel_active"):
            factor = 1.0 + 0.01 * math.sin(t * 2)
            scaled = self.scale_image(base_img, factor)
            self.gui.display_pil_image(scaled)
            self.current_display_image = scaled
            
        elif self.current_state == "listening":
            factor = 1.01 + 0.01 * math.sin(t * 4)
            scaled = self.scale_image(base_img, factor)
            self.gui.display_pil_image(scaled)
            self.current_display_image = scaled
            
        elif self.current_state == "thinking":
            offset = int(2.5 * math.sin(t * 3))
            self.gui.image_label.place(x=0, y=offset, relx=0.5, rely=0.5, anchor="center")
            self.gui.display_pil_image(base_img)
            self.current_display_image = base_img
            
        elif self.current_state == "error":
            offsets = [0, 1, 3, 5, 5, 4, 3, 2, 1, 0]
            if self.tick_count - 1 < len(offsets):
                offset = offsets[self.tick_count - 1]
                self.gui.image_label.place(x=0, y=offset, relx=0.5, rely=0.5, anchor="center")
            else:
                self.gui.image_label.place(x=0, y=0, relx=0.5, rely=0.5, anchor="center")
            self.gui.display_pil_image(base_img)
            self.current_display_image = base_img
            
        elif self.current_state == "music":
            factor = 1.01 + 0.01 * math.sin(t * 4)
            scaled = self.scale_image(base_img, factor)
            self.gui.display_pil_image(scaled)
            self.current_display_image = scaled
            
        elif self.current_state in ("speaking", "executing"):
            factor = 1.0 + 0.01 * math.sin(t * 2)
            scaled = self.scale_image(base_img, factor)
            self.gui.display_pil_image(scaled)
            self.current_display_image = scaled
            
        else:
            self.gui.display_pil_image(base_img)
            self.current_display_image = base_img
            
        self.animation_loop_id = self.gui.root.after(tick_ms, self._run_animation_loop)
        
    def scale_image(self, base_img, factor):
        w, h = 300, 300
        new_w = int(w * factor)
        new_h = int(h * factor)
        return base_img.resize((new_w, new_h), Image.Resampling.BILINEAR)

class SmaranGUI:
    def __init__(self, on_send_callback=None, on_voice_change_callback=None):
        self.on_send_callback = on_send_callback
        self.on_voice_change_callback = on_voice_change_callback
        
        self.root = tk.Tk()
        self.root.title("Smaran")
        self.root.configure(bg="#11111b")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # Center alignment calculations
        window_width = 300
        window_height = 460
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        # Pre-load expression images
        self.expressions = {}
        expression_dir = os.path.join(os.path.dirname(__file__), "smaran-face-expressions")
        image_candidates = {
            "idle": ["smaran_expression_idle.jpeg", "smaran_idle.jpeg", "smaran_idle.jpg", "smaran_idle.png"],
            "listening": ["smaran_listening.jpeg", "smaran_listening.jpg", "smaran_listening.png", "smaran_expression_listening.png"],
            "thinking": ["smaran_thinking.jpg", "smaran_thinking.jpeg", "smaran_thinking.png", "smaran_expression_thinking.png"],
            "error": ["smaran_sad.jpg", "smaran_sad.jpeg", "smaran_sad.png", "smaran_error.jpg", "smaran_error.jpeg", "smaran_error.png", "smaran_expression_sad.png"],
            "music": ["smaran_playing.jpg", "smaran_playing.jpeg", "smaran_playing.png", "smaran_expression_music.png"]
        }
        
        for key, filenames in image_candidates.items():
            loaded = False
            for filename in filenames:
                path = os.path.join(expression_dir, filename)
                if os.path.exists(path):
                    try:
                        img = Image.open(path).convert("RGBA")
                        img_resized = img.resize((300, 300), Image.Resampling.BILINEAR)
                        self.expressions[key] = img_resized
                        print(f"[GUI INIT] Loaded expression '{key}': {path}")
                        loaded = True
                        break
                    except Exception as e:
                        print(f"⚠️ [GUI INIT] Failed to load expression '{key}' from {path}: {e}")
            if not loaded:
                print(f"⚠️ [GUI INIT] Expression candidates for '{key}' do not exist.")

        # Fallback for idle
        if "idle" not in self.expressions:
            fallback_idle_path = os.path.join(os.path.dirname(__file__), "smaran_face.jpeg")
            if os.path.exists(fallback_idle_path):
                try:
                    img = Image.open(fallback_idle_path).convert("RGBA")
                    self.expressions["idle"] = img.resize((300, 300), Image.Resampling.BILINEAR)
                    print(f"[GUI INIT] Loaded fallback idle: {fallback_idle_path}")
                except Exception:
                    pass

        # Animation/State tracking
        self.current_state = "idle"
        self.animation_running = True
        self._revert_timer_id = None

        self.log_visible = False
        self.is_music_active = False
        self.animation_manager = PandaAnimationManager(self)
        self.create_widgets()
        
        # Start dots animation loop
        self.animate()
        
        # Start visual animation loop
        self.animation_manager.transition_to_state("idle")

    def create_widgets(self):
        # 1. Panda Display Frame (fixed size to prevent layout jitter)
        self.avatar_frame = tk.Frame(self.root, width=300, height=300, bg="#11111b")
        self.avatar_frame.pack(pady=(15, 2))
        self.avatar_frame.pack_propagate(False)

        idle_img = self.expressions.get("idle")
        if idle_img:
            try:
                self.avatar_image = ImageTk.PhotoImage(idle_img)
                self.image_label = tk.Label(self.avatar_frame, image=self.avatar_image, bg="#11111b", bd=0, highlightthickness=0)
                self.image_label.place(relx=0.5, rely=0.5, anchor="center")
            except Exception as e:
                print(f"⚠️ [GUI INIT] Could not render idle image: {e}")
                self.image_label = tk.Label(self.avatar_frame, text="🐼", font=("Segoe UI", 48), bg="#11111b", fg="#ffffff", bd=0, highlightthickness=0)
                self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.image_label = tk.Label(self.avatar_frame, text="🐼", font=("Segoe UI", 48), bg="#11111b", fg="#ffffff", bd=0, highlightthickness=0)
            self.image_label.place(relx=0.5, rely=0.5, anchor="center")

        # 1.5. Status Label (Displays companion's current action/mood)
        self.status_label = tk.Label(self.root, text="Ready", font=("Segoe UI Italic", 10), bg="#11111b", fg="#a6adc8")
        self.status_label.pack(pady=(2, 2))

        # Radiobuttons for Voice selection (Male / Female)
        self.voice_gender = tk.StringVar(value="male")
        
        self.voice_frame = tk.Frame(self.root, bg="#11111b")
        self.voice_frame.pack(pady=(0, 5))
        
        self.male_rb = tk.Radiobutton(
            self.voice_frame, 
            text="Male Voice", 
            variable=self.voice_gender,
            value="male",
            bg="#11111b", 
            fg="#a6adc8", 
            selectcolor="#313244",
            activebackground="#11111b",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=0,
            command=self.handle_voice_change
        )
        self.male_rb.pack(side="left", padx=10)
        
        self.female_rb = tk.Radiobutton(
            self.voice_frame, 
            text="Female Voice", 
            variable=self.voice_gender,
            value="female",
            bg="#11111b", 
            fg="#a6adc8", 
            selectcolor="#313244",
            activebackground="#11111b",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=0,
            command=self.handle_voice_change
        )
        self.female_rb.pack(side="left", padx=10)

        # 2. Control Layout Line
        self.control_frame = tk.Frame(self.root, bg="#11111b")
        self.control_frame.pack(fill="x", padx=15, pady=5)

        self.input_box = tk.Entry(self.control_frame, bg="#313244", fg="#cdd6f4", font=("Segoe UI", 11), bd=0)
        self.input_box.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 5))
        self.input_box.bind("<Return>", lambda event: self.handle_send())
        self.input_box.focus()
        self.root.bind("<FocusIn>", lambda event: self.input_box.focus())

        # Text Send Button
        self.send_button = tk.Button(self.control_frame, text="Go", bg="#89b4fa", fg="#11111b", font=("Segoe UI Bold", 9), bd=0, padx=10, command=self.handle_send)
        self.send_button.pack(side="left")

        # 3. Log Activity Drawer
        self.toggle_btn = tk.Button(self.root, text="▼ Show Activity Log", bg="#11111b", fg="#6c7086", font=("Segoe UI", 8), bd=0, command=self.toggle_logs)
        self.toggle_btn.pack(pady=(2, 5))

        self.chat_display = tk.Text(self.root, bg="#181825", fg="#cdd6f4", font=("Consolas", 9), state="disabled", wrap="word", bd=0)

    def toggle_logs(self):
        if not self.log_visible:
            self.root.geometry("300x640")
            self.chat_display.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            self.toggle_btn.config(text="▲ Hide Activity Log")
            self.log_visible = True
        else:
            self.chat_display.pack_forget()
            self.root.geometry("300x460")
            self.toggle_btn.config(text="▼ Show Activity Log")
            self.log_visible = False

    def log_message(self, sender, text):
        """Thread-safe method to append message to chat display"""
        self.root.after(0, lambda: self._log_message_main_thread(sender, text))

    def _log_message_main_thread(self, sender, text):
        self.chat_display.config(state="normal")
        if sender == "User":
            self.chat_display.insert(tk.END, f"\n😎 You: {text}\n")
        elif sender == "Smaran":
            self.chat_display.insert(tk.END, f"\n🐼 Smaran: {text}\n", "smaran_style")
        else:
            self.chat_display.insert(tk.END, f"\n📊 {text}\n", "system_style")
            
        self.chat_display.tag_config("smaran_style", foreground="#a6e3a1")
        self.chat_display.tag_config("system_style", foreground="#f9e2af")
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")

    def handle_voice_change(self):
        if self.on_voice_change_callback:
            self.on_voice_change_callback()

    def handle_send(self):
        user_text = self.input_box.get().strip()
        if not user_text:
            return
        self.log_message("User", user_text)
        self.input_box.delete(0, tk.END)
        if self.on_send_callback:
            self.on_send_callback(user_text)

    def set_state(self, state, task=None):
        """Thread-safe method to request state changes in the UI"""
        self.root.after(0, lambda: self._set_state_main_thread(state, task))

    def display_pil_image(self, img):
        try:
            self.avatar_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.avatar_image, text="")
        except Exception as e:
            print(f"⚠️ [GUI] Failed to display image: {e}")

    def _set_state_main_thread(self, state, task=None):
        self.current_state = state
        
        # Cancel any pending auto-revert timer
        if self._revert_timer_id:
            self.root.after_cancel(self._revert_timer_id)
            self._revert_timer_id = None
            
        # Update expression image via animation manager
        self.animation_manager.transition_to_state(state)
            
        if state == "idle":
            self.status_label.config(text="Ready", fg="#a6adc8")
        elif state == "listening":
            self.status_label.config(text="Listening...", fg="#89b4fa")
        elif state == "thinking":
            self.status_label.config(text="Thinking...", fg="#f9e2af")
        elif state == "speaking":
            display_text = task if task else "Speaking..."
            self.status_label.config(text=display_text, fg="#a6e3a1")
        elif state == "music":
            display_text = task if task else "Playing Music..."
            self.status_label.config(text=display_text, fg="#f9e2af")
        elif state == "executing":
            display_text = task if task else "Executing..."
            self.status_label.config(text=display_text, fg="#cba6f7")
        elif state == "quiet":
            self.status_label.config(text="Quiet Mode Active", fg="#f38ba8")
        elif state == "intel_active":
            self.status_label.config(text="Intelligence Mode Activated", fg="#89b4fa")
        elif state == "success":
            display_text = task if task else "Done."
            self.status_label.config(text=display_text, fg="#a6e3a1")
            # Auto-revert to idle after 1.5s
            self._revert_timer_id = self.root.after(1500, lambda: self.set_state("idle"))
        elif state == "error":
            display_text = task if task else "Error."
            self.status_label.config(text=display_text, fg="#f38ba8")
            # Auto-revert to idle after 2.5s
            self._revert_timer_id = self.root.after(2500, lambda: self.set_state("idle"))

        self.root.update()

    def update_expression_image(self, state):
        expr_key = "idle"
        if state == "listening":
            if getattr(self, "is_music_active", False):
                expr_key = "music"
            else:
                expr_key = "listening"
        elif state == "thinking":
            expr_key = "thinking"
        elif state in ("speaking", "executing"):
            expr_key = "idle"  # Shows idle/speaking expression
        elif state == "music":
            expr_key = "music"
        elif state == "error":
            expr_key = "error"
            
        img = self.expressions.get(expr_key)
        if img:
            try:
                self.avatar_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.avatar_image, text="")
            except Exception as e:
                print(f"⚠️ [GUI] Failed to update expression image: {e}")
        else:
            # Fallback to emoji if images not loaded
            emoji = "🐼"
            if expr_key == "listening":
                emoji = "👂"
            elif expr_key == "thinking":
                emoji = "🤔"
            elif expr_key == "error":
                emoji = "😢"
            elif expr_key == "music":
                emoji = "🎵"
            self.image_label.config(text=emoji, image="", font=("Segoe UI", 48), fg="#ffffff")

    def animate(self):
        if not self.animation_running:
            return
            
        import time
        now = time.time()
        
        # Update thinking state dots animation dynamically without image scaling
        if self.current_state == "thinking":
            dots_count = int(now * 2) % 4
            self.status_label.config(text="Thinking" + "." * dots_count)
            
        # Schedule next frame in 100ms
        self.root.after(100, self.animate)

    def run(self):
        self.root.mainloop()

class PandaStateManager:
    def __init__(self, gui):
        self.gui = gui

    def set_state(self, state, task=None):
        """Changes the assistant state thread-safely via GUI delegation"""
        if self.gui:
            self.gui.set_state(state, task)