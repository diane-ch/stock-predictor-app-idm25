import json
import os
from pathlib import Path

class ContentLoader:
    def __init__(self, content_file='content/modules.json'):
        self.project_root = Path(__file__).parent.parent.parent
        self.content_file = self.project_root / content_file
        self.content_cache = None
        self._load_content()
    
    def _load_content(self):
        """Load the main content file"""
        try:
            with open(self.content_file, 'r', encoding='utf-8') as file:
                self.content_cache = json.load(file)
                print(f"✅ Content loaded from {self.content_file}")
        except FileNotFoundError:
            print(f"❌ Content file {self.content_file} not found!")
            self.content_cache = {"modules": []}
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {self.content_file}: {e}")
            self.content_cache = {"modules": []}
        except Exception as e:
            print(f"❌ Error loading content: {e}")
            self.content_cache = {"modules": []}
    
    def get_modules(self):
        """Get all modules with their basic info"""
        if not self.content_cache:
            self._load_content()
        
        modules = self.content_cache.get('modules', [])
        # Sort by order if available, otherwise by array position
        return sorted(modules, key=lambda x: x.get('order', 999))
    
    def get_module_by_id(self, module_id):
        """Get specific module by ID"""
        if not self.content_cache:
            self._load_content()
        
        for module in self.content_cache.get('modules', []):
            if module.get('id') == module_id:
                return module
        
        print(f"⚠️ Module '{module_id}' not found")
        return None
    
    def get_lesson_by_id(self, module_id, lesson_id):
        """Get specific lesson by ID"""
        module = self.get_module_by_id(module_id)
        if not module:
            return None
        
        for lesson in module.get('lessons', []):
            if lesson.get('id') == lesson_id:
                return lesson
        
        print(f"⚠️ Lesson '{lesson_id}' not found in module '{module_id}'")
        return None
    
    def get_quiz_by_ids(self, module_id, lesson_id):
        """Get quiz from a specific lesson"""
        lesson = self.get_lesson_by_id(module_id, lesson_id)
        if lesson and 'quiz' in lesson:
            return lesson['quiz']
        
        print(f"⚠️ Quiz not found for lesson '{lesson_id}' in module '{module_id}'")
        return None
    
    def reload_content(self):
        """Reload all content (useful for development)"""
        self.content_cache = None
        self._load_content()
        print("🔄 Content reloaded!")
    
    def validate_content(self):
        """Validate the content structure"""
        if not self.content_cache:
            self._load_content()
        
        errors = []
        
        # Check top-level structure
        if 'modules' not in self.content_cache:
            errors.append("Missing 'modules' key in root object")
            return False
        
        modules = self.content_cache.get('modules', [])
        if not isinstance(modules, list):
            errors.append("'modules' should be an array")
            return False
        
        # Validate each module
        for i, module in enumerate(modules):
            module_prefix = f"Module {i} ({module.get('id', 'unknown')})"
            
            # Required module fields
            required_module_fields = ['id', 'title', 'description', 'emoji', 'icon', 'lessons']
            for field in required_module_fields:
                if field not in module:
                    errors.append(f"{module_prefix}: missing required field '{field}'")
            
            # Validate lessons
            lessons = module.get('lessons', [])
            if not isinstance(lessons, list):
                errors.append(f"{module_prefix}: 'lessons' should be an array")
                continue
            
            for j, lesson in enumerate(lessons):
                lesson_prefix = f"{module_prefix} -> Lesson {j} ({lesson.get('id', 'unknown')})"
                
                # Required lesson fields
                required_lesson_fields = ['id', 'title', 'level', 'steps']
                for field in required_lesson_fields:
                    if field not in lesson:
                        errors.append(f"{lesson_prefix}: missing required field '{field}'")
                
                # Validate steps
                steps = lesson.get('steps', [])
                if not isinstance(steps, list):
                    errors.append(f"{lesson_prefix}: 'steps' should be an array")
                    continue
                
                for k, step in enumerate(steps):
                    step_prefix = f"{lesson_prefix} -> Step {k+1}"
                    
                    # Required step fields
                    required_step_fields = ['title', 'content']
                    for field in required_step_fields:
                        if field not in step:
                            errors.append(f"{step_prefix}: missing required field '{field}'")
                
                # Validate quiz if present
                if 'quiz' in lesson:
                    quiz = lesson['quiz']
                    quiz_prefix = f"{lesson_prefix} -> Quiz"
                    
                    if 'questions' not in quiz:
                        errors.append(f"{quiz_prefix}: missing 'questions' array")
                    else:
                        questions = quiz['questions']
                        if not isinstance(questions, list):
                            errors.append(f"{quiz_prefix}: 'questions' should be an array")
                        else:
                            for q_idx, question in enumerate(questions):
                                q_prefix = f"{quiz_prefix} -> Question {q_idx+1}"
                                required_q_fields = ['question', 'options', 'correct_answer', 'explanation']
                                for field in required_q_fields:
                                    if field not in question:
                                        errors.append(f"{q_prefix}: missing required field '{field}'")
        
        # Print results
        if errors:
            print("❌ Content validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("✅ All content is valid!")
            return True
    
    def get_content_stats(self):
        """Get statistics about the content"""
        if not self.content_cache:
            self._load_content()
        
        modules = self.content_cache.get('modules', [])
        total_lessons = sum(len(module.get('lessons', [])) for module in modules)
        total_steps = 0
        total_quizzes = 0
        total_questions = 0
        
        for module in modules:
            for lesson in module.get('lessons', []):
                total_steps += len(lesson.get('steps', []))
                if 'quiz' in lesson:
                    total_quizzes += 1
                    total_questions += len(lesson['quiz'].get('questions', []))
        
        stats = {
            'modules': len(modules),
            'lessons': total_lessons,
            'steps': total_steps,
            'quizzes': total_quizzes,
            'questions': total_questions
        }
        
        print("📊 Content Statistics:")
        for key, value in stats.items():
            print(f"  - {key.capitalize()}: {value}")
        
        return stats
    

# Global content loader instance
content_loader = ContentLoader()