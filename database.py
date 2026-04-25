from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    whatsapp_number = Column(String, unique=True, nullable=False)
    name = Column(String)
    level = Column(String, default="Beginner")
    points = Column(Integer, default=0)
    current_lesson_index = Column(Integer, default=1)

class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    order_index = Column(Integer, unique=True, nullable=False)

class StudentProgress(Base):
    __tablename__ = 'student_progress'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    lesson_id = Column(Integer, ForeignKey('lessons.id'))
    status = Column(String, default="In Progress") # e.g., "Completed"

class Quiz(Base):
    __tablename__ = 'quizzes'
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'))
    question = Column(String, nullable=False)
    options = Column(String, nullable=False) # Store as JSON or string
    correct_answer = Column(String, nullable=False)

# Database setup
import os
from dotenv import load_dotenv
load_dotenv()

# Use DATABASE_URL from .env (for Supabase/Postgres) or fallback to local SQLite
db_url = os.getenv("DATABASE_URL", "sqlite:///flutter_tutor.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

def init_db():
    Base.metadata.create_all(engine)
    print("Database initialized.")

if __name__ == "__main__":
    init_db()
