# test_e12_13.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Распознавание лица (mock)
face_data = {
    "image": "base64_face_image_here",
    "camera_id": "hik_cam_02"
}
resp = requests.post("http://localhost:8001/api/v1/video-alerts/face-match", headers=headers, json=face_data)
print(f"E12.13 Status: {resp.status_code}")
print(f"E12.13 Response: {resp.text[:500]}")
