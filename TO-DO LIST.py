import time
from tkinter import *
from tkinter import messagebox
from plyer import notification  # For system-level notifications
import sqlite3 as sql
import threading
from datetime import datetime

# Database Operations
class TaskDatabase:
    def __init__(self, db_name='tasks.db'):
        self.db_name = db_name

    def get_connection(self):
        # Ensure each thread gets its own database connection
        return sql.connect(self.db_name)

    def add_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            return True
        except sql.IntegrityError:
            return False
        finally:
            conn.close()

    def authenticate_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        return user

    def add_task(self, user_id, title, deadline, priority):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO tasks (user_id, title, deadline, priority, completed) VALUES (?, ?, ?, ?, 0)',
            (user_id, title, deadline, priority)
        )
        conn.commit()
        conn.close()

    def get_tasks(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, title, deadline, priority, completed FROM tasks WHERE user_id = ? ORDER BY deadline ASC',
            (user_id,)
        )
        tasks = cursor.fetchall()
        conn.close()
        return tasks

    def mark_completed(self, task_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET completed = 1 WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()

    def delete_task(self, task_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()

# GUI for Login and Task Management
class TaskManager:
    def __init__(self, root):
        self.db = TaskDatabase()
        self.user_id = None

        # Root Window Configuration
        root.title("To-Do List - Industry Edition")
        root.geometry("800x600+450+150")
        root.configure(bg="#EAF6F6")
        self.root = root

        # Login Frame
        self.login_frame = Frame(root, bg="#A8D5E2", pady=20, padx=20)
        self.login_frame.pack(fill="both", expand=True)
        self.build_login_screen()

    def build_login_screen(self):
        Label(self.login_frame, text="Welcome to To-Do List", font=("Arial", 24, "bold"), bg="#A8D5E2").pack(pady=20)
        Label(self.login_frame, text="Username:", font=("Arial", 14), bg="#A8D5E2").pack(pady=5)
        self.username_entry = Entry(self.login_frame, font=("Arial", 14))
        self.username_entry.pack(pady=5)
        Label(self.login_frame, text="Password:", font=("Arial", 14), bg="#A8D5E2").pack(pady=5)
        self.password_entry = Entry(self.login_frame, font=("Arial", 14), show="*")
        self.password_entry.pack(pady=5)

        Button(self.login_frame, text="Login", font=("Arial", 14), bg="#36B7B7", fg="white",
               command=self.login).pack(pady=10)
        Button(self.login_frame, text="Sign Up", font=("Arial", 14), bg="#36B7B7", fg="white",
               command=self.signup).pack(pady=10)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        user = self.db.authenticate_user(username, password)
        if user:
            self.user_id = user[0]
            self.login_frame.pack_forget()
            self.build_task_screen()
        else:
            messagebox.showerror("Error", "Invalid username or password.")

    def signup(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        if self.db.add_user(username, password):
            messagebox.showinfo("Success", "Account created successfully! You can now log in.")
        else:
            messagebox.showerror("Error", "Username already exists.")

    def build_task_screen(self):
        self.task_frame = Frame(self.root, bg="#EAF6F6", pady=10)
        self.task_frame.pack(fill="both", expand=True)

        # Task List Display
        self.task_listbox = Listbox(self.task_frame, width=80, height=15, font=("Arial", 14), selectmode="SINGLE")
        self.task_listbox.pack(pady=10)

        # Buttons
        Button(self.task_frame, text="Add Task", font=("Arial", 14), bg="#36B7B7", fg="white",
               command=self.add_task_popup).pack(pady=5)
        Button(self.task_frame, text="Mark Completed", font=("Arial", 14), bg="#36B7B7", fg="white",
               command=self.mark_completed).pack(pady=5)
        Button(self.task_frame, text="Delete Task", font=("Arial", 14), bg="#36B7B7", fg="white",
               command=self.delete_task).pack(pady=5)

        # Populate Task List
        self.populate_tasks()

        # Notification System
        self.notification_thread = threading.Thread(target=self.notification_worker)
        self.notification_thread.daemon = True
        self.notification_thread.start()

    def populate_tasks(self):
        self.task_listbox.delete(0, 'end')
        tasks = self.db.get_tasks(self.user_id)
        for task in tasks:
            display_task = f"{task[1]} | Deadline: {task[2]} | Priority: {task[3]} | {'Completed' if task[4] else 'Pending'}"
            self.task_listbox.insert('end', display_task)

    def add_task_popup(self):
        popup = Toplevel(self.root)
        popup.title("Add Task")
        popup.geometry("400x300")

        Label(popup, text="Task Title:", font=("Arial", 14)).pack(pady=5)
        title_entry = Entry(popup, font=("Arial", 14))
        title_entry.pack(pady=5)

        Label(popup, text="Deadline (YYYY-MM-DD HH:MM):", font=("Arial", 14)).pack(pady=5)
        deadline_entry = Entry(popup, font=("Arial", 14))
        deadline_entry.pack(pady=5)

        Label(popup, text="Priority:", font=("Arial", 14)).pack(pady=5)
        priority_var = StringVar(value="Medium")
        OptionMenu(popup, priority_var, "High", "Medium", "Low").pack(pady=5)

        def save_task():
            title = title_entry.get().strip()
            deadline = deadline_entry.get().strip()
            priority = priority_var.get()
            if not title or not deadline:
                messagebox.showerror("Error", "Please fill in all fields.")
                return

            try:
                datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                self.db.add_task(self.user_id, title, deadline, priority)
                self.populate_tasks()
                popup.destroy()
            except ValueError:
                messagebox.showerror("Error", "Invalid deadline format. Use YYYY-MM-DD HH:MM.")

        Button(popup, text="Save Task", font=("Arial", 14), bg="#36B7B7", fg="white", command=save_task).pack(pady=10)

    def mark_completed(self):
        selected_index = self.task_listbox.curselection()
        if not selected_index:
            messagebox.showerror("Error", "No task selected.")
            return

        task_id = self.db.get_tasks(self.user_id)[selected_index[0]][0]
        self.db.mark_completed(task_id)
        self.populate_tasks()

    def delete_task(self):
        selected_index = self.task_listbox.curselection()
        if not selected_index:
            messagebox.showerror("Error", "No task selected.")
            return

        task_id = self.db.get_tasks(self.user_id)[selected_index[0]][0]
        self.db.delete_task(task_id)
        self.populate_tasks()

    def notification_worker(self):
        while True:
            tasks = self.db.get_tasks(self.user_id)
            current_time = datetime.now()
            for task in tasks:
                task_deadline = datetime.strptime(task[2], "%Y-%m-%d %H:%M")
                time_diff = task_deadline - current_time
                if 0 <= time_diff.total_seconds() <= 3600:  # Notify within the next hour
                    notification.notify(
                        title=f"Task Due Soon: {task[1]}",
                        message=f"Your task '{task[1]}' is due at {task_deadline.strftime('%Y-%m-%d %H:%M')}",
                        timeout=10
                    )
            time.sleep(10)  # Check every 10 seconds

# Run the Application
root = Tk()
app = TaskManager(root)
root.mainloop()
