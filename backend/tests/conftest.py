import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base

# In-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db():
    """Fixture to create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """Fixture to override the database dependency and provide a test client"""
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def test_upload_pdf(client):
    """Test uploading a PDF file"""
    pdf_content = b"%PDF-1.4\nThis is a dummy PDF content"
    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = client.post("/upload_pdf/", files=files)

    assert response.status_code == 201
    assert response.json()["message"] == "PDF uploaded successfully"

def test_list_pdfs(client):
    """Test fetching list of uploaded PDFs"""
    response = client.get("/pdfs/")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_generate_pdf(client):
    """Test generating a PDF"""
    payload = {
        "title": "Test PDF",
        "content": "This is a test PDF generated by API."
    }
    response = client.post("/generate_pdf/", json=payload)

    assert response.status_code == 201
    assert response.json()["message"] == "PDF generated successfully"

def test_get_pdf_sections(client):
    """Test retrieving PDF sections"""
    pdf_id = 1  # Assuming a PDF is uploaded
    response = client.get(f"/pdf/{pdf_id}/sections/?page=1&size=5")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_download_pdf(client):
    """Test downloading a PDF"""
    pdf_id = 1  # Assuming a PDF is available
    response = client.get(f"/download_pdf/{pdf_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
