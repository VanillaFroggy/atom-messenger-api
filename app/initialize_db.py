from sqlalchemy.orm import Session
from app.models import User, Role
import os


def initialize_db(db: Session):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123")

    admin = db.query(User).filter_by(username=admin_username, role=Role.ADMIN).first()

    if not admin:
        new_admin = User(
            username=admin_username,
            password=admin_password,
            role=Role.ADMIN,
            blocked=False
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        print(f"Администратор '{admin_username}' успешно создан.")
    else:
        print("Администратор уже существует.")
