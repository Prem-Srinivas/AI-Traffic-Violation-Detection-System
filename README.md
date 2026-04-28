🚦 AI Traffic Violation Detection System
📌 Overview

The AI Traffic Violation Detection System is a real-time computer vision project that automatically detects traffic rule violations using deep learning.

This system analyzes video streams from CCTV cameras or recorded footage and identifies violations such as:

🪖 No Helmet Detection
👨‍👨‍👦 Triple Riding
🚗 Vehicle Detection
⚡ Over-speeding (optional)
🚧 Wrong Direction (optional)

The goal is to reduce manual monitoring and improve road safety using AI automation.

🎯 Features
🎥 Real-time video processing
🧠 AI-based object detection using YOLO
🏍️ Helmet and rider detection
🚗 Vehicle detection and tracking
⚠️ Automatic violation detection
💾 Save violation images/videos
📊 Logs for analysis
🛠️ Technologies Used
Language: Python
Libraries: OpenCV, NumPy
Deep Learning Models: YOLOv5 / YOLOv8
Frameworks: PyTorch / TensorFlow
IDE: VS Code
🧠 System Architecture
Video Input (CCTV / Camera / Video file)
Frame Extraction
Object Detection (YOLO Model)
Rider & Helmet Classification
Violation Detection Logic
Output Display & Storage
⚙️ Installation
1️⃣ Clone the Repository
git clone https://github.com/Prem-Srinivas/AI-Traffic-Violation-Detection-System.git
cd AI-Traffic-Violation-Detection-System
2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate   # For Windows
3️⃣ Install Dependencies
pip install -r requirements.txt
▶️ Usage
python main.py

👉 Steps:

Run the script
Provide input video or camera
System will detect and display violations in real-time
📂 Project Structure
AI-Traffic-Violation-Detection-System/
│
├── models/              # Trained models
├── dataset/             # Training data
├── outputs/             # Detected results
├── utils/               # Helper functions
├── main.py              # Main execution file
├── detect.py            # Detection logic
├── requirements.txt     # Dependencies
└── README.md            # Documentation
📸 Output
Bounding boxes on vehicles and riders
Highlighted violations
Saved images of detected violations
Real-time video output
🔒 Future Enhancements
📱 Mobile App Integration
☁️ Cloud Deployment
🚓 Integration with Traffic Police Systems
🪪 Automatic License Plate Recognition (ALPR)
📊 Dashboard with analytics
👨‍💻 Author

Prem Srinivas
B.Tech Student | AI & Full Stack Developer

📜 License

This project is developed for academic and learning purposes.
