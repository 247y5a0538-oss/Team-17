import os
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- DATABASE MODEL ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))

with app.app_context():
    db.create_all()

# ---------------- AI SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are an AI Career Planning and Resume Mentor.
Help users with career guidance, resume tips, skill gaps, roadmaps, and interview prep.
Be structured, motivating, and practical.
"""

# ---------------- AUTH PAGE ----------------
AUTH_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Career Mentor AI</title>
<style>
body {font-family:Arial;background:linear-gradient(135deg,#4e73df,#1cc88a);display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
.box {background:white;padding:30px;border-radius:10px;width:350px;}
input,button {width:100%;padding:10px;margin-top:10px;}
button {background:#1cc88a;color:white;border:none;}
.toggle {margin-top:10px;text-align:center;color:#4e73df;cursor:pointer;}
.hidden {display:none;}
</style>
</head>
<body>
<div class="box">
<h2 id="title">Login</h2>

<form id="loginForm" method="POST" action="/login">
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>

<form id="registerForm" class="hidden" method="POST" action="/register">
<input name="name" type="text" placeholder="Full Name" required>
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit">Register</button>
</form>

<div class="toggle" onclick="toggleForm()">Don't have an account? Register</div>
</div>

<script>
function toggleForm(){
 document.getElementById("loginForm").classList.toggle("hidden");
 document.getElementById("registerForm").classList.toggle("hidden");
 document.getElementById("title").innerText =
  document.getElementById("loginForm").classList.contains("hidden") ? "Register" : "Login";
}
</script>
</body>
</html>
"""

# ---------------- CHAT PAGE ----------------
CHAT_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Career Mentor AI</title>
<style>
body {margin:0;font-family:Arial;background:#f4f6f9;}
.topbar {background:#4e73df;color:white;padding:10px;text-align:right;}
.chat-container {
    width:500px;margin:30px auto;background:white;border-radius:10px;
    box-shadow:0 5px 15px rgba(0,0,0,0.1);display:flex;flex-direction:column;height:600px;
}
#chat-box {flex:1;padding:15px;overflow-y:auto;}
.input-area {display:flex;align-items:center;border-top:1px solid #ddd;padding:5px;}
input[type="text"] {flex:1;padding:10px;border:none;}
button {padding:8px 12px;border:none;background:#1cc88a;color:white;font-weight:bold;cursor:pointer;margin-left:5px;border-radius:5px;}
.icon-btn {background:#858796;}
.message {margin:8px 0;}
.preview-img {max-width:120px;margin-top:5px;border-radius:5px;}
</style>
</head>
<body>
<div style="text-align:center; margin-top:20px;">
    <img src="picture.png" alt="Career Mentor AI" style="max-width:90%; border-radius:10px;">
</div>

<div class="topbar">
Welcome, {{name}} | <a href="/logout" style="color:white;">Logout</a>
</div>

<div class="chat-container">
<div id="chat-box"></div>

<div class="input-area">
    <!-- Attachment Buttons -->
    <button class="icon-btn" onclick="document.getElementById('fileInput').click()">📎</button>
    <button class="icon-btn" onclick="document.getElementById('cameraInput').click()">📷</button>
    <button class="icon-btn" onclick="startVoice()">🎤</button>

    <input type="file" id="fileInput" style="display:none" onchange="handleFile(event)">
    <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display:none" onchange="handleFile(event)">

    <input id="user-input" type="text" placeholder="Ask about careers, resumes, skills...">
    <button onclick="sendMessage()">Send</button>
</div>
</div>

<script>
let uploadedFile = null;

async function sendMessage(){
    const input=document.getElementById("user-input");
    const msg=input.value.trim();
    if(!msg && !uploadedFile) return;

    addMsg("You",msg);

    const formData = new FormData();
    formData.append("message", msg);
    if(uploadedFile) formData.append("file", uploadedFile);

    input.value="";
    uploadedFile=null;

    const res=await fetch("/chat", { method:"POST", body:formData });
    const data=await res.json();
    addMsg("Mentor AI",data.reply);
}

function addMsg(sender,text,img=null){
    const box=document.getElementById("chat-box");
    const div=document.createElement("div");
    div.className="message";
    div.innerHTML="<b>"+sender+":</b> "+text;
    if(img){
        const image=document.createElement("img");
        image.src=img;
        image.className="preview-img";
        div.appendChild(image);
    }
    box.appendChild(div);
    box.scrollTop=box.scrollHeight;
}

function handleFile(event){
    const file = event.target.files[0];
    if(!file) return;
    uploadedFile = file;

    const reader = new FileReader();
    reader.onload = function(e){
        addMsg("You","[Image Uploaded]", e.target.result);
    }
    reader.readAsDataURL(file);
}

// 🎤 Voice Input
function startVoice(){
    if(!('webkitSpeechRecognition' in window)){
        alert("Speech recognition not supported in this browser");
        return;
    }
    const recognition = new webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.start();

    recognition.onresult = function(event){
        document.getElementById("user-input").value = event.results[0][0].transcript;
    };
}
</script>
</body>
</html>
"""


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("chat_page"))
    return render_template_string(AUTH_PAGE)


@app.route("/register", methods=["POST"])
def register():
    if User.query.filter_by(email=request.form["email"]).first():
        return "Email already exists"
    user = User(name=request.form["name"], email=request.form["email"], password=request.form["password"])
    db.session.add(user)
    db.session.commit()
    return redirect("/")


@app.route("/login", methods=["POST"])
def login():
    user = User.query.filter_by(email=request.form["email"], password=request.form["password"]).first()
    if user:
        session["user_id"] = user.id
        session["user_name"] = user.name
        session["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return redirect("/chatpage")
    return "Invalid credentials"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/chatpage")
def chat_page():
    if "user_id" not in session:
        return redirect("/")
    return render_template_string(CHAT_PAGE, name=session["user_name"])


@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"reply": "Please login first."})

    user_message = request.form.get("message")
    file = request.files.get("file")

    if file:
        file_info = f"\nUser uploaded a file named {file.filename}. Provide guidance related to resumes/careers if relevant."
        user_message = (user_message or "") + file_info

    chat_history = session.get("chat_history", [])

    chat_history.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=chat_history,
        temperature=0.6,
        max_tokens=700
    )

    bot_reply = response.choices[0].message.content
    chat_history.append({"role": "assistant", "content": bot_reply})

    session["chat_history"] = chat_history[-10:]

    return jsonify({"reply": bot_reply})
if __name__ == "__main__":
    app.run(debug=True)

