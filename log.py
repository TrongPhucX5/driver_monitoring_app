import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
import requests
from io import BytesIO

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

app = ctk.CTk()
app.title("Sign In / Sign Up")
app.geometry("900x550")
app.minsize(700, 450)

users = {}
password_visible = False

# Hàm tải icon 
def load_icon(url, size=(24, 24)):
    response = requests.get(url)
    return ctk.CTkImage(Image.open(BytesIO(response.content)), size=size)

# Icon mắt mở / mắt bị chéo
eye_open = load_icon("https://cdn-icons-png.flaticon.com/512/159/159604.png")
eye_closed = load_icon("https://cdn-icons-png.flaticon.com/512/10812/10812267.png")

def toggle_password():
    global password_visible
    password_visible = not password_visible
    entry_password.configure(show="" if password_visible else "*")
    btn_eye.configure(image=eye_open if password_visible else eye_closed)

def handle_login():
    email = entry_email.get()
    password = entry_password.get()
    if email in users and users[email] == password:
        messagebox.showinfo("Thành công", "Đăng nhập thành công!")
    else:
        messagebox.showerror("Lỗi", "Sai email hoặc mật khẩu.")

def handle_register():
    name = entry_name.get()
    email = entry_email.get()
    password = entry_password.get()
    if agree_var.get() == 0:
        messagebox.showwarning("Chưa đồng ý", "Bạn phải đồng ý với điều khoản!")
    elif email in users:
        messagebox.showerror("Lỗi", "Email đã tồn tại!")
    else:
        users[email] = password
        messagebox.showinfo("Thành công", f"Chào {name}, bạn đã đăng ký thành công!")

def show_signup():
    btn_signin.configure(fg_color="gray")
    btn_signup.configure(fg_color="#00bfa6")

    # Reset form
    entry_email.delete(0, 'end')
    entry_password.delete(0, 'end')
    entry_name.delete(0, 'end')

    label_name.grid(row=0, column=0, sticky="w", padx=20, pady=(0, 5))
    entry_name.grid(row=1, column=0, padx=20, pady=(0, 10))
    remember_check.grid_forget()
    checkbox.grid(row=6, column=0, padx=20, pady=(0, 10))
    btn_action.configure(text="Sign Up", command=handle_register)
    btn_action.grid(row=7, column=0, padx=20, pady=(10, 10))

def show_signin():
    btn_signin.configure(fg_color="#00bfa6")
    btn_signup.configure(fg_color="gray")

    # Reset form
    entry_email.delete(0, 'end')
    entry_password.delete(0, 'end')
    entry_name.delete(0, 'end')

    label_name.grid_forget()
    entry_name.grid_forget()
    checkbox.grid_forget()
    remember_check.grid(row=6, column=0, sticky="w", padx=20, pady=(0, 10))
    btn_action.configure(text="Sign In", command=handle_login)
    btn_action.grid(row=7, column=0, padx=20, pady=(10, 10))

# Khung trái
left_frame = ctk.CTkFrame(app, fg_color="#0bc3ab")
left_frame.pack(side="left", fill="both", expand=True)
hashtag = ctk.CTkLabel(left_frame, text="Chào mừng bạn\n đến với\n Driver Monitoring",
             font=("Ravie",28), text_color="white", justify="center")
hashtag.place(relx=0.5, rely=0.5, anchor="center")


# Khung phải
right_frame = ctk.CTkFrame(app, fg_color="#1e1e1e")
right_frame.pack(side="right", fill="both", expand=True)

# Nút chuyển chế độ
top_bar = ctk.CTkFrame(right_frame, fg_color="transparent")
top_bar.pack(anchor="ne", padx=20, pady=10)

btn_signin = ctk.CTkButton(top_bar, text="Sign In", width=80, fg_color="#00bfa6", corner_radius=20, command=show_signin)
btn_signin.pack(side="left", padx=5)

btn_signup = ctk.CTkButton(top_bar, text="Sign Up", width=80, fg_color="gray", corner_radius=20, command=show_signup)
btn_signup.pack(side="left", padx=5)

# Form nhập
form_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
form_frame.pack(expand=True)

label_name = ctk.CTkLabel(form_frame, text="HỌ VÀ TÊN", font=("Arial", 12))
entry_name = ctk.CTkEntry(form_frame, width=280)

ctk.CTkLabel(form_frame, text="E-MAIL", font=("Arial", 12)).grid(row=2, column=0, sticky="w", padx=20, pady=(10, 5))
entry_email = ctk.CTkEntry(form_frame, width=280)
entry_email.grid(row=3, column=0, padx=20, pady=(0, 10))

ctk.CTkLabel(form_frame, text="PASSWORD", font=("Arial", 12)).grid(row=4, column=0, sticky="w", padx=20, pady=(10, 5))
entry_password = ctk.CTkEntry(form_frame, show="*", width=280)
entry_password.grid(row=5, column=0, padx=20, pady=(0, 10))

btn_eye = ctk.CTkButton(form_frame,text="",image=eye_closed,width=30,height=30,fg_color="transparent",hover=False,command=toggle_password)
btn_eye.grid(row=5, column=1, padx=(0, 10), pady=(0, 10))

remember_var = ctk.BooleanVar()
remember_check = ctk.CTkCheckBox(form_frame, text="Ghi nhớ đăng nhập", variable=remember_var)

agree_var = ctk.IntVar()
checkbox = ctk.CTkCheckBox(form_frame, text="Bạn đồng ý với Điều Khoản Dịch Vụ\n  và Chính Sách Bảo Mật", variable=agree_var)

btn_action = ctk.CTkButton(form_frame, text="Sign In", width=280, corner_radius=20)

ctk.CTkLabel(form_frame, text="Hoặc", font=("Arial", 12)).grid(row=8, column=0, pady=(10, 5))

btn_google = ctk.CTkButton(form_frame,text="Đăng nhập bằng Google",fg_color="white",text_color="black",hover_color="#f2ebeb",corner_radius=20,width=280)
btn_google.grid(row=9, column=0, pady=(0, 20))

# Mặc định là đăng nhập
show_signin()

app.mainloop()
