import os
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.llms import OpenAI

app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Configuration for Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")

mail = Mail(app)

# Configuration for SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Load data from a text file
loader = TextLoader("mydata.txt")
documents = loader.load()

# Split the documents into chunks
text_splitter = CharacterTextSplitter(chunk_size=10, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# Create an embedding model
embedding_model = OpenAIEmbeddings()

# Create a Chroma vector store
vector_store = Chroma.from_documents(documents=texts, embedding=embedding_model)

# Initialize the OpenAI language model
llm = OpenAI()

def get_response(question):
    # Simple greetings handling
    greetings = ['hello', 'hi', 'hey', 'how are you']
    if question.lower() in greetings:
        return "Hello! How can I help you today?"

    # Format the question into a structured prompt
    prompt = f"Question: {question}"

    # Query the vector store for relevant documents
    relevant_docs = vector_store.similarity_search(prompt, k=3)

    # Combine the content of the relevant documents
    context = " ".join([doc.page_content for doc in relevant_docs])

    # Generate response based on context or fallback to general knowledge
    if context:
        response = llm(f"Answer the question based on the following context: {context}\n\nQuestion: {question}")
    else:
        response = llm(question)

    return response

# Define a model for storing chat history
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(5000), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create the database and tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/activities')
def activities():
    return render_template('activities.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        msg = Message(subject=f"Contact Form: {name}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[app.config['MAIL_USERNAME']],
                      body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}")

        mail.send(msg)
        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    response = get_response(question)

    # Store question and response in the database
    chat_history = ChatHistory(question=question, answer=response)
    db.session.add(chat_history)
    db.session.commit()

    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
