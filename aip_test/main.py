import os
import cv2
import yaml
import json
import natsort
import cloudinary
import cloudinary.uploader
from io import BytesIO
from datetime import date
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from auth.auth_routes import router as auth_router
from auth.otp_service import send_download_link_email, send_rejection_email
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, HTTPException


BASE_DIR = os.path.dirname(os.path.abspath(__file__))



##app_init
app = FastAPI(title="AIP-API's")
app.include_router(auth_router)

##cors_config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

##global_state
PROJECTS_STATUS = {}
ACTIVE_PROJECT_ID = None  # Tracks current project for get-result and get-analytics

##project_mapping
PROJECT_PATH_MAP = {
    "001": os.path.join(BASE_DIR, "Datasets", "counting of animals.v1i.yolov12", "train"),
    "002": os.path.join(BASE_DIR, "Datasets", "Mining Vehicles.v1i.yolov12", "train"),
    "003": os.path.join(BASE_DIR, "Datasets", "Vehicle Detection.v1i.yolov12", "train"),
}

##storage_paths
OUTPUT_DIR = "output_annotated_images"
UPLOAD_DIR = "uploaded_files"
ALERTS_FILE = "alerts-page.json"
PROJECTS_FILE = "demo_website_db.projects.json"
ADMIN_MANAGEMENT_DATA = "admin management data.json"
USER_MANAGEMENT_DATA = "user management data.json"
CLIENT_MANAGEMENT = "clients.json"
ADMIN_DASHBOARD = "Admin_dashboard.json"
INDUSTRIES = "industries.json"
RECENT_PROJECTS = "recent_projects.json"

##dir_setup
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

##cloudinary_auth
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

##schemas
class StartProcessRequest(BaseModel):
    project_id: str 

class RejectionRequest(BaseModel):
    image_id: str
    image_url: str

# ================================
# HELPERS
# ================================
def is_project_cached(project_id: str) -> bool:
    return os.path.exists(f"imageData_{project_id}.json")

def load_cached_result(project_id: str) -> dict:
    with open(f"imageData_{project_id}.json", "r") as f:
        return json.load(f)


##analytics_helper - UPDATED TO BE PROJECT SPECIFIC
def update_analytics_data(final_data: dict, project_id: str):
    species_stats = {}
    gallery = []
    area_data = []
    line_data = []
    colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
    running_totals = {}

    for i, img in enumerate(final_data["images"]):
        img_id = img["id"]
        url = img["mainImage"]
        count = 0
        categories_str = "None"
        for metric in img["metrics"]:
            if metric["label"] == "Total Count":
                count = int(metric["value"])
            if metric["label"] == "Categories":
                categories_str = metric["value"]

        gallery.append({"id": img_id, "url": url, "species": categories_str, "count": count})
        
        labels = [l.strip() for l in categories_str.split(",")]
        for label in labels:
            if label == "None" or label == "": continue
            if label not in species_stats:
                species_stats[label] = {"Total": 0, "Images": 0}
            species_stats[label]["Total"] += count
            species_stats[label]["Images"] += 1
            running_totals[label] = running_totals.get(label, 0) + count

        line_data.append({"name": f"Observation {i+1}", "Detections": count, "Confidence": 95})
        area_entry = {"name": f"Batch {i+1}"}
        area_entry.update(running_totals)
        area_data.append(area_entry)

    dashboard_json = {
        "barData": [{"name": k, "Total": v["Total"], "Images": v["Images"]} for k, v in species_stats.items()],
        "pieData": [{"name": k, "value": v["Total"], "color": colors[idx % len(colors)]} for idx, (k, v) in enumerate(species_stats.items())],
        "areaData": area_data,
        "lineData": line_data,
        "gallery": gallery
    }

    # Save unique analytics file per project
    analytics_filename = f"analytics_{project_id}.json"
    with open(analytics_filename, "w") as f:
        json.dump(dashboard_json, f, indent=2)

