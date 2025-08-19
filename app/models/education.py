from app import db
from datetime import datetime, timezone

class UserLessonProgress(db.Model):
    __tablename__ = 'user_lesson_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_id = db.Column(db.String(50), nullable=False)
    lesson_id = db.Column(db.String(50), nullable=False)
    
    # Progress tracking
    is_started = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    current_step = db.Column(db.Integer, default=1)
    quiz_attempts = db.Column(db.Integer, default=0)
    quiz_completed = db.Column(db.Boolean, default=False)
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    last_accessed = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='lesson_progress')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'module_id', 'lesson_id', name='unique_user_lesson'),
    )
    
    def __repr__(self):
        return f'<UserLessonProgress {self.user_id}-{self.module_id}-{self.lesson_id}>'
    
    @classmethod
    def get_or_create(cls, user_id, module_id, lesson_id):
        """Get existing progress or create new one"""
        progress = cls.query.filter_by(
            user_id=user_id,
            module_id=module_id,
            lesson_id=lesson_id
        ).first()
        
        if not progress:
            progress = cls(
                user_id=user_id,
                module_id=module_id,
                lesson_id=lesson_id,
                is_started=True
            )
            db.session.add(progress)
            db.session.commit()
        
        return progress
    
    def mark_completed(self):
        """Mark lesson as completed"""
        self.is_completed = True
        self.completed_at = datetime.now(timezone.utc)
        self.last_accessed = datetime.now(timezone.utc)
        db.session.commit()
    
    def update_step(self, step_number):
        """Update current step"""
        self.current_step = max(self.current_step, step_number)
        self.last_accessed = datetime.now(timezone.utc)
        db.session.commit()

class UserModuleProgress(db.Model):
    __tablename__ = 'user_module_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_id = db.Column(db.String(50), nullable=False)
    
    # Progress tracking
    is_started = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    lessons_completed = db.Column(db.Integer, default=0)
    total_lessons = db.Column(db.Integer, default=0)
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='module_progress')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'module_id', name='unique_user_module'),
    )
    
    def calculate_progress_percentage(self):
        """Calculate completion percentage"""
        if self.total_lessons == 0:
            return 0
        return int((self.lessons_completed / self.total_lessons) * 100)

