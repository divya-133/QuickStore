# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager
# from config import Config

# db = SQLAlchemy()
# login = LoginManager()
# login.login_view = 'login'

# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     db.init_app(app)
#     login.init_app(app)

#     from app import routes, models
#     with app.app_context():
#         db.create_all()
    
#     return app

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

    db.init_app(app)
    login_manager.init_app(app)

    # Optional: redirect unauthorized users
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'

    from app.routes import main
    app.register_blueprint(main)

    return app
