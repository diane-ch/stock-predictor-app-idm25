from app import create_app, db
from app.models.education import Module, Lesson, Quiz, Question
from app.models.users import User

def create_sample_data():
    """Create sample modules and lessons for testing"""
    app = create_app()
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        print("Creating sample education data...")
        
        # Create 4 modules
        modules_data = [
            {
                "name": "Investment Basics",
                "description": "Learn fundamental investment concepts!!!!",
                "order": 1,
                "unlock_requirement": 0  # First module - always unlocked
            },
            {
                "name": "Stock Market",
                "description": "Understanding stocks and trading",
                "order": 2,
                "unlock_requirement": 1  # Unlocked after completing 1 module
            },
            {
                "name": "Cryptocurrency",
                "description": "Digital currencies and blockchain",
                "order": 3,
                "unlock_requirement": 1  # Unlocked after completing 1 module
            },
            {
                "name": "Advanced Trading",
                "description": "Professional trading strategies",
                "order": 4,
                "unlock_requirement": 2  # Unlocked after completing 2 modules
            }
        ]
        
        # Create modules
        modules = []
        for module_data in modules_data:
            module = Module(
                name=module_data["name"],
                description=module_data["description"],
                order=module_data["order"],
                unlock_requirement=module_data["unlock_requirement"]
            )
            db.session.add(module)
            modules.append(module)
        
        db.session.flush()  # Get IDs
        
        # Create 4 lessons for each module
        lesson_templates = [
            {"level": 1, "title": "Basics", "description": "Introduction level"},
            {"level": 2, "title": "Fundamentals", "description": "Core concepts"},
            {"level": 3, "title": "Intermediate", "description": "Advanced understanding"},
            {"level": 4, "title": "Expert", "description": "Master level"}
        ]
        
        for module in modules:
            for lesson_template in lesson_templates:
                lesson = Lesson(
                    module_id=module.id,
                    title=f"{module.name} - {lesson_template['title']}",
                    description=lesson_template["description"],
                    level=lesson_template["level"],
                    content={
                        "steps": [
                            {
                                "title": f"Step 1: Introduction to {module.name}",
                                "content": f"Welcome to {module.name} lesson!"
                            },
                            {
                                "title": f"Step 2: Key Concepts",
                                "content": f"Learn the key concepts of {module.name}."
                            },
                            {
                                "title": f"Step 3: Examples",
                                "content": f"Real-world examples of {module.name}."
                            }
                        ]
                    },
                    estimated_duration=10
                )
                db.session.add(lesson)
        
        # Create a test user
        test_user = User(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            investment_level="basic"
        )
        test_user.set_password("password123")
        db.session.add(test_user)
        
        db.session.commit()
        print("✅ Sample data created successfully!")
        print("📧 Test user: test@example.com / password123")

if __name__ == '__main__':
    create_sample_data()