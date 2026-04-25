import os
from dotenv import load_dotenv
from groq import Groq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.document_loaders import PyPDFDirectoryLoader

load_dotenv()

class AIHandler:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_db = None
        self._init_rag()

    def _init_rag(self):
        docs = []
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        
        # Try to load PDFs if the data directory exists and has PDF files
        if os.path.exists(data_dir) and any(f.endswith('.pdf') for f in os.listdir(data_dir)):
            try:
                print("Loading PDFs from data directory...")
                loader = PyPDFDirectoryLoader(data_dir)
                docs = loader.load()
                print(f"Successfully loaded {len(docs)} pages from PDFs.")
            except Exception as e:
                print(f"Error loading PDFs: {e}")
        
        # Fallback to placeholder data if no docs are loaded
        if not docs:
            print("No PDFs found or error loading them. Using fallback data.")
            initial_data = [
                "Flutter is an open-source UI software development kit created by Google.",
                "Widgets are the central hierarchy in the Flutter framework.",
                "StatefulWidget is a widget that has mutable state.",
                "StatelessWidget does not require mutable state.",
                "Provider is a popular state management solution in Flutter.",
                "Riverpod is a reactive caching and state management framework."
            ]
            docs = [Document(page_content=t) for t in initial_data]
            
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        split_docs = text_splitter.split_documents(docs)
        
        # Initialize Chroma in-memory for this example
        self.vector_db = Chroma.from_documents(split_docs, self.embeddings)

    def get_response(self, user_query, context=""):
        # RAG Search
        search_results = self.vector_db.similarity_search(user_query, k=2)
        rag_context = "\n".join([doc.page_content for doc in search_results])
        
        system_prompt = f"""
        You are a Flutter Tutor. Use the following context to help the student.
        Context: {rag_context}
        Student History/Context: {context}
        
        Rules:
        1. Keep responses educational and encouraging.
        2. If the user asks for a lesson, provide a structured explanation.
        3. If it's a quiz, evaluate their answer.
        """
        
        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return completion.choices[0].message.content

ai_handler = AIHandler()
