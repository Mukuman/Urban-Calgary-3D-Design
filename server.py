import os
import re
import json
from flask import Flask, request, jsonify, render_template
# from flask_sqlalchemy import SQLAlchemy
import requests
import pandas as pd
from shapely import wkt
from shapely.geometry import Polygon
from shapely.errors import WKTReadingError
from llm_query import parse_query_with_llm
from dotenv import load_dotenv


load_dotenv()


# -----------------------------------------------------------------------------
# Simple Flask backend for 3D City Dashboard with LLM Querying
# - Fetches building data from Overpass API (Calgary downtown bbox)
# - Exposes endpoints to get buildings, filter via LLM, and persist user projects
# - Uses SQLite via Flask-SQLAlchemy for persistence
# -----------------------------------------------------------------------------

app = Flask(__name__)
# Configure SQLite database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# db = SQLAlchemy(app)

@app.route('/')
def serve_index():
    return render_template('index.html')

# -----------------------------------------------------------------------------
# Database model: Project stores username, project name, and JSON filters
# -----------------------------------------------------------------------------
# class Project(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), nullable=False)
#     project_name = db.Column(db.String(120), nullable=False)
#     filters = db.Column(db.JSON, nullable=False)

# In-memory cache for building data to avoid repeated API calls
buildings_cache = []

# @app.before_first_request
# def init_db():
#     """Create SQLite tables before first request."""
#     db.create_all()

# south = 51.04519365627357
#     west = -114.08381578463135
#     north = 51.049629227864315
#     east = -114.07364009846911

def safe_wkt_loads(wkt_str):
    try:
        if isinstance(wkt_str, str) and wkt_str.strip():
            return wkt.loads(wkt_str)
    except WKTReadingError:
        pass
    return None  # return None if invalid or empty

# -----------------------------------------------------------------------------
# Helper: Fetch building data from saved dataset
# -----------------------------------------------------------------------------

cached_buildings = None
CACHE_FILE = 'buildings_cache.json'

def load_and_filter_buildings(csv_file, bbox_coords):
    # Check for cached 
    global cached_buildings
    if cached_buildings is not None:
        return cached_buildings
    
    if os.path.exists(CACHE_FILE):
        print ("loading from cache")
        with open(CACHE_FILE, 'r') as f:
            cached_buildings = json.load(f)
        return cached_buildings
    
    # Define column names based on your CSV structure
    columns = [
        'grd_elev_min_x', 'grd_elev_max_x', 'grd_elev_min_y', 'grd_elev_max_y',
        'grd_elev_min_z', 'grd_elev_max_z', 'rooftop_elev_x', 'rooftop_elev_y',
        'rooftop_elev_z', 'stage', 'struct_id', 'polygon_wkt'
    ]

    # Load CSV
    df = pd.read_csv(csv_file, names=columns, header=None)

    # Parse polygon WKT to shapely geometries
    df['polygon'] = df['polygon_wkt'].apply(safe_wkt_loads)

    # Then drop rows where polygon failed to parse
    df = df.dropna(subset=['polygon'])

    # Create bounding box polygon
    bbox = Polygon(bbox_coords)

    # Filter buildings by intersection with bbox
    df_filtered = df[df['polygon'].apply(lambda poly: poly.intersects(bbox))].copy()

    df_filtered['rooftop_elev_z'] = pd.to_numeric(df_filtered['rooftop_elev_z'], errors='coerce')
    df_filtered['grd_elev_min_z'] = pd.to_numeric(df_filtered['grd_elev_min_z'], errors='coerce')

    df_filtered = df_filtered.dropna(subset=['rooftop_elev_z', 'grd_elev_min_z'])

    # Calculate building height (in meters)
    df_filtered['height'] = df_filtered['rooftop_elev_z'] - df_filtered['grd_elev_min_z']

    # Prepare list of building dicts to return
    buildings = []
    for _, row in df_filtered.iterrows():
        buildings.append({
            'struct_id': row['struct_id'],
            'height': row['height'],
            'stage': row['stage'],
            'footprint': list(row['polygon'].exterior.coords),
        })

    with open(CACHE_FILE, 'w') as f:
        json.dump(buildings, f)

    cached_buildings = buildings
    return cached_buildings

