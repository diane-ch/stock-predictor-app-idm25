from app.models.education import Module, Lesson, UserLessonProgress
from app.models.users import User
from datetime import date
from sqlalchemy import and_

class EducationManager:
    """Simplified education manager for testing"""
    
    @staticmethod
    def get_user_unlocked_modules(user_id):
        """Get modules available to user based on progress"""
        # For now, just return the first module as unlocked
        # Later we'll implement the full logic
        first_module = Module.query.filter_by(unlock_requirement=0).first()
        if first_module:
            return [first_module]
        return []
    
    @staticmethod
    def get_user_unlocked_lessons(user_id, module_id):
        """Get lessons available to user in a module"""
        # For now, only the first lesson (level 1) is unlocked
        return [1]  # Only level 1 is unlocked
    
    @staticmethod
    def get_module_progress(user_id, module_id):
        """Get user's progress in a specific module"""
        lessons = Lesson.query.filter_by(module_id=module_id).order_by(Lesson.level).all()
        progress_info = []
        
        for lesson in lessons:
            progress = UserLessonProgress.query.filter_by(
                user_id=user_id,
                lesson_id=lesson.id
            ).first()
            
            progress_info.append({
                'lesson': lesson,
                'progress': progress,
                'is_unlocked': lesson.level == 1  # Only level 1 unlocked for now
            })
        
        return progress_info