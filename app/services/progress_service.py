# Dans app/services/progress_service.py

from datetime import datetime, timezone
from app.models.education import UserLessonProgress, UserModuleProgress
from app.content.content_loader import content_loader
from app import db

class ProgressService:
    
    @staticmethod
    def get_user_lesson_progress(user_id, module_id, lesson_id):
        """Get progress for a specific lesson"""
        return UserLessonProgress.query.filter_by(
            user_id=user_id,
            module_id=module_id,
            lesson_id=lesson_id
        ).first()
    
    @staticmethod
    def get_user_completed_lessons(user_id, module_id):
        """Get all completed lessons for a user in a module"""
        return UserLessonProgress.query.filter_by(
            user_id=user_id,
            module_id=module_id,
            is_completed=True
        ).all()
    
    @staticmethod
    def is_lesson_unlocked(user_id, module_id, lesson_id):
        """Check if a lesson is unlocked for a user"""
        
        # Get the module and lesson info
        module = content_loader.get_module_by_id(module_id)
        if not module:
            return False
        
        # Find the lesson and its order
        lessons = module.get('lessons', [])
        lesson_order = None
        for i, lesson in enumerate(lessons):
            if lesson['id'] == lesson_id:
                lesson_order = i
                break
        
        if lesson_order is None:
            return False
        
        # First lesson is always unlocked
        if lesson_order == 0:
            return True
        
        # Check if previous lesson is completed
        previous_lesson = lessons[lesson_order - 1]
        previous_progress = ProgressService.get_user_lesson_progress(
            user_id, module_id, previous_lesson['id']
        )
        
        return previous_progress and previous_progress.is_completed
    
    @staticmethod
    def is_module_unlocked(user_id, module_id):
        """Check if a module is unlocked for a user"""
        
        # Get all modules
        all_modules = content_loader.get_modules()
        
        # Find current module order
        current_module_order = None
        for module in all_modules:
            if module['id'] == module_id:
                current_module_order = module.get('order', 999)
                break
        
        if current_module_order is None:
            return False
        
        # First module (order 1) is always unlocked
        if current_module_order <= 1:
            return True
        
        # Check if previous module is completed
        previous_module = None
        for module in all_modules:
            if module.get('order', 999) == current_module_order - 1:
                previous_module = module
                break
        
        if not previous_module:
            return True  # If no previous module found, unlock
        
        return ProgressService.is_module_completed(user_id, previous_module['id'])
    
    @staticmethod
    def is_module_completed(user_id, module_id):
        """Check if all lessons in a module are completed"""
        
        module = content_loader.get_module_by_id(module_id)
        if not module:
            return False
        
        lessons = module.get('lessons', [])
        if not lessons:
            return True  # No lessons = completed
        
        completed_lessons = ProgressService.get_user_completed_lessons(user_id, module_id)
        completed_lesson_ids = {progress.lesson_id for progress in completed_lessons}
        
        # Check if all lessons are completed
        for lesson in lessons:
            if lesson['id'] not in completed_lesson_ids:
                return False
        
        return True
    
    @staticmethod
    def get_module_progress(user_id, module_id):
        """Get detailed progress for a module"""
        
        module = content_loader.get_module_by_id(module_id)
        if not module:
            return None
        
        lessons = module.get('lessons', [])
        lesson_progress = []
        
        for i, lesson in enumerate(lessons):
            progress = ProgressService.get_user_lesson_progress(user_id, module_id, lesson['id'])
            is_unlocked = ProgressService.is_lesson_unlocked(user_id, module_id, lesson['id'])
            
            lesson_progress.append({
                'lesson': lesson,
                'progress': progress,
                'is_unlocked': is_unlocked,
                'is_completed': progress.is_completed if progress else False,
                'is_started': progress.is_started if progress else False
            })
        
        # Calculate module stats
        completed_count = sum(1 for lp in lesson_progress if lp['is_completed'])
        total_count = len(lessons)
        is_completed = completed_count == total_count and total_count > 0
        
        return {
            'module': module,
            'lessons': lesson_progress,
            'completed_lessons': completed_count,
            'total_lessons': total_count,
            'is_completed': is_completed,
            'progress_percentage': int((completed_count / total_count) * 100) if total_count > 0 else 0
        }
    
    @staticmethod
    def start_lesson(user_id, module_id, lesson_id):
        """Mark a lesson as started"""
        progress = UserLessonProgress.get_or_create(user_id, module_id, lesson_id)
        progress.is_started = True
        progress.last_accessed = datetime.now(timezone.utc)
        db.session.commit()
        return progress
    
    @staticmethod
    def complete_lesson(user_id, module_id, lesson_id, quiz_attempts=0):
        """Mark a lesson as completed"""
        progress = UserLessonProgress.get_or_create(user_id, module_id, lesson_id)
        progress.mark_completed()
        progress.quiz_attempts = quiz_attempts
        progress.quiz_completed = True
        
        # Update module progress
        ProgressService._update_module_progress(user_id, module_id)
        
        db.session.commit()  # Ajout du commit
        return progress
    
    @staticmethod
    def _update_module_progress(user_id, module_id):
        """Update module progress based on lesson completions"""
        
        module_progress = UserModuleProgress.query.filter_by(
            user_id=user_id,
            module_id=module_id
        ).first()
        
        if not module_progress:
            module = content_loader.get_module_by_id(module_id)
            total_lessons = len(module.get('lessons', [])) if module else 0
            
            module_progress = UserModuleProgress(
                user_id=user_id,
                module_id=module_id,
                total_lessons=total_lessons,
                is_started=True
            )
            db.session.add(module_progress)
        
        # Count completed lessons
        completed_lessons = ProgressService.get_user_completed_lessons(user_id, module_id)
        module_progress.lessons_completed = len(completed_lessons)
        
        # Check if module is completed
        if module_progress.lessons_completed >= module_progress.total_lessons and module_progress.total_lessons > 0:
            module_progress.is_completed = True
            module_progress.completed_at = datetime.now(timezone.utc)
        
        db.session.commit()
        return module_progress