bbox_coords = [
        (-114.08381578463135, 51.04519365627357),
        (-114.07364009846911, 51.04519365627357),
        (-114.07364009846911, 51.049629227864315),
        (-114.08381578463135, 51.049629227864315),
    ]
csv_path = 'buildings.csv'
# -----------------------------------------------------------------------------
# Endpoint: GET /api/buildings
# Returns all fetched buildings as JSON
# -----------------------------------------------------------------------------
@app.route('/api/buildings', methods=['GET'])
def get_buildings():
    """Return list of all buildings (id, geometry, height, zoning, address, value)."""
    # bbox_coords = [
    #     (-114.08381578463135, 51.04519365627357),
    #     (-114.07364009846911, 51.04519365627357),
    #     (-114.07364009846911, 51.049629227864315),
    #     (-114.08381578463135, 51.049629227864315),
    # ]
    # csv_path = 'buildings.csv'

    buildings_in_bbox = load_and_filter_buildings(csv_path, bbox_coords)
    return jsonify(buildings_in_bbox), 200

# -----------------------------------------------------------------------------
# Endpoint: POST /api/query
# Body: {"query": "highlight buildings over 100 feet"}
# Returns filtered buildings
# -----------------------------------------------------------------------------
@app.route('/api/query', methods=['POST'])
def query_buildings():
    data = request.get_json() or {}
    user_query = data.get('query')
    if not user_query:
        return jsonify({'error': 'Missing "query" field'}), 400

    try:
        flt = parse_query_with_llm(user_query)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    attr = flt.get('attribute')
    op = flt.get('operator')
    val = flt.get('value')

    print("Parsed Query Filter:")
    print(json.dumps(flt, indent=2))

    try:
        val = float(val)
    except (ValueError, TypeError):
        pass

    def matches(b):
        bval = b.get(attr)
        if bval is None:
            return False
        try:
            if attr != "stage":
                bval_num = float(bval)
            else:
                bval_num = bval
        except Exception:
            return False
        if op == '>': return bval_num > val
        if op == '<': return bval_num < val
        if op in ('==', '='): 
            print ("myval " + bval_num + "compared to" + val)
            return bval_num == val
        if op == '!=': return bval_num != val
        return False

    filtered = [b for b in load_and_filter_buildings(csv_path, bbox_coords) if matches(b)]
    return jsonify(filtered), 200
    

# # -----------------------------------------------------------------------------
# # Persistence: Save and load user projects
# # -----------------------------------------------------------------------------
# @app.route('/api/save_project', methods=['POST'])
# def save_project():
#     """Save a project: POST username, project_name, filters JSON."""
#     data = request.get_json() or {}
#     username = data.get('username')
#     project_name = data.get('project_name')
#     filters = data.get('filters')
#     if not all([username, project_name, filters]):
#         return jsonify({'error': 'username, project_name, and filters are required'}), 400

#     proj = Project(username=username, project_name=project_name, filters=filters)
#     db.session.add(proj)
#     db.session.commit()
#     return jsonify({'project_id': proj.id}), 201

# @app.route('/api/load_projects', methods=['GET'])
# def load_projects():
#     """Load list of projects for a given username via ?username=..."""
#     username = request.args.get('username')
#     if not username:
#         return jsonify({'error': 'username is required'}), 400
#     projs = Project.query.filter_by(username=username).all()
#     return jsonify([
#         {'project_id': p.id, 'project_name': p.project_name}
#         for p in projs
#     ]), 200

# @app.route('/api/load_project', methods=['GET'])
# def load_project():
#     """Load filters for a project via ?username=...&project_id=..."""
#     username = request.args.get('username')
#     pid = request.args.get('project_id')
#     if not username or not pid:
#         return jsonify({'error': 'username and project_id are required'}), 400
#     proj = Project.query.filter_by(username=username, id=pid).first()
#     if not proj:
#         return jsonify({'error': 'Project not found'}), 404
#     return jsonify({'filters': proj.filters}), 200

# -----------------------------------------------------------------------------
# Start Flask app
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # print(f"Found {len(buildings_in_bbox)} buildings in bounding box")
    # for b in buildings_in_bbox[:5]:
    #     print(b)
    """Create SQLite tables before first request."""
    # with app.app_context():
    #     db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
    
