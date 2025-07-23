import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let INTERSECTED;  // currently hovered building
const buildingMeshes = [];  // store all building meshes with their data
let highlightedBuildings = [];

// html index container
const container = document.getElementById('container');
const defaultColor = new THREE.Color(0xa0aebc);

// setting up the 3d scene

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeeeeee);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 5000);
camera.position.set(-221.9077034413541, 232.26971930673085, 586.9923219862362);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

controls.target.set(307.2094496160439, -240.37996855992088, 124.38433392531955);
controls.addEventListener('change', () => {
  console.log('Camera position:', camera.position);
  console.log('Controls target:', controls.target);
});

const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(10, 10, 10);
scene.add(light);

const ambientLight = new THREE.AmbientLight(0xffffff); 
scene.add(ambientLight);

function animate() {
  requestAnimationFrame(animate);

  controls.update();
  renderer.render(scene, camera);
}

animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
  // camera.position.set(0, 100, 100); // Pull back from buildings
  // camera.lookAt(0, 0, 0);
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function projectCoords(lon, lat, originLon, originLat) {
  const scale = 100000; // tweak this
  const x = (lon - originLon) * scale;
  const y = (lat - originLat) * scale;
  return [x, y];
}

async function fetchBuildings() {
  const res = await fetch('/api/buildings');
  const buildings = await res.json();

  if (buildings.length === 0) return;

  // Use first building as origin
  const [originLon, originLat] = buildings[0].footprint[0];

  buildings.forEach(b => {
    const shape = new THREE.Shape();

    b.footprint.forEach(([lon, lat], i) => {
      const [x, y] = projectCoords(lon, lat, originLon, originLat);
      if (i === 0) shape.moveTo(x, y);
      else shape.lineTo(x, y);
    });

    const extrudeSettings = {
      depth: b.height,
      bevelEnabled: false
    };

    const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    const material = new THREE.MeshStandardMaterial({ color: defaultColor, opacity: 0.9, transparent: true });
    const mesh = new THREE.Mesh(geometry, material);



    // Raise building from ground
    // mesh.position.z = 0;
    mesh.position.y = -b.height / 2;  // shifts building down so base aligns with ground
    mesh.rotation.x = -Math.PI / 2; // Rotate 90° to stand upright (Z becomes Y)
    mesh.userData = b;
    buildingMeshes.push(mesh);
    scene.add(mesh);
  });

  setupBuildingHoverPreview();
}
fetchBuildings();

function setupBuildingHoverPreview() {
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let INTERSECTED = null;

  // Create info box once
  const infoBox = document.createElement('div');
  infoBox.id = 'infoBox';
  infoBox.style.position = 'absolute';
  infoBox.style.background = 'white';
  infoBox.style.padding = '8px';
  infoBox.style.borderRadius = '5px';
  infoBox.style.boxShadow = '0 0 5px rgba(0,0,0,0.3)';
  infoBox.style.pointerEvents = 'none';
  infoBox.style.fontSize = '14px';
  infoBox.style.fontFamily = 'Arial';
  infoBox.style.display = 'none';
  document.body.appendChild(infoBox);

  // Mouse move listener
  window.addEventListener('mousemove', (event) => {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = - (event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(buildingMeshes);

    if (intersects.length > 0) {
      const intersected = intersects[0].object;

      // highlight a new building, if the old one doesnt work anymore
      if (INTERSECTED !== intersected) {
        if (INTERSECTED) INTERSECTED.material.color.set(0xa0aebc);
        INTERSECTED = intersected;
        INTERSECTED.material.color.set(0xffaa00); // highlight

        const b = INTERSECTED.userData;
        infoBox.innerHTML = `
          <b>ID:</b> ${b.struct_id} <br>
          <b>Height:</b> ${b.height.toFixed(2)} m <br>
          <b>Status:</b> ${b.stage}
        `;
        infoBox.style.display = 'block';
      }

      infoBox.style.left = (event.clientX + 15) + 'px';
      infoBox.style.top = (event.clientY + 15) + 'px';
    } else {
      if (INTERSECTED) INTERSECTED.material.color.set(0xa0aebc);
      INTERSECTED = null;
      infoBox.style.display = 'none';
    }
  });
}

function setupQueryFormHandler() {
  const form = document.getElementById('query-form');

  if (!form) {
    console.error("Query form not found!");
    return;
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const queryInput = document.getElementById('query-input');
    const query = queryInput.value.trim();
    const errorElem = document.getElementById('query-error');
    const resultsElem = document.getElementById('query-results');

    clearHighlights();

    errorElem.textContent = '';
    // resultsElem.innerHTML = 'Loading...';

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      const data = await res.json();

      if (!res.ok) {
        errorElem.textContent = data.error || 'Something went wrong.';
        // resultsElem.innerHTML = '';
        return;
      }

      if (data.length === 0) {
        // resultsElem.innerHTML = '<p>No matching buildings found.</p>';
      } else {
        // resultsElem.innerHTML = `<ul>${data.map(b =>
        //   `<li>${b.name || 'Unnamed'} — ${b.height || '?'}m tall</li>`
        // ).join('')}</ul>`;
        highlightBuildings(data);
      }
    } catch (err) {
      errorElem.textContent = 'Server error';
      resultsElem.innerHTML = '';
    }
  });
}
// Run once DOM is ready
window.addEventListener('DOMContentLoaded', setupQueryFormHandler);


const highlightColor = new THREE.Color(0xffaa00);


function highlightBuildings(filteredBuildings) {

  // Create a Set of IDs from filtered buildings for faster lookup
  const filteredIds = new Set(filteredBuildings.map(b => b.struct_id));

  buildingMeshes.forEach(mesh => {
    if (filteredIds.has(mesh.userData.struct_id)) {
      mesh.material.color.copy(highlightColor);
    } 
    // else {
    //   mesh.material.color.copy(defaultColor);
    // }
  });
}

function clearHighlights() {
  buildingMeshes.forEach(mesh => {
    mesh.material.color.copy(defaultColor);
  });
}

document.getElementById('clear-query-btn').addEventListener('click', () => {
  clearHighlights();
  document.getElementById('query-results').innerHTML = '';
  document.getElementById('query-input').value = '';
  document.getElementById('query-error').textContent = '';
});
