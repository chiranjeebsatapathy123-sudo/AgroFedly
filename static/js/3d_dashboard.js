import * as THREE from 'three';

export function initDashboard3D(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Set up scene
    const scene = new THREE.Scene();
    
    // Set up camera
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 5, 10);
    camera.lookAt(0, 0, 0);

    // Set up renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 10);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    // Create a stylized field
    const fieldGeometry = new THREE.PlaneGeometry(12, 12, 16, 16);
    
    // Create some terrain variance
    const positionAttribute = fieldGeometry.attributes.position;
    for (let i = 0; i < positionAttribute.count; i++) {
        const x = positionAttribute.getX(i);
        const y = positionAttribute.getY(i);
        
        // Add subtle noise to the z coordinate (which becomes Y when rotated)
        const z = Math.sin(x * 2) * 0.1 + Math.cos(y * 2) * 0.1;
        positionAttribute.setZ(i, z);
    }
    fieldGeometry.computeVertexNormals();

    const fieldMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x27ae60, 
        wireframe: false,
        roughness: 0.8,
        metalness: 0.1
    });
    
    const field = new THREE.Mesh(fieldGeometry, fieldMaterial);
    field.rotation.x = -Math.PI / 2;
    field.receiveShadow = true;
    scene.add(field);

    // Add some stylized crops
    const cropGroup = new THREE.Group();
    
    // Add multiple crop rows
    for (let row = -4; row <= 4; row += 2) {
        for (let col = -4; col <= 4; col += 1.5) {
            // Randomize slightly
            const rX = col + (Math.random() - 0.5) * 0.5;
            const rZ = row + (Math.random() - 0.5) * 0.2;
            
            const cropGeometry = new THREE.ConeGeometry(0.3, 1, 8);
            const cropMaterial = new THREE.MeshStandardMaterial({ 
                color: 0x2ecc71,
                roughness: 0.6 
            });
            const crop = new THREE.Mesh(cropGeometry, cropMaterial);
            
            crop.position.set(rX, 0.5, rZ);
            crop.castShadow = true;
            
            // Add a small animation offset
            crop.userData = {
                phase: Math.random() * Math.PI * 2,
                speed: 0.02 + Math.random() * 0.02
            };
            
            cropGroup.add(crop);
        }
    }
    scene.add(cropGroup);

    // Animation Loop
    function animate() {
        requestAnimationFrame(animate);
        
        // Slowly rotate the entire field for effect
        scene.rotation.y += 0.002;
        
        // Subtle wind effect on crops
        const time = Date.now() * 0.001;
        cropGroup.children.forEach(crop => {
            crop.rotation.z = Math.sin(time + crop.userData.phase) * 0.1;
            crop.rotation.x = Math.cos(time + crop.userData.phase) * 0.1;
        });

        renderer.render(scene, camera);
    }
    
    animate();

    // Handle Resize
    window.addEventListener('resize', () => {
        if (!container) return;
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
}
