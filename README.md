# 3D City Dashboard

An interactive 3D city visualization dashboard that allows users to query Calgary buildings using natural language, powered by a Flask backend and Hugging Face’s LLM API.

[🌐 Live App on Render](https://urban-calgary-3d-design.onrender.com/)

---

## 📦 Features

- 🌇 3D Visualization of Calgary buildings using **Three.js**
- 🧠 Natural language queries via **Hugging Face Inference API**
- 🔍 Highlight buildings that match user queries
- 🧼 Clear query/reset highlights
- 🗃️ (Planned) Store user/project data with SQLite

---

## 🧰 Tech Stack

- **Frontend:** JavaScript, React, Three.js
- **Backend:** Python (Flask, Pandas, Shapely)
- **Database:** SQLite (planned for project persistence)
- **LLM:** Hugging Face Inference API
- **Deployment:** [Render.com](https://render.com)

---

## 🚀 Live Demo

👉 [https://urban-calgary-3d-design.onrender.com/](https://urban-calgary-3d-design.onrender.com/)

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
### 2. Create a Virtual Environment
```
bash
Copy
Edit
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install Python Requirements
```
pip install -r requirements.txt
```
### 4. Add Environment Variables
Create a .env file in the project root:

```
.env
HUGGINGFACE_API_KEY=your_huggingface_api_key

You can get a free Hugging Face token at: https://huggingface.co/settings/tokens
```

### 5. Run the Backend Server

python ./server.py
Visit the link provided to view it locally.

Parameters for the query currently contain height, and status (new or contructed) as according to dataset.