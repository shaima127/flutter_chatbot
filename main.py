import os
from flask import Flask, request, jsonify
from database import session, init_db, Student, Lesson, StudentProgress, Quiz
from whatsapp_handler import send_whatsapp_message, parse_incoming_message, VERIFY_TOKEN
from ai_handler import ai_handler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize DB
init_db()

# --- Utility Functions ---

def get_or_create_student(phone_number, name):
    student = session.query(Student).filter_by(whatsapp_number=phone_number).first()
    if not student:
        student = Student(whatsapp_number=phone_number, name=name)
        session.add(student)
        session.commit()
        return student, True
    return student, False

def get_next_lesson(student):
    # Find lessons not completed by student
    completed_ids = [p.lesson_id for p in session.query(StudentProgress).filter_by(student_id=student.id).all()]
    next_lesson = session.query(Lesson).filter(~Lesson.id.in_(completed_ids)).order_by(Lesson.order_index).first()
    return next_lesson

# --- Webhook Routes ---

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    phone_number, text, name = parse_incoming_message(data)
    
    if not phone_number or not text:
        return jsonify({"status": "ok"})

    student, is_new = get_or_create_student(phone_number, name)
    
    response_text = ""
    
    if is_new:
        response_text = f"مرحباً {name}! أنا بوت تعليم لغة Flutter. سأقوم بمساعدتك في رحلة تعلمك. يمكنك البدء بطلب 'درس اليوم' أو إجراء 'اختبار تحديد مستوى'."
    
    elif "درس اليوم" in text:
        lesson = get_next_lesson(student)
        if lesson:
            response_text = f"درس اليوم: *{lesson.title}*\n\n{lesson.content}\n\nبعد قراءة الدرس، أجب على السؤال التالي للتأكد من فهمك."
            # Here we could automatically send the first quiz question for this lesson
            quiz = session.query(Quiz).filter_by(lesson_id=lesson.id).first()
            if quiz:
                response_text += f"\n\n*سؤال الاختبار:*\n{quiz.question}\n{quiz.options}"
        else:
            response_text = "لقد أكملت جميع الدروس المتاحة حالياً! أحسنت."
    
    elif "اختبار تحديد مستوى" in text:
        response_text = "حسناً، دعنا نرى مستواك في Flutter. أخبرني، ما هو الفرق بين StatefulWidget و StatelessWidget؟"
    
    elif text.isdigit() and len(text) == 1:
        # Check if the student is currently on a lesson quiz
        lesson = get_next_lesson(student)
        if lesson:
            quiz = session.query(Quiz).filter_by(lesson_id=lesson.id).first()
            if quiz and text == quiz.correct_answer:
                # Mark as completed
                progress = StudentProgress(student_id=student.id, lesson_id=lesson.id, status="Completed")
                session.add(progress)
                student.points += 10
                session.commit()
                response_text = f"إجابة صحيحة! أحسنت يا {student.name}. لقد حصلت على 10 نقاط. نقاطك الحالية: {student.points}.\nاطلب 'درس اليوم' للدرس التالي."
            else:
                response_text = "إجابة غير صحيحة، حاول مرة أخرى أو ابحث في الدرس!"
        else:
            response_text = "يبدو أنك أجبت على سؤال بدون وجود درس حالي. اطلب 'درس اليوم' للبدء."

    else:
        # General AI Response using Groq + RAG
        context = f"Student Name: {student.name}, Level: {student.level}, Points: {student.points}"
        response_text = ai_handler.get_response(text, context)

    send_whatsapp_message(phone_number, response_text)
    return jsonify({"status": "ok"})

# --- Seed Data Route (Helpful for testing) ---

@app.route("/seed")
def seed():
    # Only add if empty
    if session.query(Lesson).count() == 0:
        lessons_data = [
            {
                "title": "مقدمة في بنية Flutter",
                "content": "يعتمد فلاتر على مفهوم 'كل شيء وجت' (Everything is a Widget). تنقسم الوجت إلى نوعين: StatelessWidget للواجهات الثابتة، و StatefulWidget للواجهات التي تحتاج لتغيير حالتها (State).",
                "order_index": 1,
                "quiz": {
                    "question": "ما هي الوجت التي تستخدم لعرض نص ثابت لا يتغير؟",
                    "options": "1. Text (Stateless)\n2. Text (Stateful)\n3. Checkbox\n4. TextField",
                    "correct_answer": "1"
                }
            },
            {
                "title": "إدارة Layout في Flutter",
                "content": "لتنظيم الوجت نستخدم Row للترتيب الأفقي و Column للترتيب الرأسي. كما نستخدم Stack لوضع الوجت فوق بعضها البعض.",
                "order_index": 2,
                "quiz": {
                    "question": "أي وجت تستخدم لترتيب العناصر أفقياً؟",
                    "options": "1. Column\n2. Row\n3. ListView\n4. Container",
                    "correct_answer": "2"
                }
            },
            {
                "title": "التنقل بين الصفحات (Navigation)",
                "content": "نستخدم Navigator.push للانتقال لصفحة جديدة و Navigator.pop للعودة. يمكننا تعريف Routes لتسهيل عملية التنقل في التطبيقات الكبيرة.",
                "order_index": 3,
                "quiz": {
                    "question": "ما هو الأمر المستخدم للعودة إلى الصفحة السابقة؟",
                    "options": "1. Navigator.push\n2. Navigator.pop\n3. Navigator.home\n4. MaterialPageRoute",
                    "correct_answer": "2"
                }
            },
            {
                "title": "بناء القوائم (ListView)",
                "content": "لعرض قائمة من البيانات نستخدم ListView. إذا كانت القائمة طويلة، نستخدم ListView.builder لتحسين الأداء (Lazy Loading).",
                "order_index": 4,
                "quiz": {
                    "question": "أيهما أفضل أداءً لعرض قائمة تحتوي على 1000 عنصر؟",
                    "options": "1. ListView العادي\n2. SingleChildScrollView\n3. ListView.builder\n4. Column",
                    "correct_answer": "3"
                }
            },
            {
                "title": "التحريك (Animations) في Flutter",
                "content": "يوفر فلاتر نوعين من التحريك: Implicit (مثل AnimatedContainer) و Explicit للحركات الأكثر تعقيداً باستخدام AnimationController.",
                "order_index": 5,
                "quiz": {
                    "question": "ما هي الوجت التي تقوم بتحريك خصائصها تلقائياً عند تغير قيمتها؟",
                    "options": "1. Container\n2. AnimatedContainer\n3. Transform\n4. Opacity",
                    "correct_answer": "2"
                }
            }
        ]

        for ld in lessons_data:
            lesson = Lesson(title=ld["title"], content=ld["content"], order_index=ld["order_index"])
            session.add(lesson)
            session.flush()
            
            quiz_data = ld["quiz"]
            quiz = Quiz(
                lesson_id=lesson.id,
                question=quiz_data["question"],
                options=quiz_data["options"],
                correct_answer=quiz_data["correct_answer"]
            )
            session.add(quiz)
        
        session.commit()
    return "تم تحديث المنهج: جميع الدروس الآن مخصصة لـ Flutter فقط وبنجاح!"
    
if __name__ == "__main__":
app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
