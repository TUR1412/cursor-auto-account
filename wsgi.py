from app import create_app
from db_utils import init_db

app = create_app()
init_db(app)
