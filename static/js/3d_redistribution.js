import * as THREE from 'three';

export function initRedistribution3D(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Scene Setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x4c1d95, 0.015); // Deep purple fog
    
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 18);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    scene.add(ambientLight);
    
    const coreLight = new THREE.PointLight(0xa855f7, 3, 30);
    coreLight.position.set(0, 0, 0);
    scene.add(coreLight);

    const rimLight = new THREE.DirectionalLight(0xc084fc, 1.5);
    rimLight.position.set(10, 10, -10);
    scene.add(rimLight);

    // Main Neural Network Group
    const networkGroup = new THREE.Group();
    scene.add(networkGroup);

    // AI Core (Pulsating center sphere)
    const coreGeo = new THREE.IcosahedronGeometry(2, 2);
    const coreMat = new THREE.MeshPhysicalMaterial({
        color: 0x7e22ce,
        metalness: 0.8,
        roughness: 0.2,
        wireframe: true,
        emissive: 0x9333ea,
        emissiveIntensity: 0.5
    });
    const core = new THREE.Mesh(coreGeo, coreMat);
    networkGroup.add(core);

    // Create complex distribution nodes (floating around the core)
    const nodeCount = 45;
    const nodes = [];
    const nodeGeo = new THREE.SphereGeometry(0.2, 16, 16);
    const nodeMat = new THREE.MeshBasicMaterial({ color: 0xd8b4fe });

    for (let i = 0; i < nodeCount; i++) {
        // Place nodes in a spherical shell distribution
        const radius = 5 + Math.random() * 6;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos((Math.random() * 2) - 1);
        
        const x = radius * Math.sin(phi) * Math.cos(theta);
        const y = radius * Math.sin(phi) * Math.sin(theta);
        const z = radius * Math.cos(phi);
        
        const node = new THREE.Mesh(nodeGeo, nodeMat);
        node.position.set(x, y, z);
        node.userData = {
            basePos: new THREE.Vector3(x, y, z),
            phase: Math.random() * Math.PI * 2,
            speed: 0.01 + Math.random() * 0.02,
            links: []
        };
        networkGroup.add(node);
        nodes.push(node);
    }

    // Dynamic linking lines (Neural synapes)
    const lineMat = new THREE.LineBasicMaterial({
        color: 0xa855f7,
        transparent: true,
        opacity: 0.2,
        blending: THREE.AdditiveBlending
    });
    
    // We'll update the line geometry every frame based on proximity
    const lineGeo = new THREE.BufferGeometry();
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    networkGroup.add(lines);

    // Data Packets (Redistribution Flow)
    const packetGeo = new THREE.SphereGeometry(0.1, 8, 8);
    const packetMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const packets = [];
    
    for(let i=0; i<20; i++) {
        const packet = new THREE.Mesh(packetGeo, packetMat);
        packet.userData = {
            source: nodes[Math.floor(Math.random()*nodes.length)],
            target: nodes[Math.floor(Math.random()*nodes.length)],
            progress: 0,
            speed: 0.02 + Math.random() * 0.03
        };
        networkGroup.add(packet);
        packets.push(packet);
    }

    let time = 0;
    function animate() {
        requestAnimationFrame(animate);
        time += 0.01;

        // Slow global rotation
        networkGroup.rotation.y += 0.002;
        networkGroup.rotation.z = Math.sin(time * 0.5) * 0.1;

        // Core pulsation
        core.scale.setScalar(1 + Math.sin(time * 4) * 0.05);
        core.rotation.x += 0.01;
        core.rotation.y += 0.005;

        // Animate nodes organic floating
        const positions = [];
        nodes.forEach((node, i) => {
            const phase = node.userData.phase;
            node.position.x = node.userData.basePos.x + Math.sin(time * 2 + phase) * 0.3;
            node.position.y = node.userData.basePos.y + Math.cos(time * 2.5 + phase) * 0.3;
            node.position.z = node.userData.basePos.z + Math.sin(time * 1.5 + phase) * 0.3;

            // Gather close nodes for lines
            for (let j = i + 1; j < nodes.length; j++) {
                if (node.position.distanceTo(nodes[j].position) < 4.5) {
                    positions.push(
                        node.position.x, node.position.y, node.position.z,
                        nodes[j].position.x, nodes[j].position.y, nodes[j].position.z
                    );
                }
            }
        });

        // Update neural lines
        lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        
        // Pulse line opacity
        lines.material.opacity = 0.15 + Math.abs(Math.sin(time * 3)) * 0.15;

        // Move Data Packets along dynamic lines
        packets.forEach(p => {
            p.userData.progress += p.userData.speed;
            
            if (p.userData.progress >= 1) {
                p.userData.progress = 0;
                p.userData.source = p.userData.target;
                // Pick a new random target node
                p.userData.target = nodes[Math.floor(Math.random() * nodes.length)];
            }
            
            p.position.lerpVectors(p.userData.source.position, p.userData.target.position, p.userData.progress);
        });

        renderer.render(scene, camera);
    }
    
    animate();

    window.addEventListener('resize', () => {
        if (!container) return;
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
}
