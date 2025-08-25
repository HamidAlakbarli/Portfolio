import os
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, OpenAI

# ---------- Init & Config ----------
load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# Mail
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# DB (SQLite locally; Postgres on Heroku if provided)
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///chatbot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# OpenAI key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# ---------- Data & RAG ----------
# Load your context file
loader = TextLoader("mydata.txt")
documents = loader.load()

# Sensible chunk size to avoid warnings
text_splitter = CharacterTextSplitter(chunk_size=800, chunk_overlap=100)
texts = text_splitter.split_documents(documents)

# Embeddings + vector store
embedding_model = OpenAIEmbeddings()
vector_store = Chroma.from_documents(documents=texts, embedding=embedding_model)

# LLM (completion-style)
llm = OpenAI()  # or: OpenAI(model="gpt-3.5-turbo-instruct")

instruction_prompt = """
You are a chatbot that answers questions based on a provided text file. Follow these instructions carefully:

1.Search for Relevant Information: When you receive a question, search for relevant information within the provided text file.
2.Answer Based on Context: If you find relevant information in the text file, answer the question using that information.
3.No Relevant Information: If you do not find relevant information in the text file, respond with "I do not have this information."
4.Explain Missing Information: If asked why, what, or similar terms, explain that your responses are based on the provided text file and that the information was not found within it.
5.Do Not Make Up Information: Do not fabricate or make up information. Only provide answers supported by the text file.
6.Do not put a question mark when answering if the user did not include it in their question.
7.Do not ask clarifying questions when the user asks a question.
8.If you get a question or just chat with greeting such as Hi, hello, how are you: answer with "Hello, how can I help you?"
9.If there is a question such as "where are you studying" or "where do you work," answer based on the context with the latest information without mentioning that it was taken from the context.
10.If unable to answer a question, respond with "Sorry, I cannot answer this question."
11. Do not put a question mark on your answers!
12. Do not aks a question and respont to the chat which is not question as a answer to question. Just say. I do not have this information.
12. You are Hamid and you should answer like Hamid. Behave and answer like Hamid, you are Hamid.
"""

def get_response(question: str) -> str:
    # greetings
    if question.lower().strip() in ["hello", "hi", "hey", "how are you"]:
        return "Hello! How can I help you today?"

    prompt = f"Question: {question}"
    relevant_docs = vector_store.similarity_search(prompt, k=3)
    context = " ".join(d.page_content for d in relevant_docs)

    if context:
        full = f"{instruction_prompt}\n\nContext: {context}\n\nQuestion: {question}"
        resp = llm.invoke(full)  # returns str for OpenAI() wrapper
        if not question.endswith("?") and isinstance(resp, str) and resp.endswith("?"):
            resp = resp.rstrip("?")
        return resp or "I do not have this information."
    else:
        return "I do not have this information."

# ---------- DB Model ----------
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(5000), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.current_timestamp())

with app.app_context():
    db.create_all()

# ---------- Routes (same pages as before) ----------
@app.get("/")
def home():
    return render_template("index.html")

@app.get("/about")
def about():
    return render_template("about.html")

@app.get("/activities")
def activities():
    return render_template("activities.html")

@app.get("/portfolio")
def portfolio():
    return render_template("portfolio.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        message = request.form.get("message", "")

        msg = Message(
            subject=f"Contact Form: {name}",
            sender=app.config["MAIL_USERNAME"],
            recipients=[app.config["MAIL_USERNAME"]],
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
        )
        mail.send(msg)
        flash("Message sent successfully!", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    answer = get_response(question) if question else "I do not have this information."

    try:
        db.session.add(ChatHistory(question=question, answer=answer))
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"response": answer})

@app.get("/ping")
def ping():
    return "pong"

# ---------- Run (local fallback; Heroku uses PORT) ----------
if __name__ == "__main__":
    import socket

    def free(p: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", p)) != 0

    env_port = os.environ.get("PORT")
    if env_port:          
        port = int(env_port)
    else:                   
        port = 5000 if free(5000) else 5001
        if port == 5001:
            print(" Port 5000 busy locally; using 5001")

    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(debug=debug, host="0.0.0.0", port=port)
