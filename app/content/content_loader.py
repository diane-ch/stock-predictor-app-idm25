import json
import os
from pathlib import Path

class ContentLoader:
    def __init__(self, content_dir='content'):
        self.project_root = Path(__file__).parent.parent.parent
        self.content_dir = self.project_root / content_dir
        self.modules_index_file = self.content_dir / 'config' / 'modules-index.json'
        self.modules_cache = {}
        self._load_modules_index()
    
    def _load_modules_index(self):
        """Load the modules index file"""
        try:
            with open(self.modules_index_file, 'r') as file:
                self.modules_index = json.load(file)
        except FileNotFoundError:
            print(f"Modules index file {self.modules_index_file} not found!")
            self.modules_index = {"modules": []}
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {self.modules_index_file}: {e}")
            self.modules_index = {"modules": []}
    
    def _load_module_file(self, module_file_path):
        """Load a specific module file"""
        if module_file_path in self.modules_cache:
            return self.modules_cache[module_file_path]
        
        full_path = self.content_dir / module_file_path
        try:
            with open(full_path, 'r') as file:
                module_data = json.load(file)
                self.modules_cache[module_file_path] = module_data
                return module_data
        except FileNotFoundError:
            print(f"Module file {full_path} not found!")
            return None
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {full_path}: {e}")
            return None
    
    def get_modules(self):
        """Get all modules with their basic info"""
        modules = []
        for module_info in self.modules_index.get('modules', []):
            module_data = self._load_module_file(module_info['file'])
            if module_data:
                # Merge index info with module data
                module_data['order'] = module_info['order']
                module_data['unlock_requirement'] = module_info['unlock_requirement']
                modules.append(module_data)
        
        return sorted(modules, key=lambda x: x['order'])
    
    def get_module_by_id(self, module_id):
        """Get specific module by ID"""
        # Find module info in index
        module_info = None
        for info in self.modules_index.get('modules', []):
            if info['id'] == module_id:
                module_info = info
                break
        
        if not module_info:
            return None
        
        # Load the full module data
        module_data = self._load_module_file(module_info['file'])
        if module_data:
            module_data['order'] = module_info['order']
            module_data['unlock_requirement'] = module_info['unlock_requirement']
        
        return module_data
    
    def get_lesson_by_id(self, module_id, lesson_id):
        """Get specific lesson by ID"""
        module = self.get_module_by_id(module_id)
        if module:
            for lesson in module.get('lessons', []):
                if lesson['id'] == lesson_id:
                    return lesson
        return None
    
    def reload_content(self):
        """Reload all content (useful for development)"""
        self.modules_cache.clear()
        self._load_modules_index()
        print("✅ Content reloaded!")
    
    def validate_content(self):
        """Validate all content files"""
        errors = []
        
        for module_info in self.modules_index.get('modules', []):
            module_data = self._load_module_file(module_info['file'])
            if not module_data:
                errors.append(f"Could not load module file: {module_info['file']}")
                continue
            
            # Validate module structure
            required_fields = ['id', 'name', 'description', 'lessons']
            for field in required_fields:
                if field not in module_data:
                    errors.append(f"Module {module_info['id']} missing field: {field}")
            
            # Validate lessons
            for lesson in module_data.get('lessons', []):
                lesson_required = ['id', 'title', 'level', 'steps']
                for field in lesson_required:
                    if field not in lesson:
                        errors.append(f"Lesson {lesson.get('id', 'unknown')} missing field: {field}")
        
        if errors:
            print("❌ Content validation errors:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("✅ All content files are valid!")
        
        return len(errors) == 0

# Global content loader instance
content_loader = ContentLoader()