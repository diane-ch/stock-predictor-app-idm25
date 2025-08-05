from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from app import db
from app.models.users import User
from app.models.education import Module, Lesson, UserLessonProgress
from app.content.content_loader import content_loader
from flask_login import login_required, current_user

education_bp = Blueprint('education', __name__, template_folder='../templates')

@education_bp.route('/')
@login_required
def education_home():
    """Main education page - display modules with lesson circles"""
    
    # Get modules from JSON file
    json_modules = content_loader.get_modules()
    
    modules_data = []
    for i, module in enumerate(json_modules):
        # Add lesson circles info to each module
        lesson_circles = []
        for lesson in module.get('lessons', [])[:4]:  # Only show first 4 lessons as circles
            lesson_circles.append({
                'lesson_id': lesson['id'],
                'title': lesson['title'],
                'is_unlocked': lesson['level'] == 1  # Only level 1 unlocked for now
            })
        
        modules_data.append({
            'module': module,
            'lesson_circles': lesson_circles,
            'is_unlocked': i == 0  # Only first module unlocked for now
        })
    
    return render_template('education/home.html', modules_data=modules_data)

@education_bp.route('/lesson/<module_id>/<lesson_id>')
@login_required
def lesson_preview(module_id, lesson_id):
    """Lesson preview/popup - shows lesson info and 'Start Lesson' button"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Check if lesson is unlocked
    if lesson['level'] != 1:  # Only level 1 unlocked for now
        flash('This lesson is locked. Complete previous lessons first.', 'error')
        return redirect(url_for('education.education_home'))
    
    module = content_loader.get_module_by_id(module_id)
    
    return render_template('education/lesson_preview.html', 
                         lesson=lesson, 
                         module=module)

@education_bp.route('/lesson/<module_id>/<lesson_id>/start')
@login_required
def lesson_start(module_id, lesson_id):
    """Start lesson - redirect to first step"""
    return redirect(url_for('education.lesson_step', 
                          module_id=module_id, 
                          lesson_id=lesson_id, 
                          step_number=1))

@education_bp.route('/lesson/<module_id>/<lesson_id>/step/<int:step_number>')
@login_required
def lesson_step(module_id, lesson_id, step_number):
    """Display specific step of a lesson"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Check if lesson is unlocked
    if lesson['level'] != 1:
        flash('This lesson is locked.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Get lesson steps (from your JSON structure)
    lesson_content = lesson.get('steps', [])
    total_steps = len(lesson_content)
    
    # Validate step number
    if step_number < 1 or step_number > total_steps:
        flash('Invalid lesson step.', 'error')
        return redirect(url_for('education.lesson_preview', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    
    # Get current step content
    current_step = lesson_content[step_number - 1]  # Array is 0-indexed
    
    # Calculate progress
    progress_percentage = int((step_number / total_steps) * 100)
    is_last_step = step_number == total_steps
    
    # Determine next action
    if is_last_step:
        next_url = url_for('education.quiz_detail', 
                          module_id=module_id, 
                          lesson_id=lesson_id)
        button_text = "Go to Quiz"
    else:
        next_url = url_for('education.lesson_step', 
                          module_id=module_id, 
                          lesson_id=lesson_id, 
                          step_number=step_number + 1)
        button_text = "Next"
    
    module = content_loader.get_module_by_id(module_id)
    
    return render_template('education/lesson_step.html',
                         lesson=lesson,
                         module=module,
                         current_step=current_step,
                         step_number=step_number,
                         total_steps=total_steps,
                         progress_percentage=progress_percentage,
                         is_last_step=is_last_step,
                         next_url=next_url,
                         button_text=button_text)

# ADAPTIVE QUIZ SYSTEM
@education_bp.route('/quiz/<module_id>/<lesson_id>')
@login_required
def quiz_detail(module_id, lesson_id):
    """Start quiz - initialize session and redirect to first question"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson or 'quiz' not in lesson:
        flash('Quiz not found.', 'error')
        return redirect(url_for('education.lesson_preview', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    
    quiz = lesson['quiz']
    
    # Initialize quiz session data
    quiz_session_key = f"quiz_{module_id}_{lesson_id}"
    session[quiz_session_key] = {
        'questions_remaining': list(range(len(quiz['questions']))),  # [0, 1, 2, 3, 4]
        'questions_wrong': [],  # Questions that were answered incorrectly
        'questions_correct': [],  # Questions answered correctly
        'current_question_index': 0,
        'total_attempts': 0
    }
    
    # Redirect to first question
    return redirect(url_for('education.quiz_question', 
                          module_id=module_id, 
                          lesson_id=lesson_id))

@education_bp.route('/quiz/<module_id>/<lesson_id>/question')
@login_required  
def quiz_question(module_id, lesson_id):
    """Display current quiz question"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson or 'quiz' not in lesson:
        flash('Quiz not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    quiz = lesson['quiz']
    quiz_session_key = f"quiz_{module_id}_{lesson_id}"
    
    # Get or initialize quiz session
    if quiz_session_key not in session:
        return redirect(url_for('education.quiz_detail', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    
    quiz_data = session[quiz_session_key]
    
    # Check if quiz is complete
    if not quiz_data['questions_remaining']:
        return redirect(url_for('education.quiz_complete', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    
    # Get current question
    current_q_index = quiz_data['questions_remaining'][0]
    current_question = quiz['questions'][current_q_index]
    
    # Calculate progress
    total_questions = len(quiz['questions'])
    questions_answered_correctly = len(quiz_data['questions_correct'])
    progress_percentage = int((questions_answered_correctly / total_questions) * 100)
    
    module = content_loader.get_module_by_id(module_id)
    
    return render_template('education/quiz_question.html',
                         lesson=lesson,
                         module=module,
                         quiz=quiz,
                         current_question=current_question,
                         current_q_index=current_q_index,
                         question_number=questions_answered_correctly + 1,
                         total_questions=total_questions,
                         progress_percentage=progress_percentage)

@education_bp.route('/quiz/<module_id>/<lesson_id>/answer', methods=['POST'])
@login_required
def quiz_answer(module_id, lesson_id):
    """Process quiz answer and show immediate feedback"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson or 'quiz' not in lesson:
        flash('Quiz not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    quiz = lesson['quiz']
    quiz_session_key = f"quiz_{module_id}_{lesson_id}"
    
    if quiz_session_key not in session:
        return redirect(url_for('education.quiz_detail', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    
    quiz_data = session[quiz_session_key]
    
    # Get user's answer
    user_answer = request.form.get('answer')
    if user_answer is None:
        flash('Please select an answer.', 'error')
        return redirect(url_for('education.quiz_question', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    
    user_answer = int(user_answer)
    
    # Get current question
    current_q_index = quiz_data['questions_remaining'][0]
    current_question = quiz['questions'][current_q_index]
    correct_answer = current_question['correct_answer']
    
    # Check if answer is correct
    is_correct = user_answer == correct_answer
    
    quiz_data['total_attempts'] += 1
    
    if is_correct:
        # Remove from remaining, add to correct
        quiz_data['questions_remaining'].pop(0)
        quiz_data['questions_correct'].append(current_q_index)
        # Remove from wrong list if it was there
        if current_q_index in quiz_data['questions_wrong']:
            quiz_data['questions_wrong'].remove(current_q_index)
    else:
        # Move to end of remaining questions (will be asked again)
        quiz_data['questions_remaining'].pop(0)
        quiz_data['questions_remaining'].append(current_q_index)
        # Add to wrong list if not already there
        if current_q_index not in quiz_data['questions_wrong']:
            quiz_data['questions_wrong'].append(current_q_index)
    
    # Update session
    session[quiz_session_key] = quiz_data
    
    module = content_loader.get_module_by_id(module_id)
    
    return render_template('education/quiz_feedback.html',
                         lesson=lesson,
                         module=module,
                         current_question=current_question,
                         user_answer=user_answer,
                         is_correct=is_correct,
                         questions_remaining=len(quiz_data['questions_remaining']),
                         total_questions=len(quiz['questions']))

@education_bp.route('/quiz/<module_id>/<lesson_id>/complete')
@login_required
def quiz_complete(module_id, lesson_id):
    """Quiz completion page"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    quiz_session_key = f"quiz_{module_id}_{lesson_id}"
    
    if quiz_session_key not in session:
        return redirect(url_for('education.quiz_detail', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    
    quiz_data = session[quiz_session_key]
    
    # Clean up session
    session.pop(quiz_session_key, None)
    
    module = content_loader.get_module_by_id(module_id)
    
    return render_template('education/quiz_complete.html',
                         lesson=lesson,
                         module=module,
                         total_attempts=quiz_data['total_attempts'],
                         total_questions=len(lesson['quiz']['questions']))

# LEGACY/ADMIN ROUTES - Keep for development
@education_bp.route('/module/<module_id>')
@login_required
def module_detail(module_id):
    """Legacy route - View lessons in a specific module"""
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