##pipeline_logic
def run_pipeline(project_id: str, train_path: str):
    global PROJECTS_STATUS
    PROJECTS_STATUS[project_id] = {"running": True, "completed": False, "result": None}

    try:
        project_root = os.path.dirname(train_path)
        dynamic_yaml_path = os.path.join(project_root, "data.yaml")
        if not os.path.exists(dynamic_yaml_path):
            raise Exception(f"data.yaml not found at {dynamic_yaml_path}")

        with open(dynamic_yaml_path, "r") as f:
            data = yaml.safe_load(f)
        CLASS_NAMES = data["names"]
        IMAGES_DIR = os.path.join(train_path, "images")
        LABELS_DIR = os.path.join(train_path, "labels")
        today_date = date.today().isoformat()
        final_data = {"project_id": project_id, "images": []}
        image_list = natsort.natsorted(os.listdir(IMAGES_DIR))

        for idx, img_name in enumerate(image_list, start=101):
            if not img_name.lower().endswith((".jpg", ".jpeg", ".png")): continue
            image_path = os.path.join(IMAGES_DIR, img_name)
            label_path = os.path.join(LABELS_DIR, os.path.splitext(img_name)[0] + ".txt")
            img = cv2.imread(image_path)
            if img is None: continue
            h, w = img.shape[:2]
            detection_count = 0
            found_classes = set()

            if os.path.exists(label_path):
                with open(label_path, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) < 5: continue
                    cls, x, y, bw, bh = map(float, parts[:5])
                    label = CLASS_NAMES[int(cls)] if int(cls) < len(CLASS_NAMES) else f"Unknown({int(cls)})"
                    detection_count += 1
                    found_classes.add(label)
                    x1, y1 = int((x - bw/2)*w), int((y - bh/2)*h)
                    x2, y2 = int((x + bw/2)*w), int((y + bh/2)*h)
                    
                    # DRAWING LOGIC
                    # 1. Draw the Bounding Box (Red)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0,0,255), 2)
                    
                    # 2. Add the Label Name
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    # Place text slightly above the box; if at top of image, move inside box
                    text_position = (x1, y1 - 10 if y1 > 20 else y1 + 20)
                    cv2.putText(img, label, text_position, font, 0.6, (0, 0, 255), 2, cv2.LINE_AA)

            output_filename = f"{project_id}_{img_name}"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            cv2.imwrite(output_path, img)
            upload_result = cloudinary.uploader.upload(output_path)
            final_data["images"].append({
                "id": idx, "mainImage": upload_result["secure_url"],
                "cardTitle": f"Detection: {project_id}",
                "meta": {"date": today_date, "location": "Analysis Lab"},
                "sectionTitle": "Object Statistics",
                "metrics": [
                    {"label": "Total Count", "value": str(detection_count)},
                    {"label": "Categories", "value": ", ".join(found_classes) if found_classes else "None"}
                ]
            })

        # Save specific results
        with open(f"imageData_{project_id}.json", "w") as f:
            json.dump(final_data, f, indent=2)

        # Update specific analytics
        update_analytics_data(final_data, project_id)

        PROJECTS_STATUS[project_id]["result"] = final_data
        PROJECTS_STATUS[project_id]["completed"] = True
    except Exception as e:
        PROJECTS_STATUS[project_id]["result"] = {"error": str(e)}
    finally:
        PROJECTS_STATUS[project_id]["running"] = False

##DASHBOARDS
@app.get("/get-SuperAdmin_Dashboard", tags=["Dashboard API's"])
def Admin_Dashboard():
    if not os.path.exists(ADMIN_DASHBOARD):
        return []
    with open(ADMIN_DASHBOARD, "r") as f:
        return json.load(f)


@app.get("/get-Client_Management_Dashboard", tags=["Dashboard API's"])
def Client_Management():
    if not os.path.exists(CLIENT_MANAGEMENT):
        return []
    with open(CLIENT_MANAGEMENT, "r") as f:
        return json.load(f)

@app.get("/get-Industries", tags=["Dashboard API's"])
def Industries():
    if not os.path.exists(INDUSTRIES):
        return []
    with open(INDUSTRIES, "r") as f:
        return json.load(f)


@app.get("/get-Recent_Projects", tags=["Dashboard API's"])
def Recent_projects():
    if not os.path.exists(RECENT_PROJECTS):
        return []
    with open(RECENT_PROJECTS, "r") as f:
        return json.load(f)

