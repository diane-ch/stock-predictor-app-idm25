from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.users import User
from app.models.education import Module, Lesson, UserLessonProgress
from app.content.content_loader import content_loader  # ← Add this import
from flask_login import login_required, current_user

education_bp = Blueprint('education', __name__, template_folder='../templates')

@education_bp.route('/')
@login_required
def education_home():
    """Main education page - display modules from JSON"""
    
    # Get modules from JSON file (not database)
    json_modules = content_loader.get_modules()
    
    modules_data = []
    for i, module in enumerate(json_modules):
        modules_data.append({
            'module': module,
            'is_unlocked': i == 0  # Only first module unlocked for now
        })
    
    return render_template('education/home.html', modules_data=modules_data)

@education_bp.route('/module/<module_id>')  # ← Note: string ID, not int
@login_required
def module_detail(module_id):
    """View lessons in a specific module"""
    module = content_loader.get_module_by_id(module_id)
    if not module:
        flash('Module not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    # For now, only allow first module
    if module['order'] != 1:
        flash('This module is locked. Complete previous modules to unlock it.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Prepare lesson data
    lessons_data = []
    for lesson in module.get('lessons', []):
        lessons_data.append({
            'lesson': lesson,
            'is_unlocked': lesson['level'] == 1  # Only level 1 unlocked for now
        })
    
    return render_template('education/module_detail.html',
                         module=module,
                         lessons_data=lessons_data)

@education_bp.route('/lesson/<module_id>/<lesson_id>')  # ← Two string parameters
@login_required
def lesson_detail(module_id, lesson_id):
    """View specific lesson"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Only allow level 1 lessons for now
    if lesson['level'] != 1:
        flash('This lesson is locked. Complete previous lessons first.', 'error')
        return redirect(url_for('education.module_detail', module_id=module_id))
    
    module = content_loader.get_module_by_id(module_id)
    return render_template('education/lesson.html', lesson=lesson, module=module)

@education_bp.route('/quiz/<module_id>/<lesson_id>')
@login_required
def quiz_detail(module_id, lesson_id):
    """View quiz for a lesson"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson or 'quiz' not in lesson:
        flash('Quiz not found.', 'error')
        return redirect(url_for('education.lesson_detail', module_id=module_id, lesson_id=lesson_id))
    
    module = content_loader.get_module_by_id(module_id)
    return render_template('education/quiz.html', 
                         lesson=lesson, 
                         module=module, 
                         quiz=lesson['quiz'])

@education_bp.route('/quiz/<module_id>/<lesson_id>/submit', methods=['POST'])
@login_required
def quiz_submit(module_id, lesson_id):
    """Submit quiz answers"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson or 'quiz' not in lesson:
        flash('Quiz not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    quiz = lesson['quiz']
    
    # Get user answers
    answers = []
    for i in range(len(quiz.get('questions', []))):
        answer = request.form.get(f'question_{i}')
        if answer is not None:
            answers.append(int(answer))
        else:
            answers.append(-1)  # No answer selected
    
    # Calculate score
    correct_count = 0
    total_questions = len(quiz.get('questions', []))
    
    for i, question in enumerate(quiz.get('questions', [])):
        if i < len(answers) and answers[i] == question.get('correct_answer', -1):
            correct_count += 1
    
    score = int((correct_count / total_questions) * 100) if total_questions > 0 else 0
    is_passed = score >= 100  # Need 100% to pass
    
    result = {
        'score': score,
        'is_passed': is_passed,
        'correct_answers': correct_count,
        'total_questions': total_questions
    }
    
    # For now, just show results (later we'll save to database)
    module = content_loader.get_module_by_id(module_id)
    return render_template('education/quiz_results.html',
                         lesson=lesson,
                         module=module,
                         quiz=quiz,
                         result=result,
                         user_answers=answers)

# Development/admin routes
@education_bp.route('/reload-content')
@login_required
def reload_content():
    """Reload content from JSON files (for development)"""
    if current_user.email.endswith('@admin.com') or True:  # Allow for now
        content_loader.reload_content()
        flash('Content reloaded successfully!', 'success')
    else:
        flash('Admin access required.', 'error')
    return redirect(url_for('education.education_home'))

@education_bp.route('/validate-content')
@login_required
def validate_content():
    """Validate all content files"""
    if current_user.email.endswith('@admin.com') or True:  # Allow for now
        is_valid = content_loader.validate_content()
        if is_valid:
            flash('All content files are valid!', 'success')
        else:
            flash('Content validation errors found. Check console.', 'error')
    else:
        flash('Admin access required.', 'error')
    return redirect(url_for('education.education_home'))