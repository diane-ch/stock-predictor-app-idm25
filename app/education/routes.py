from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.users import User
from app.models.education import Module, Lesson, UserLessonProgress
from app.education.utils import EducationManager
from flask_login import login_required, current_user

# Education blueprint
education_bp = Blueprint('education', __name__, template_folder='../templates')

@education_bp.route('/')
@login_required
def education_home():
    """Main education page - display modules"""
    
    # Get all modules
    all_modules = Module.query.order_by(Module.order).all()
    
    # Get unlocked modules for user
    unlocked_modules = EducationManager.get_user_unlocked_modules(current_user.id)
    unlocked_module_ids = [module.id for module in unlocked_modules]
    
    # Prepare module data with lock status
    modules_data = []
    for module in all_modules:
        modules_data.append({
            'module': module,
            'is_unlocked': module.id in unlocked_module_ids
        })
    
    return render_template('education/home.html', modules_data=modules_data)

@education_bp.route('/module/<int:module_id>')
@login_required
def module_detail(module_id):
    """View lessons in a specific module"""
    module = Module.query.get_or_404(module_id)
    
    # Check if user has access to this module
    unlocked_modules = EducationManager.get_user_unlocked_modules(current_user.id)
    unlocked_module_ids = [m.id for m in unlocked_modules]
    
    if module_id not in unlocked_module_ids:
        flash('This module is locked. Complete previous modules to unlock it.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Get lessons and progress
    lessons = Lesson.query.filter_by(module_id=module_id).order_by(Lesson.level).all()
    unlocked_lessons = EducationManager.get_user_unlocked_lessons(current_user.id, module_id)
    
    # Prepare lesson data
    lessons_data = []
    for lesson in lessons:
        progress = UserLessonProgress.query.filter_by(
            user_id=current_user.id,
            lesson_id=lesson.id
        ).first()
        
        lessons_data.append({
            'lesson': lesson,
            'progress': progress,
            'is_unlocked': lesson.level in unlocked_lessons
        })
    
    return render_template('education/module_detail.html',
                         module=module,
                         lessons_data=lessons_data)

@education_bp.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    """View specific lesson - basic version"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # Simple check: only allow level 1 lessons for now
    if lesson.level != 1:
        flash('This lesson is locked. Complete previous lessons first.', 'error')
        return redirect(url_for('education.module_detail', module_id=lesson.module_id))
    
    return render_template('education/lesson.html', lesson=lesson)