##api_file_upload
@app.post("/upload-file",tags=["File API's"])
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        upload_result = cloudinary.uploader.upload(contents, resource_type="raw", public_id=file.filename)
        send_download_link_email(upload_result["secure_url"])
        return {"status": "success", "download_link": upload_result["secure_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reject-image",tags=["File API's"])
def reject_image(request: RejectionRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_rejection_email, request.image_id, request.image_url)
    return {"status": "success"}

##api_process

@app.post("/start-processing", tags=["Process API"])
def start_processing(request: StartProcessRequest, background_tasks: BackgroundTasks):
    global LAST_PROJECT_ID, PROJECTS_STATUS

    # 1️⃣ Normalize project ID
    project_id = request.project_id.zfill(3)
    LAST_PROJECT_ID = project_id

    # ✅ TERMINAL LOG (THIS IS WHAT YOU WANT)
    print(f"📌 API HIT: /start-processing | project_id = {project_id}")

    # 2️⃣ Validate project mapping
    train_path = PROJECT_PATH_MAP.get(project_id)
    if not train_path:
        print(f"❌ INVALID PROJECT ID: {project_id}")
        raise HTTPException(status_code=404, detail="Project ID not mapped")

    # 3️⃣ Cache check
    if is_project_cached(project_id):
        print(f"✅ CACHE HIT: Project {project_id} loaded from Cloudinary")
        PROJECTS_STATUS[project_id] = {
            "running": False,
            "completed": True,
            "cached": True
        }
        return {
            "message": f"Project {project_id} already processed",
            "cached": True
        }

    # 4️⃣ Start processing
    PROJECTS_STATUS[project_id] = {
        "running": True,
        "completed": False,
        "cached": False
    }

    background_tasks.add_task(run_pipeline, project_id, train_path)

    return {
        "message": f"Processing started for {project_id}",
        "cached": False
    }


##api_results
@app.get("/get-result", tags=["Result API"])
def get_result():
    global LAST_PROJECT_ID

    # 1️⃣ No project started yet
    if not LAST_PROJECT_ID:
        return {
            "images": [],
            "message": "No project started yet"
        }

    project_id = LAST_PROJECT_ID
    status = PROJECTS_STATUS.get(project_id)

    # 2️⃣ Project is still running
    if status and status.get("running"):
        return {
            "project_id": project_id,
            "images": [{
                "id": "",
                "mainImage": "https://via.placeholder.com/600x400?text=Processing",
                "cardTitle": "Processing...",
                "meta": {"date": "", "location": ""},
                "sectionTitle": "Processing",
                "metrics": []
            }]
        }

    # 3️⃣ Project completed in current session
    if status and status.get("completed"):
        file_path = f"imageData_{project_id}.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)

    # 4️⃣ Server restart safe (load from disk cache)
    file_path = f"imageData_{project_id}.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    # 5️⃣ Fallback
    return {
        "images": [],
        "message": "Result not available yet"
    }


##api_analytics
@app.get("/get-analytics", tags=["Analytical API's"])
def get_analytics():
    global LAST_PROJECT_ID
   
    if not LAST_PROJECT_ID:
        return {
            "error": "No project started yet"
        }

    project_id = LAST_PROJECT_ID
    analytics_file = f"analytics_{project_id}.json"

    if not os.path.exists(analytics_file):
        return {
            "error": "Analytics not available yet"
        }
   
    with open(analytics_file, "r") as f:
        return json.load(f)

##ALERTS
@app.get("/get-alerts", tags=["Alerts API"])
def alerts():
    if not os.path.exists(ALERTS_FILE): return []
    with open(ALERTS_FILE, "r") as f: return json.load(f)

##PROJECTS
@app.get("/get-projects", tags=["Projects API"])
def projects():
    if not os.path.exists(PROJECTS_FILE): return []
    with open(PROJECTS_FILE, "r") as f: return json.load(f)

##MANAGEMENT
@app.get("/get-Admin_Management_data", tags=["Management API's"])
def Admin_Management_data():
    if not os.path.exists(ADMIN_MANAGEMENT_DATA):
        raise HTTPException(status_code=404, detail=f"File not found: {ADMIN_MANAGEMENT_DATA}")
    with open(ADMIN_MANAGEMENT_DATA, "r") as f:
        return json.load(f)

@app.get("/get-User_Management_data", tags=["Management API's"])
def ser_Management_data():
    if not os.path.exists(USER_MANAGEMENT_DATA): return []
    with open(USER_MANAGEMENT_DATA, "r") as f: return json.load(f)


















