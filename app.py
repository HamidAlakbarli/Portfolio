import os
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from dotenv import load_dotenv
from langchain.llms import OpenAI


# Load environment variables from .env file
load_dotenv()

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

# Seting OpenAI API key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Loading data from a text file
loader = TextLoader("mydata.txt")
documents = loader.load()

# Spliting the documents into chunks
text_splitter = CharacterTextSplitter(chunk_size=10, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# Creating an embedding model
embedding_model = OpenAIEmbeddings()

# Creating a Chroma vector store
vector_store = Chroma.from_documents(documents=texts, embedding=embedding_model)

# Initializing the OpenAI language model
llm = OpenAI()

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


def get_response(question):
    # Simple greetings handling
    greetings = ['hello', 'hi', 'hey', 'how are you']
    if question.lower() in greetings:
        return "Hello! How can I help you today?"
    
    # Format the question into a structured prompt
    prompt = f"Question: {question}"

    # Query the vector store for relevant documents
    relevant_docs = vector_store.similarity_search(prompt, k=3)

    # Combining the content of the relevant documents
    context = " ".join([doc.page_content for doc in relevant_docs])

   #Checking if context is available and generate response based on context
     # Construct the full prompt with the instructions and context
    if context:
        prompt = f"{instruction_prompt}\n\nContext: {context}\n\nQuestion: {question}"
        response = llm(prompt)
        # Removing the question mark if the user did not include it
        if not question.endswith('?') and response.endswith('?'):
            response = response.rstrip('?')
    else:
        response = "I do not have this information."

    return response


# Defining a model for storing chat history
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(5000), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Creating the database and tables
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

    # Storing question and response in the database
    chat_history = ChatHistory(question=question, answer=response)
    db.session.add(chat_history)
    db.session.commit()

    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)