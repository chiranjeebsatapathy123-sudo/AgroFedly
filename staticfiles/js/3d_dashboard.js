import * as THREE from 'three';

export function initDashboard3D(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Set up scene
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x10b981, 0.015);
    
    // Set up camera
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 12, 20);
    camera.lookAt(0, 0, 0);

    // Set up renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfffae6, 1.2); // Warm sunlight
    sunLight.position.set(20, 30, 10);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 1024;
    sunLight.shadow.mapSize.height = 1024;
    scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0x90e0ef, 0.4);
    fillLight.position.set(-10, 10, -10);
    scene.add(fillLight);

    // Create a stylized high-tech field (Hexagonal grid look)
    const fieldGeometry = new THREE.PlaneGeometry(30, 30, 30, 30);
    const pos = fieldGeometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
        // Add subtle rolling hills terrain
        const x = pos.getX(i);
        const y = pos.getY(i);
        const z = Math.sin(x * 0.5) * 0.5 + Math.cos(y * 0.5) * 0.5;
        pos.setZ(i, z);
    }
    fieldGeometry.computeVertexNormals();

    const fieldMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x10b981, 
        roughness: 0.9,
        metalness: 0.1,
        wireframe: false
    });
    
    const field = new THREE.Mesh(fieldGeometry, fieldMaterial);
    field.rotation.x = -Math.PI / 2;
    field.receiveShadow = true;
    scene.add(field);

    // Digital Grid overlay for "AI/Tech" feel
    const gridHelper = new THREE.GridHelper(30, 30, 0x059669, 0x059669);
    gridHelper.position.y = 0.05;
    gridHelper.material.transparent = true;
    gridHelper.material.opacity = 0.3;
    scene.add(gridHelper);

    // Advanced Crops Group
    const cropGroup = new THREE.Group();
    scene.add(cropGroup);
    
    const cropGeo = new THREE.CylinderGeometry(0, 0.2, 1, 6);
    const cropMat = new THREE.MeshStandardMaterial({ 
        color: 0x34d399,
        roughness: 0.4,
        emissive: 0x059669,
        emissiveIntensity: 0.2
    });

    const cropNodes = [];
    for (let row = -10; row <= 10; row += 1.5) {
        for (let col = -10; col <= 10; col += 1.5) {
            // Only place crops in a circular radius
            if (row*row + col*col < 80) {
                const crop = new THREE.Mesh(cropGeo, cropMat);
                
                // Get terrain height at this position
                const terrainY = Math.sin(col * 0.5) * 0.5 + Math.cos(row * 0.5) * 0.5;
                
                crop.position.set(col + (Math.random()-0.5)*0.5, terrainY + 0.5, row + (Math.random()-0.5)*0.5);
                crop.castShadow = true;
                crop.userData = {
                    phase: Math.random() * Math.PI * 2,
                    speed: 0.01 + Math.random() * 0.02,
                    baseY: terrainY + 0.5
                };
                cropGroup.add(crop);
                cropNodes.push(crop);
            }
        }
    }

    // AI Scanning Drone (A floating glowing orb that moves over the crops)
    const droneGroup = new THREE.Group();
    scene.add(droneGroup);

    const droneCoreGeo = new THREE.SphereGeometry(0.3, 16, 16);
    const droneCoreMat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: 0x3b82f6,
        emissiveIntensity: 1.5,
        roughness: 0.2
    });
    const droneCore = new THREE.Mesh(droneCoreGeo, droneCoreMat);
    droneGroup.add(droneCore);

    // Drone Scanning Beam
    const beamGeo = new THREE.ConeGeometry(2, 5, 16, 1, true);
    const beamMat = new THREE.MeshBasicMaterial({
        color: 0x3b82f6,
        transparent: true,
        opacity: 0.2,
        side: THREE.DoubleSide,
        depthWrite: false,
        blending: THREE.AdditiveBlending
    });
    const beam = new THREE.Mesh(beamGeo, beamMat);
    beam.position.y = -2.5;
    droneGroup.add(beam);

    // Data Particles flowing up from the field (AI insights)
    const particleGeo = new THREE.BufferGeometry();
    const particleCount = 150;
    const posArray = new Float32Array(particleCount * 3);
    for(let i = 0; i < particleCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 20;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particleMat = new THREE.PointsMaterial({
        size: 0.15,
        color: 0x34d399,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // Animation Loop
    let time = 0;
    function animate() {
        requestAnimationFrame(animate);
        time += 0.01;
        
        // Very slow scene rotation
        scene.rotation.y += 0.001;
        
        // Organic wind effect on crops
        cropNodes.forEach(crop => {
            crop.rotation.z = Math.sin(time * 2 + crop.userData.phase) * 0.1;
            crop.rotation.x = Math.cos(time * 2 + crop.userData.phase) * 0.1;
            // Pulsating emissive for "AI health monitoring" effect
            crop.material.emissiveIntensity = 0.1 + Math.abs(Math.sin(time + crop.userData.phase)) * 0.3;
        });

        // Drone movement (Lissajous curve over the field)
        droneGroup.position.x = Math.sin(time * 0.5) * 8;
        droneGroup.position.z = Math.sin(time * 0.3) * 8;
        // Drone bobbing
        droneGroup.position.y = 5 + Math.sin(time * 2) * 0.5;

        // Animate data particles floating upwards
        const pPositions = particles.geometry.attributes.position.array;
        for (let i = 1; i < particleCount * 3; i += 3) {
            pPositions[i] += 0.02; // Move up
            if (pPositions[i] > 10) {
                pPositions[i] = 0; // Reset to ground
            }
        }
        particles.geometry.attributes.position.needsUpdate = true;

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
