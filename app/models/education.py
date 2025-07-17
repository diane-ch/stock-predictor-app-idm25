from app import db
from datetime import datetime, date
from sqlalchemy import and_


class Module(db.Model):
    """Learning modules (investment, stock, bitcoin, etc...)"""
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon_path = db.Column(db.String(200))
    order = db.Column(db.Integer, default=1) # Display order
    unlock_requirement = db.Column(db.Integer, default=0) # How many modules must be completed to unlock
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)

    # Relationships
    lessons = db.relationship('Lesson', backref='module', order_by='Lesson.level')

    def __repr__(self):
        return f'<Module {self.name}>'
    
class Lesson(db.Model):
    """Individual lessons within modules"""
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    level = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4 (increasing complexity)
    content = db.Column(db.JSON)  # JSON structure for lesson steps/cards
    estimated_duration = db.Column(db.Integer, default=10)  # 10 minutes
    created_at = db.Column(db.DateTime)

    # Relationships
    quiz = db.relationship('Quiz', backref='lesson', uselist=False)
    user_progress = db.relationship('UserLessonProgress', backref='lesson')

    def __repr__(self):
        return f'<Lesson {self.title}>'

class Quiz(db.Model):
    """Quiz for each lesson (step m+1)"""
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    title = db.Column(db.String(200))
    pass_threshold = db.Column(db.Integer, default=100)     # % needed to pass (100% required for now)
    created_at = db.Column(db.DateTime)

    # Relationships
    questions = db.relationship('Question', backref='quiz', order_by='Question.order')
    attempts = db.relationship('QuizAttempt', backref='quiz')

    def __repr__(self):
        return f'<Quiz for {self.lesson.title}>'
    
class Question(db.Model):
    """Individual quiz questions"""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)    # List of answer options
    correct_answer_index = db.Column(db.Integer, nullable=False)    # Index of correct answer
    explanation = db.Column(db.Text, nullable=False)  # Explanation shown after answer
    lesson_step_reference = db.Column(db.Integer)  # Which lesson step this relates to
    order = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<Question {self.id}>'
    
class UserLessonProgress(db.Model):
    """Track user progress through lessons"""
    __tablename__ = 'user_lesson_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)

    # Progress tracking
    current_step = db.Column(db.Integer, default=1)
    total_steps = db.Column(db.Integer)
    is_completed = db.Column(db.Boolean, default=False)
    quiz_passed = db.Column(db.Boolean, default=False)

    # Date tracking for daily limit
    started_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    last_accessed = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one progress record per user per lesson
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),)
    
    def __repr__(self):
        return f'<UserLessonProgress User:{self.user_id} Lesson:{self.lesson_id}>'
    
class QuizAttempt(db.Model):
    """Track quiz attempts (users can retake)"""
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)

    # Results
    score = db.Column(db.Integer)  # Percentage score
    total_questions = db.Column(db.Integer)
    correct_answers = db.Column(db.Integer)
    is_passed = db.Column(db.Boolean, default=False)
    
    # Attempt tracking
    attempt_number = db.Column(db.Integer, default=1)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Store user answers for review
    answers = db.Column(db.JSON)  # User's answers for each question
    
    def __repr__(self):
        return f'<QuizAttempt User:{self.user_id} Quiz:{self.quiz_id} Score:{self.score}%>'
    
class DailyLessonLimit(db.Model):
    """Track daily lesson limits (1 lesson per day)"""
    __tablename__ = 'daily_lesson_limits'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    lesson_completed = db.Column(db.Boolean, default=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    
    # Unique constraint: one record per user per day
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='unique_user_date'),)
    
    def __repr__(self):
        return f'<DailyLimit User:{self.user_id} Date:{self.date}>'
