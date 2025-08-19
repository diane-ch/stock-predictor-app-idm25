from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from app import db
from app.content.content_loader import content_loader
from app.services.progress_service import ProgressService
from flask_login import login_required, current_user

education_bp = Blueprint('education', __name__, template_folder='../templates')

@education_bp.route('/')
@login_required
def education_home():
    """Main education page - display modules with lesson circles"""
    
    # Get modules from JSON file
    json_modules = content_loader.get_modules()
    
    print(f"DEBUG: User ID = {current_user.id}")
    print(f"DEBUG: Found {len(json_modules)} modules")
    
    modules_data = []
    for i, module in enumerate(json_modules):
        module_id = module["id"]
        print(f"DEBUG: Processing module {module_id}, order: {module.get('order', 'NO ORDER')}")

        # Get module progress
        module_progress = ProgressService.get_module_progress(current_user.id, module_id)
        is_module_unlocked = ProgressService.is_module_unlocked(current_user.id, module_id)

        # Add lesson circles info to each module
        lesson_circles = []
        lessons = module.get('lessons', [])
        for j, lesson in enumerate(lessons): 
            lesson_id = lesson['id']
            lesson_progress = ProgressService.get_user_lesson_progress(current_user.id, module_id, lesson_id)
            is_unlocked = ProgressService.is_lesson_unlocked(current_user.id, module_id, lesson_id)
            is_completed = lesson_progress.is_completed if lesson_progress else False
            
            lesson_circles.append({
                'lesson_id': lesson['id'],
                'title': lesson['title'],
                'is_unlocked': is_unlocked and is_module_unlocked,
                'is_completed': is_completed
            })
        
        # Determine module status
        module_status = None
        if not is_module_unlocked:
            module_status = "locked"
        elif module_progress and module_progress.get('is_completed'):
            module_status = "completed"
        else:
            module_status = "available"  # Module déverrouillé mais pas complété
        
        modules_data.append({
            'module': module,
            'lesson_circles': lesson_circles,
            'is_unlocked': is_module_unlocked,
            'status': module_status,
            'progress': module_progress
        })
    
    return render_template('education/learn.html', modules_data=modules_data)


@education_bp.route('/lesson/<module_id>/<lesson_id>/preview')
@login_required
def lesson_preview_api(module_id, lesson_id):
    """API endpoint for lesson preview data (AJAX call)"""

    # Check if lesson is unlocked
    if not ProgressService.is_lesson_unlocked(current_user.id, module_id, lesson_id):
        return jsonify({'error': 'Lesson is locked'}), 403

    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    module = content_loader.get_module_by_id(module_id)
    
    if not lesson:
        return jsonify({'error': 'Lesson not found'}), 404
    
    # Ensure duration field exists
    if 'duration' not in lesson:
        lesson['duration'] = 8  # default duration
        
    return jsonify({
        'lesson': lesson,
        'module': module
    })


@education_bp.route('/lesson/<module_id>/<lesson_id>')
@login_required
def lesson_preview(module_id, lesson_id):
    """Lesson preview page (if accessed directly) - redirects to start"""
    return redirect(url_for('education.lesson_start', 
                          module_id=module_id, 
                          lesson_id=lesson_id))


@education_bp.route('/lesson/<module_id>/<lesson_id>/start')
@login_required
def lesson_start(module_id, lesson_id):
    """Start lesson - redirect to first step"""

    # Check if lesson is unlocked
    if not ProgressService.is_lesson_unlocked(current_user.id, module_id, lesson_id):
        flash('This lesson is locked. Complete previous lessons first.', 'error')
        return redirect(url_for('education.education_home'))

    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Mark lesson as started
    ProgressService.start_lesson(current_user.id, module_id, lesson_id)
    
    return redirect(url_for('education.lesson_step', 
                          module_id=module_id, 
                          lesson_id=lesson_id, 
                          step_number=1))


@education_bp.route('/lesson/<module_id>/<lesson_id>/step/<int:step_number>')
@login_required
def lesson_step(module_id, lesson_id, step_number):
    """Display specific step of a lesson"""

    # Check if lesson is unlocked
    if not ProgressService.is_lesson_unlocked(current_user.id, module_id, lesson_id):
        flash('This lesson is locked.', 'error')
        return redirect(url_for('education.education_home'))

    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Get lesson steps (from your JSON structure)
    lesson_content = lesson.get('steps', [])
    total_steps = len(lesson_content)
    
    # Validate step number
    if step_number < 1 or step_number > total_steps:
        flash('Invalid lesson step.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Update progress - user has reached this step
    progress = ProgressService.get_user_lesson_progress(current_user.id, module_id, lesson_id)
    if progress and hasattr(progress, 'update_step'):
        progress.update_step(step_number)
        db.session.commit()
    
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
        return redirect(url_for('education.lesson_start', 
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
    
    return render_template('education/quiz.html',
                         lesson=lesson,
                         module=module,
                         quiz=quiz,
                         current_question=current_question,
                         current_q_index=current_q_index,
                         question_number=questions_answered_correctly + 1,
                         total_questions=total_questions,
                         progress_percentage=progress_percentage,
                         questions_remaining=len(quiz_data['questions_remaining']))

@education_bp.route('/quiz/<module_id>/<lesson_id>/answer', methods=['POST'])
@login_required
def quiz_answer(module_id, lesson_id):
    """Process quiz answer and redirect back to question or completion"""
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
    
    # CORRECTION: Vérifier si le quiz est terminé et rediriger directement
    if not quiz_data['questions_remaining']:
        # Quiz terminé - marquer comme complété et rediriger
        ProgressService.complete_lesson(
            current_user.id,
            module_id,
            lesson_id,
            quiz_attempts=quiz_data['total_attempts']
        )
        
        # Clean up session
        session.pop(quiz_session_key, None)
        
        return redirect(url_for('education.quiz_complete', 
                              module_id=module_id, 
                              lesson_id=lesson_id))
    else:
        # Continue to next question
        return redirect(url_for('education.quiz_question', 
                              module_id=module_id, 
                              lesson_id=lesson_id))


@education_bp.route('/quiz/<module_id>/<lesson_id>/complete')
@login_required
def quiz_complete(module_id, lesson_id):
    """Quiz completion page - simplified"""
    lesson = content_loader.get_lesson_by_id(module_id, lesson_id)
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('education.education_home'))
    
    # Quiz est déjà marqué comme complété dans quiz_answer
    # On affiche juste la page de completion
    module = content_loader.get_module_by_id(module_id)
    
    return render_template('education/quiz.html',
                         lesson=lesson,
                         module=module,
                         quiz_completed=True)

#####################
# ADMIN/DEV ROUTES
@education_bp.route('/reload-content')
@login_required
def reload_content():
    """Reload content from JSON files (for development)"""
    try:
        content_loader.reload_content()
        flash('Content reloaded successfully!', 'success')
    except Exception as e:
        flash(f'Error reloading content: {str(e)}', 'error')
    return redirect(url_for('education.education_home'))

@education_bp.route('/validate-content')
@login_required
def validate_content():
    """Validate all content files"""
    try:
        is_valid = content_loader.validate_content()
        if is_valid:
            flash('All content files are valid!', 'success')
        else:
            flash('Content validation errors found. Check console.', 'error')
    except Exception as e:
        flash(f'Error validating content: {str(e)}', 'error')
    return redirect(url_for('education.education_home'))