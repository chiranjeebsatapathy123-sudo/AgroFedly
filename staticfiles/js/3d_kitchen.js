import * as THREE from 'three';

export function initKitchen3D(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xf59e0b, 0.012); // Warm orange fog
    
    // Camera setup
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 10, 16);
    camera.lookAt(0, 0, 0);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    
    const keyLight = new THREE.DirectionalLight(0xffa500, 1.5); // Orange/Warm
    keyLight.position.set(15, 20, 10);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 1024;
    keyLight.shadow.mapSize.height = 1024;
    scene.add(keyLight);

    const ovenLight = new THREE.PointLight(0xff4500, 2, 20); // Deep fire red/orange
    ovenLight.position.set(0, 2, -5);
    scene.add(ovenLight);

    const scanLight = new THREE.SpotLight(0x3b82f6, 4, 30, Math.PI / 6, 0.5, 1);
    scanLight.position.set(0, 15, 0);
    scanLight.castShadow = true;
    scene.add(scanLight);

    // AI Production Conveyor System
    const conveyorGroup = new THREE.Group();
    scene.add(conveyorGroup);

    // Conveyor Belt Base
    const beltGeo = new THREE.BoxGeometry(24, 0.5, 6);
    const beltMat = new THREE.MeshStandardMaterial({ 
        color: 0x222222, 
        metalness: 0.8, 
        roughness: 0.2,
        emissive: 0x111111 
    });
    const belt = new THREE.Mesh(beltGeo, beltMat);
    belt.receiveShadow = true;
    conveyorGroup.add(belt);

    // Conveyor Grid Lines (Movement effect)
    const gridHelper = new THREE.GridHelper(24, 12, 0xf59e0b, 0xf59e0b);
    gridHelper.position.y = 0.26;
    gridHelper.material.transparent = true;
    gridHelper.material.opacity = 0.5;
    conveyorGroup.add(gridHelper);

    // Meal Modules moving along the belt
    const modulesGroup = new THREE.Group();
    conveyorGroup.add(modulesGroup);

    const moduleGeo = new THREE.BoxGeometry(1.5, 0.8, 1.5);
    
    const meals = [];
    for (let i = 0; i < 6; i++) {
        // High-tech translucent boxes
        const mat = new THREE.MeshPhysicalMaterial({ 
            color: new THREE.Color().setHSL(0.08 + Math.random() * 0.05, 0.9, 0.5),
            metalness: 0.2,
            roughness: 0.1,
            transmission: 0.6,
            thickness: 0.5,
            emissive: 0xd97706,
            emissiveIntensity: 0.2
        });
        const box = new THREE.Mesh(moduleGeo, mat);
        box.position.set(-12 + i * 4, 0.65, (Math.random() - 0.5) * 2);
        box.castShadow = true;
        box.userData = { 
            speed: 0.03 + Math.random() * 0.01, 
            phase: Math.random() * Math.PI * 2,
            baseZ: box.position.z 
        };
        modulesGroup.add(box);
        meals.push(box);
    }

    // Advanced AI Scanner Arch (Quality Control)
    const archGeo = new THREE.TorusGeometry(3, 0.2, 16, 32, Math.PI);
    const archMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.9, roughness: 0.1 });
    const arch = new THREE.Mesh(archGeo, archMat);
    arch.rotation.y = Math.PI / 2;
    arch.position.set(0, 0.5, 0);
    conveyorGroup.add(arch);

    // Scanning Laser Beam inside the Arch
    const laserGeo = new THREE.PlaneGeometry(6, 4);
    const laserMat = new THREE.MeshBasicMaterial({
        color: 0x3b82f6,
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });
    const laser = new THREE.Mesh(laserGeo, laserMat);
    laser.rotation.y = Math.PI / 2;
    laser.position.set(0, 2.5, 0);
    conveyorGroup.add(laser);

    // Thermal Steam / Particles Simulation
    const particleGeo = new THREE.BufferGeometry();
    const particleCount = 200;
    const posArray = new Float32Array(particleCount * 3);
    for(let i=0; i < particleCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 16;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particleMat = new THREE.PointsMaterial({
        size: 0.2,
        color: 0xfca5a5,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    particles.position.y = 1;
    scene.add(particles);

    let time = 0;
    function animate() {
        requestAnimationFrame(animate);
        time += 0.01;

        // Gentle camera float
        camera.position.x = Math.sin(time * 0.5) * 2;
        camera.position.y = 10 + Math.cos(time * 0.7) * 1;
        camera.lookAt(0, 0, 0);

        // Move Grid to simulate belt motion
        gridHelper.position.x = (time * 3) % 2 - 1;

        // Move Meals along the conveyor
        meals.forEach(meal => {
            meal.position.x += meal.userData.speed;
            meal.position.z = meal.userData.baseZ + Math.sin(time * 5 + meal.userData.phase) * 0.1;
            
            // Interaction with Scanner Arch
            if (Math.abs(meal.position.x) < 1.5) {
                meal.material.emissive.setHex(0x3b82f6); // Turns blue while scanned
                meal.material.emissiveIntensity = 0.8;
            } else {
                meal.material.emissive.setHex(0xd97706);
                meal.material.emissiveIntensity = 0.2;
            }

            if (meal.position.x > 12) {
                meal.position.x = -12; // Wrap around
            }
        });

        // Pulsate Laser
        laser.material.opacity = 0.2 + Math.abs(Math.sin(time * 10)) * 0.2;

        // Animate Thermal Steam Particles
        const pPositions = particles.geometry.attributes.position.array;
        for (let i = 1; i < particleCount * 3; i += 3) {
            pPositions[i] += 0.03; // Drift up
            pPositions[i-1] += Math.sin(time * 2 + pPositions[i]) * 0.01; // Drift sideways
            
            if (pPositions[i] > 8) {
                pPositions[i] = 0; // Reset to belt level
            }
        }
        particles.geometry.attributes.position.needsUpdate = true;

        // Oven light flickering
        ovenLight.intensity = 2 + Math.random() * 0.5;

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
