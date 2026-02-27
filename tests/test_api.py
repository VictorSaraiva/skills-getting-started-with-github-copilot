"""
Tests for the Mergington High School API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Basketball Team": {
            "description": "Join the school basketball team and compete in inter-school matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 6:00 PM",
            "max_participants": 15,
            "participants": ["alex@mergington.edu", "james@mergington.edu"]
        },
    }
    
    # Reset to original state
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Basketball Team" in data
    
    def test_get_activities_includes_participants(self, client):
        """Test that activities include participant lists"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "participants" in data["Chess Club"]
        assert isinstance(data["Chess Club"]["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity(self, client):
        """Test signing up for an existing activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_when_already_registered(self, client):
        """Test signing up when already registered for the activity"""
        # Sign up once
        client.post("/activities/Chess%20Club/signup?email=test@mergington.edu")
        
        # Try to sign up again
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"


class TestGetUserActivities:
    """Tests for GET /users/{email}/activities endpoint"""

    def test_get_activities_for_registered_user(self, client):
        """Test retrieving activities for a student who is registered"""
        response = client.get("/users/michael@mergington.edu/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]

    def test_get_activities_for_unregistered_user(self, client):
        """Test retrieving activities for a student with no registrations"""
        response = client.get("/users/nobody@mergington.edu/activities")
        assert response.status_code == 200
        data = response.json()
        assert data == {}

    def test_get_activities_does_not_include_other_activities(self, client):
        """Test that only activities the student is in are returned"""
        response = client.get("/users/alex@mergington.edu/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Basketball Team" in data
        assert "Chess Club" not in data


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # First, sign up a student
        client.post("/activities/Chess%20Club/signup?email=temp@mergington.edu")
        
        # Then unregister
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=temp@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "temp@mergington.edu" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "temp@mergington.edu" not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant who isn't registered"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Participant not found in this activity"
    
    def test_unregister_original_participant(self, client):
        """Test unregistering an originally registered participant"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
