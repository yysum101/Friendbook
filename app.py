from flask import Flask, render_template_string, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "friendbook_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///friendbook.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    posts = db.relationship("Post", backref="author", lazy=True)
    comments = db.relationship("Comment", backref="author", lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comments = db.relationship("Comment", backref="post", lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user = db.Column(db.String(150), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

layout = '''
<!doctype html>
<html>
<head>
    <title>FriendBook</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-4">
    <h1 class="text-center mb-4">📘 FriendBook</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="alert alert-warning">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
</body>
</html>
'''

@app.route("/")
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template_string(layout + '''
    {% block content %}
    <div class="mb-3">
        {% if session.get("user_id") %}
            <form method="POST" action="/post">
                <textarea name="content" class="form-control" placeholder="What's on your mind?" required></textarea>
                <button class="btn btn-primary mt-2">Post</button>
            </form>
            <a href="/chat" class="btn btn-secondary mt-2">Chat Room</a>
            <a href="/logout" class="btn btn-danger mt-2">Logout</a>
        {% else %}
            <a href="/login" class="btn btn-primary">Login</a>
            <a href="/register" class="btn btn-secondary">Register</a>
        {% endif %}
    </div>
    {% for post in posts %}
        <div class="card mb-3">
            <div class="card-body">
                <p>{{ post.content }}</p>
                <small class="text-muted">By {{ post.author.username }} | {{ post.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
                {% if session.get("user_id") == post.user_id %}
                    <form method="POST" action="/edit_post/{{ post.id }}">
                        <textarea name="content" class="form-control mt-2">{{ post.content }}</textarea>
                        <button class="btn btn-sm btn-warning mt-1">Update</button>
                        <a href="/delete_post/{{ post.id }}" class="btn btn-sm btn-danger mt-1">Delete</a>
                    </form>
                {% endif %}
                <hr>
                <form method="POST" action="/comment/{{ post.id }}">
                    <input name="comment" class="form-control" placeholder="Add comment..." required>
                    <button class="btn btn-sm btn-outline-primary mt-1">Comment</button>
                </form>
                {% for comment in post.comments %}
                    <div class="mt-2 ms-3">
                        <strong>{{ comment.author.username }}:</strong> {{ comment.content }}
                        {% if session.get("user_id") == comment.user_id %}
                            <form method="POST" action="/edit_comment/{{ comment.id }}" class="d-inline">
                                <input name="content" class="form-control mt-1" value="{{ comment.content }}">
                                <button class="btn btn-sm btn-warning mt-1">Edit</button>
                            </form>
                            <a href="/delete_comment/{{ comment.id }}" class="btn btn-sm btn-danger mt-1">Delete</a>
                        {% endif %}
                    </div>
                {% endfor %}
            </div>
        </div>
    {% endfor %}
    {% endblock %}
    ''', posts=posts)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect("/register")
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registered! Please log in.")
        return redirect("/login")
    return render_template_string(layout + '''
    {% block content %}
    <h3>Register</h3>
    <form method="POST">
        <input name="username" class="form-control" placeholder="Username" required><br>
        <input name="password" type="password" class="form-control" placeholder="Password" required><br>
        <button class="btn btn-primary">Register</button>
    </form>
    {% endblock %}
    ''')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect("/")
        flash("Invalid login.")
    return render_template_string(layout + '''
    {% block content %}
    <h3>Login</h3>
    <form method="POST">
        <input name="username" class="form-control" placeholder="Username" required><br>
        <input name="password" type="password" class="form-control" placeholder="Password" required><br>
        <button class="btn btn-primary">Login</button>
    </form>
    {% endblock %}
    ''')

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/post", methods=["POST"])
def post():
    if "user_id" not in session:
        return redirect("/login")
    new_post = Post(content=request.form["content"], user_id=session["user_id"])
    db.session.add(new_post)
    db.session.commit()
    return redirect("/")

@app.route("/edit_post/<int:id>", methods=["POST"])
def edit_post(id):
    post = Post.query.get_or_404(id)
    if post.user_id != session.get("user_id"):
        return "Unauthorized"
    post.content = request.form["content"]
    db.session.commit()
    return redirect("/")

@app.route("/delete_post/<int:id>")
def delete_post(id):
    post = Post.query.get_or_404(id)
    if post.user_id != session.get("user_id"):
        return "Unauthorized"
    db.session.delete(post)
    db.session.commit()
    return redirect("/")

@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "user_id" not in session:
        return redirect("/login")
    new_comment = Comment(content=request.form["comment"], user_id=session["user_id"], post_id=post_id)
    db.session.add(new_comment)
    db.session.commit()
    return redirect("/")

@app.route("/edit_comment/<int:id>", methods=["POST"])
def edit_comment(id):
    comment = Comment.query.get_or_404(id)
    if comment.user_id != session.get("user_id"):
        return "Unauthorized"
    comment.content = request.form["content"]
    db.session.commit()
    return redirect("/")

@app.route("/delete_comment/<int:id>")
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    if comment.user_id != session.get("user_id"):
        return "Unauthorized"
    db.session.delete(comment)
    db.session.commit()
    return redirect("/")

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST" and "user_id" in session:
        msg = Message(content=request.form["message"], user=session["username"])
        db.session.add(msg)
        db.session.commit()
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template_string(layout + '''
    {% block content %}
    <h3>Chat Room</h3>
    <form method="POST">
        <input name="message" class="form-control" placeholder="Type message..." required>
        <button class="btn btn-primary mt-2">Send</button>
        <a href="/clearchat" class="btn btn-danger mt-2">Clear Chat</a>
        <a href="/" class="btn btn-secondary mt-2">Back to Home</a>
    </form>
    <div class="mt-4">
        {% for m in messages %}
            <div><strong>{{ m.user }}</strong>: {{ m.content }} <small class="text-muted">{{ m.timestamp.strftime('%H:%M') }}</small></div>
        {% endfor %}
    </div>
    {% endblock %}
    ''', messages=messages)

@app.route("/clearchat")
def clearchat():
    Message.query.delete()
    db.session.commit()
    return redirect("/chat")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=10000)
