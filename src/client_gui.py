import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import time
from datetime import datetime
from protocol.socket_wrapper import BetterUDPSocket
from collections import deque
import os

class ModernChatTCPGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 ChatTCP - Advanced TCP over UDP")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        self.colors = {
            'bg_primary': '#2b2b2b',
            'bg_secondary': '#3c3c3c',
            'bg_tertiary': '#4a4a4a',
            'accent': '#007acc',
            'accent_hover': '#0085e6',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'text_muted': '#888888'
        }
        
        self.root.configure(bg=self.colors['bg_primary'])
        
        self.client_socket = None
        self.connected = False
        self.username = ""
        self.server_ip = ""
        self.server_port = 0
        self.online_users = 0
        
        self.messages = deque(maxlen=100)
        
        self.receive_thread = None
        self.heartbeat_thread = None
        self.running = False
        
        self.connection_dots = 0
        self.typing_indicator = False
        
        self.setup_styles()
        self.setup_ui()
        self.setup_animations()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 16, 'bold'),
                       foreground=self.colors['text_primary'],
                       background=self.colors['bg_primary'])
        
        style.configure('Subtitle.TLabel',
                       font=('Segoe UI', 10),
                       foreground=self.colors['text_secondary'],
                       background=self.colors['bg_primary'])
        
        style.configure('Custom.TFrame',
                       background=self.colors['bg_secondary'],
                       relief='flat',
                       borderwidth=1)
        
        style.configure('Card.TFrame',
                       background=self.colors['bg_tertiary'],
                       relief='raised',
                       borderwidth=2)
        
        style.configure('Custom.TButton',
                       font=('Segoe UI', 9, 'bold'),
                       foreground=self.colors['text_primary'],
                       background=self.colors['accent'],
                       borderwidth=0,
                       focuscolor='none')
        
        style.map('Custom.TButton',
                 background=[('active', self.colors['accent_hover']),
                           ('pressed', self.colors['accent'])])
        
        style.configure('Success.TButton',
                       background=self.colors['success'])
        
        style.configure('Danger.TButton',
                       background=self.colors['danger'])
        
        style.configure('Custom.TEntry',
                       font=('Segoe UI', 10),
                       fieldbackground=self.colors['bg_tertiary'],
                       foreground=self.colors['text_primary'],
                       borderwidth=2,
                       insertcolor=self.colors['text_primary'])
        
    def setup_ui(self):
        main_container = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.setup_header(main_container)
        
        content_frame = tk.Frame(main_container, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        left_panel = self.setup_left_panel(content_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        right_panel = self.setup_right_panel(content_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
    def setup_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.colors['bg_secondary'], height=80)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        logo_frame = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        logo_frame.pack(side=tk.LEFT, padx=20, pady=15)
        
        title_label = tk.Label(logo_frame, text="🚀 ChatTCP", 
                              font=('Segoe UI', 20, 'bold'),
                              fg=self.colors['accent'],
                              bg=self.colors['bg_secondary'])
        title_label.pack()
        
        subtitle_label = tk.Label(logo_frame, text="JarJarJarKom",
                                 font=('Segoe UI', 9),
                                 fg=self.colors['text_muted'],
                                 bg=self.colors['bg_secondary'])
        subtitle_label.pack()
        
        status_frame = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        status_frame.pack(side=tk.RIGHT, padx=20, pady=15)
        
        self.connection_status = tk.Label(status_frame, text="● DISCONNECTED",
                                         font=('Segoe UI', 12, 'bold'),
                                         fg=self.colors['danger'],
                                         bg=self.colors['bg_secondary'])
        self.connection_status.pack(anchor=tk.E)
        
        self.status_detail = tk.Label(status_frame, text="No active connection",
                                     font=('Segoe UI', 9),
                                     fg=self.colors['text_muted'],
                                     bg=self.colors['bg_secondary'])
        self.status_detail.pack(anchor=tk.E)
        
    def setup_left_panel(self, parent):
        panel = tk.Frame(parent, bg=self.colors['bg_secondary'], width=300)
        panel.pack_propagate(False)
        
        conn_card = tk.Frame(panel, bg=self.colors['bg_tertiary'], relief='raised', bd=2)
        conn_card.pack(fill=tk.X, padx=15, pady=15)
        
        card_header = tk.Label(conn_card, text="🔗 Connection Settings",
                              font=('Segoe UI', 12, 'bold'),
                              fg=self.colors['text_primary'],
                              bg=self.colors['bg_tertiary'])
        card_header.pack(pady=(15, 10))
        
        form_frame = tk.Frame(conn_card, bg=self.colors['bg_tertiary'])
        form_frame.pack(padx=20, pady=(0, 20), fill=tk.X)
        
        tk.Label(form_frame, text="Server IP Address:",
                font=('Segoe UI', 9, 'bold'),
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_tertiary']).pack(anchor=tk.W, pady=(5, 2))
        
        self.ip_entry = tk.Entry(form_frame, font=('Segoe UI', 10),
                               bg=self.colors['bg_primary'],
                               fg=self.colors['text_primary'],
                               relief='flat', bd=5)
        self.ip_entry.pack(fill=tk.X, pady=(0, 10))
        self.ip_entry.insert(0, "127.0.0.1")
        
        tk.Label(form_frame, text="Port Number:",
                font=('Segoe UI', 9, 'bold'),
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_tertiary']).pack(anchor=tk.W, pady=(0, 2))
        
        self.port_entry = tk.Entry(form_frame, font=('Segoe UI', 10),
                                 bg=self.colors['bg_primary'],
                                 fg=self.colors['text_primary'],
                                 relief='flat', bd=5)
        self.port_entry.pack(fill=tk.X, pady=(0, 10))
        self.port_entry.insert(0, "55555")
        
        tk.Label(form_frame, text="Display Name:",
                font=('Segoe UI', 9, 'bold'),
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_tertiary']).pack(anchor=tk.W, pady=(0, 2))
        
        self.username_entry = tk.Entry(form_frame, font=('Segoe UI', 10),
                                     bg=self.colors['bg_primary'],
                                     fg=self.colors['text_primary'],
                                     relief='flat', bd=5)
        self.username_entry.pack(fill=tk.X, pady=(0, 15))
        self.username_entry.insert(0, "User1")
        
        btn_frame = tk.Frame(form_frame, bg=self.colors['bg_tertiary'])
        btn_frame.pack(fill=tk.X)
        
        self.connect_btn = tk.Button(btn_frame, text="🚀 Connect",
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['success'],
                                   fg=self.colors['text_primary'],
                                   relief='flat', bd=0,
                                   command=self.connect_to_server)
        self.connect_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.disconnect_btn = tk.Button(btn_frame, text="⏹ Disconnect",
                                      font=('Segoe UI', 10, 'bold'),
                                      bg=self.colors['danger'],
                                      fg=self.colors['text_primary'],
                                      relief='flat', bd=0,
                                      state=tk.DISABLED,
                                      command=self.disconnect_from_server)
        self.disconnect_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        stats_card = tk.Frame(panel, bg=self.colors['bg_tertiary'], relief='raised', bd=2)
        stats_card.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        stats_header = tk.Label(stats_card, text="📊 Connection Statistics",
                               font=('Segoe UI', 12, 'bold'),
                               fg=self.colors['text_primary'],
                               bg=self.colors['bg_tertiary'])
        stats_header.pack(pady=(15, 10))
        
        stats_frame = tk.Frame(stats_card, bg=self.colors['bg_tertiary'])
        stats_frame.pack(padx=20, pady=(0, 20))
        
        self.users_label = tk.Label(stats_frame, text="👥 Online Users: 0",
                                   font=('Segoe UI', 10),
                                   fg=self.colors['text_secondary'],
                                   bg=self.colors['bg_tertiary'])
        self.users_label.pack(anchor=tk.W, pady=2)
        
        self.uptime_label = tk.Label(stats_frame, text="⏱ Connection Time: --:--:--",
                                    font=('Segoe UI', 10),
                                    fg=self.colors['text_secondary'],
                                    bg=self.colors['bg_tertiary'])
        self.uptime_label.pack(anchor=tk.W, pady=2)
        
        self.messages_count = tk.Label(stats_frame, text="💬 Messages Sent: 0",
                                      font=('Segoe UI', 10),
                                      fg=self.colors['text_secondary'],
                                      bg=self.colors['bg_tertiary'])
        self.messages_count.pack(anchor=tk.W, pady=2)
        
        commands_card = tk.Frame(panel, bg=self.colors['bg_tertiary'], relief='raised', bd=2)
        commands_card.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        commands_header = tk.Label(commands_card, text="⚡ Special Commands",
                                  font=('Segoe UI', 12, 'bold'),
                                  fg=self.colors['text_primary'],
                                  bg=self.colors['bg_tertiary'])
        commands_header.pack(pady=(15, 10))
        
        commands_frame = tk.Frame(commands_card, bg=self.colors['bg_tertiary'])
        commands_frame.pack(padx=20, pady=(0, 20), fill=tk.X)
        
        self.change_name_btn = tk.Button(commands_frame, text="✏️ Change Name",
                                       font=('Segoe UI', 9, 'bold'),
                                       bg=self.colors['warning'],
                                       fg=self.colors['bg_primary'],
                                       relief='flat', bd=0,
                                       state=tk.DISABLED,
                                       command=self.change_name)
        self.change_name_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.kill_server_btn = tk.Button(commands_frame, text="💀 Kill Server",
                                       font=('Segoe UI', 9, 'bold'),
                                       bg=self.colors['danger'],
                                       fg=self.colors['text_primary'],
                                       relief='flat', bd=0,
                                       state=tk.DISABLED,
                                       command=self.kill_server)
        self.kill_server_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.clear_chat_btn = tk.Button(commands_frame, text="🗑️ Clear Chat",
                                       font=('Segoe UI', 9, 'bold'),
                                       bg=self.colors['bg_primary'],
                                       fg=self.colors['text_primary'],
                                       relief='flat', bd=0,
                                       command=self.clear_chat)
        self.clear_chat_btn.pack(fill=tk.X)
        
        return panel
        
    def setup_right_panel(self, parent):
        panel = tk.Frame(parent, bg=self.colors['bg_secondary'])
        
        chat_header = tk.Frame(panel, bg=self.colors['bg_tertiary'], height=50)
        chat_header.pack(fill=tk.X, padx=2, pady=(2, 0))
        chat_header.pack_propagate(False)
        
        header_left = tk.Frame(chat_header, bg=self.colors['bg_tertiary'])
        header_left.pack(side=tk.LEFT, padx=15, pady=10)
        
        chat_title = tk.Label(header_left, text="💬 Chat Room",
                             font=('Segoe UI', 14, 'bold'),
                             fg=self.colors['text_primary'],
                             bg=self.colors['bg_tertiary'])
        chat_title.pack(anchor=tk.W)
        
        chat_container = tk.Frame(panel, bg=self.colors['bg_primary'])
        chat_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_container,
            font=('Consolas', 10),
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['accent'],
            selectbackground=self.colors['accent'],
            relief='flat',
            bd=0,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        self.chat_display.tag_configure("system", foreground=self.colors['accent'], font=('Consolas', 9, 'italic'))
        self.chat_display.tag_configure("server", foreground=self.colors['danger'], font=('Consolas', 10, 'bold'))
        self.chat_display.tag_configure("self", foreground=self.colors['success'], font=('Consolas', 10, 'bold'))
        self.chat_display.tag_configure("other", foreground=self.colors['text_secondary'])
        self.chat_display.tag_configure("timestamp", foreground=self.colors['text_muted'], font=('Consolas', 8))
        
        input_container = tk.Frame(panel, bg=self.colors['bg_tertiary'], height=80)
        input_container.pack(fill=tk.X, padx=2, pady=(0, 2))
        input_container.pack_propagate(False)
        
        input_frame = tk.Frame(input_container, bg=self.colors['bg_tertiary'])
        input_frame.pack(fill=tk.BOTH, padx=15, pady=15)
        
        self.message_entry = tk.Entry(
            input_frame,
            font=('Segoe UI', 11),
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['accent'],
            relief='flat',
            bd=8,
            state=tk.DISABLED
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.message_entry.bind('<Return>', self.send_message)
        self.message_entry.bind('<KeyPress>', self.on_typing)
        
        self.send_btn = tk.Button(
            input_frame,
            text="📤 Send",
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors['accent'],
            fg=self.colors['text_primary'],
            relief='flat',
            bd=0,
            width=10,
            state=tk.DISABLED,
            command=self.send_message
        )
        self.send_btn.pack(side=tk.RIGHT)
        
        return panel
    
    def setup_animations(self):
        self.connection_start_time = None
        self.messages_sent = 0
        self.update_connection_time()
        
    def update_connection_time(self):
        if self.connected and self.connection_start_time:
            elapsed = time.time() - self.connection_start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.uptime_label.config(text=f"⏱ Connection Time: {hours:02d}:{minutes:02d}:{seconds:02d}")
        
        self.root.after(1000, self.update_connection_time)
    
    def on_typing(self, event):
        pass
        
    def connect_to_server(self):
        try:
            self.server_ip = self.ip_entry.get().strip()
            self.server_port = int(self.port_entry.get().strip())
            self.username = self.username_entry.get().strip()
            
            if not self.server_ip or not self.server_port or not self.username:
                messagebox.showerror("❌ Connection Error", "Please fill all connection fields!")
                return
            
            if self.username.upper() == "SERVER":
                messagebox.showerror("❌ Invalid Username", "Username 'SERVER' is reserved!")
                return
            
            self.connect_btn.config(state=tk.DISABLED, text="🔄 Connecting...")
            self.ip_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.username_entry.config(state=tk.DISABLED)
            
            self.connection_status.config(text="● CONNECTING", fg=self.colors['warning'])
            self.status_detail.config(text="Establishing TCP handshake...")
            
            self.root.update()
            
            self.client_socket = BetterUDPSocket()
            self.client_socket.connect(self.server_ip, self.server_port)
            
            self.connected = True
            self.running = True
            self.connection_start_time = time.time()
            self.messages_sent = 0
            
            try:
                initial_join = f"AWAL: !awal {self.username}\n"
                self.client_socket.send(initial_join.encode("utf-8"))
            except Exception as e:
                print(f"Error sending initial join message: {e}")
            
            self.connection_status.config(text="● CONNECTED", fg=self.colors['success'])
            self.status_detail.config(text=f"Connected to {self.server_ip}:{self.server_port}")
            
            self.message_entry.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.change_name_btn.config(state=tk.NORMAL)
            self.kill_server_btn.config(state=tk.NORMAL)
            
            self.message_entry.focus()
            
            self.start_background_threads()
            
            self.add_message("SYSTEM", "🎉 Successfully connected to chat room!", system=True)
            self.add_message("SYSTEM", f"📡 Using TCP-over-UDP protocol", system=True)
            self.add_message("SYSTEM", f"👤 Logged in as: {self.username}", system=True)
            
        except Exception as e:
            self.connection_status.config(text="● CONNECTION FAILED", fg=self.colors['danger'])
            self.status_detail.config(text="Failed to establish connection")
            
            self.connect_btn.config(state=tk.NORMAL, text="🚀 Connect")
            self.ip_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.username_entry.config(state=tk.NORMAL)
            
            messagebox.showerror("❌ Connection Failed", f"Failed to connect to server:\n\n{str(e)}")
    
    def disconnect_from_server(self):
        try:
            if self.connected and self.client_socket:
                self.add_message("SYSTEM", "📤 Sending disconnect request...", system=True)
                disconnect_msg = f"{self.username}: !disconnect\n"
                self.client_socket.send(disconnect_msg.encode("utf-8"))
                time.sleep(0.2)
                
            self.cleanup_connection()
            self.add_message("SYSTEM", "👋 Disconnected from server", system=True)
            
        except Exception as e:
            self.cleanup_connection()
            messagebox.showerror("❌ Disconnect Error", f"Error during disconnect: {str(e)}")
    
    def cleanup_connection(self):
        self.running = False
        self.connected = False
        self.connection_start_time = None
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        self.connection_status.config(text="● DISCONNECTED", fg=self.colors['danger'])
        self.status_detail.config(text="No active connection")
        
        self.connect_btn.config(state=tk.NORMAL, text="🚀 Connect")
        self.disconnect_btn.config(state=tk.DISABLED)
        self.message_entry.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.change_name_btn.config(state=tk.DISABLED)
        self.kill_server_btn.config(state=tk.DISABLED)
        
        self.ip_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.username_entry.config(state=tk.NORMAL)
        
        self.users_label.config(text="👥 Online Users: 0")
        self.uptime_label.config(text="⏱ Connection Time: --:--:--")
        self.messages_count.config(text="💬 Messages Sent: 0")
    
    def start_background_threads(self):
        self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.receive_thread.start()
        
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        self.heartbeat_thread.start()
    
    def receive_messages(self):
        while self.running and self.connected:
            try:
                data = self.client_socket.receive(timeout=1.0)
                if data:
                    message = data.decode().strip()
                    if message:
                        self.root.after(0, lambda m=message: self.process_received_message(m))
            except Exception:
                if self.running:
                    self.root.after(0, lambda: self.handle_connection_error())
                break
    
    def send_heartbeat(self):
        while self.running and self.connected:
            try:
                heartbeat_msg = f"[HEARTBEAT]: !heartbeat\n"
                self.client_socket.send(heartbeat_msg.encode("utf-8"))
                time.sleep(1)
            except Exception:
                if self.running:
                    self.root.after(0, lambda: self.handle_connection_error())
                break
    
    def process_received_message(self, message):
        try:
            if message == "SHUTDOWN":
                self.add_message("SERVER", "🔴 Server is shutting down!", system=True)
                self.root.after(3000, self.cleanup_connection)
                return
            
            if message.startswith("COUNT: "):
                try:
                    count = int(message.split(": ")[1])
                    self.users_label.config(text=f"👥 Online Users: {count}")
                except:
                    pass
                return
            
            if message.startswith("SERVER ") and "] - " in message:
                self.add_message("SERVER", message, server=True)
            elif message.startswith("["):
                self.add_message("", message)
            else:
                self.add_message("", message)
                
        except Exception:
            pass
    
    def handle_connection_error(self):
        self.add_message("SYSTEM", "⚠️ Connection lost with server", system=True)
        self.cleanup_connection()
    
    def send_message(self, event=None):
        if not self.connected:
            return
        
        message = self.message_entry.get().strip()
        if not message:
            return
        
        try:
            full_message = f"{self.username}: {message}\n"
            self.client_socket.send(full_message.encode("utf-8"))
            
            self.message_entry.delete(0, tk.END)
            self.messages_sent += 1
            self.messages_count.config(text=f"💬 Messages Sent: {self.messages_sent}")
            
            if not message.startswith("!"):
                timestamp = time.strftime("[%I:%M %p]").lstrip("0")
                self_message = f"{timestamp} {self.username}: {message}"
                self.add_message("SELF", self_message, is_self=True)
            else:
                self.add_message("SYSTEM", f"🔧 Command sent: {message}", system=True)
            
        except Exception as e:
            messagebox.showerror("❌ Send Error", f"Failed to send message: {str(e)}")
    
    def change_name(self):
        if not self.connected:
            return
        
        new_name = simpledialog.askstring("✏️ Change Username", 
                                         "Enter new username:", 
                                         initialvalue=self.username)
        if new_name and new_name.strip() and new_name.strip().upper() != "SERVER":
            try:
                old_name = self.username
                self.username = new_name.strip()
                
                change_message = f"[SERVER]: {old_name} changes its username to {self.username}\n"
                self.client_socket.send(change_message.encode("utf-8"))
                
                self.add_message("SYSTEM", f"✅ Username changed from '{old_name}' to '{self.username}'", system=True)
                
            except Exception as e:
                messagebox.showerror("❌ Error", f"Failed to change name: {str(e)}")
        elif new_name and new_name.strip().upper() == "SERVER":
            messagebox.showerror("❌ Invalid Username", "Username 'SERVER' is reserved!")
    
    def kill_server(self):
        if not self.connected:
            return
        
        if not messagebox.askyesno("💀 Kill Server", 
                                  "Are you sure you want to kill the server?\n\nThis will disconnect all users!"):
            return
        
        password = simpledialog.askstring("🔐 Server Password", 
                                         "Enter server admin password:", 
                                         show='*')
        if password:
            try:
                kill_message = f"{self.username}: !kill {password}\n"
                self.client_socket.send(kill_message.encode("utf-8"))
                self.add_message("SYSTEM", "💀 Kill command sent to server", system=True)
            except Exception as e:
                messagebox.showerror("❌ Error", f"Failed to send kill command: {str(e)}")
    
    def clear_chat(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.add_message("SYSTEM", "🗑️ Chat history cleared", system=True)
    
    def add_message(self, sender, message, system=False, server=False, is_self=False):
        self.chat_display.config(state=tk.NORMAL)
        
        if system:
            timestamp = datetime.now().strftime("[%H:%M:%S]")
            self.chat_display.insert(tk.END, f"{timestamp} ", "timestamp")
            self.chat_display.insert(tk.END, f"[SYSTEM] {message}\n", "system")
        elif server:
            self.chat_display.insert(tk.END, f"{message}\n", "server")
        elif is_self:
            self.chat_display.insert(tk.END, f"[YOU] {message}\n", "self")
        else:
            self.chat_display.insert(tk.END, f"{message}\n", "other")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def on_closing(self):
        if self.connected:
            self.add_message("SYSTEM", "🔄 Disconnecting...", system=True)
            try:
                self.disconnect_from_server()
            except:
                pass
        
        self.running = False
        
        try:
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(timeout=1.0)
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=1.0)
        except:
            pass
        
        self.root.destroy()


class SplashScreen:
    def __init__(self):
        self.splash = tk.Toplevel()
        self.splash.title("ChatTCP")
        self.splash.geometry("500x300")
        self.splash.resizable(False, False)
        self.splash.configure(bg='#1a1a1a')
        
        self.splash.transient()
        self.splash.grab_set()
        
        self.splash.overrideredirect(True)
        
        self.center_window()
        
        self.setup_splash_ui()
        self.animate_splash()
    
    def center_window(self):
        self.splash.update_idletasks()
        x = (self.splash.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.splash.winfo_screenheight() // 2) - (300 // 2)
        self.splash.geometry(f'500x300+{x}+{y}')
    
    def setup_splash_ui(self):
        container = tk.Frame(self.splash, bg='#1a1a1a')
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        title_frame = tk.Frame(container, bg='#1a1a1a')
        title_frame.pack(expand=True)
        
        logo_label = tk.Label(title_frame, text="🚀", 
                             font=('Segoe UI', 48),
                             bg='#1a1a1a', fg='#007acc')
        logo_label.pack()
        
        title_label = tk.Label(title_frame, text="ChatTCP", 
                              font=('Segoe UI', 24, 'bold'),
                              bg='#1a1a1a', fg='#ffffff')
        title_label.pack(pady=(10, 5))
        
        subtitle_label = tk.Label(title_frame, text="Advanced TCP over UDP Chat Protocol", 
                                 font=('Segoe UI', 10),
                                 bg='#1a1a1a', fg='#cccccc')
        subtitle_label.pack()
        
        version_label = tk.Label(title_frame, text="Version 2.0 - JarJarJarKom", 
                                font=('Segoe UI', 8),
                                bg='#1a1a1a', fg='#888888')
        version_label.pack(pady=(20, 0))
        
        self.progress_frame = tk.Frame(container, bg='#1a1a1a')
        self.progress_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        self.progress_label = tk.Label(self.progress_frame, text="Initializing...", 
                                      font=('Segoe UI', 9),
                                      bg='#1a1a1a', fg='#cccccc')
        self.progress_label.pack()
        
        self.progress_bg = tk.Frame(self.progress_frame, bg='#333333', height=4)
        self.progress_bg.pack(fill=tk.X, pady=(10, 0))
        
        self.progress_bar = tk.Frame(self.progress_bg, bg='#007acc', height=4)
        self.progress_bar.place(x=0, y=0, width=0, height=4)
    
    def animate_splash(self):
        steps = [
            ("Loading protocol modules...", 20),
            ("Initializing socket wrapper...", 40),
            ("Setting up GUI components...", 60),
            ("Configuring network interface...", 80),
            ("Ready to connect!", 100)
        ]
        
        def update_progress(step_index=0):
            if step_index < len(steps):
                text, progress = steps[step_index]
                self.progress_label.config(text=text)
                
                target_width = int(420 * progress / 100)
                current_width = self.progress_bar.winfo_width()
                
                def animate_bar(current=current_width):
                    if current < target_width:
                        current = min(current + 8, target_width)
                        self.progress_bar.place(width=current)
                        self.splash.after(20, lambda: animate_bar(current))
                    else:
                        if step_index < len(steps) - 1:
                            self.splash.after(500, lambda: update_progress(step_index + 1))
                        else:
                            self.splash.after(1000, self.close_splash)
                
                animate_bar()
            
        update_progress()
    
    def close_splash(self):
        self.splash.destroy()


def main():
    root = tk.Tk()
    root.withdraw() 
    
    splash = SplashScreen()
    
    def show_main_app():
        root.deiconify() 
        app = ModernChatTCPGUI(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        app.add_message("SYSTEM", "🎯 ChatTCP Client initialized successfully!", system=True)
        app.add_message("SYSTEM", "📋 Instructions:", system=True)
        app.add_message("SYSTEM", "  • Fill connection settings and click Connect", system=True)
        app.add_message("SYSTEM", "  • Use !disconnect to leave chat", system=True)
        app.add_message("SYSTEM", "  • Use !change <name> to change username", system=True)
        app.add_message("SYSTEM", "  • Use !kill <password> for admin shutdown", system=True)
        app.add_message("SYSTEM", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", system=True)
    
    root.after(3500, show_main_app) 
    
    root.mainloop()


if __name__ == "__main__":
    main()