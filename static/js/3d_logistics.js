import * as THREE from 'three';

export function initLogistics3D(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Scene Setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x1e3a8a, 0.015); // Deep blue fog
    
    // Camera
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 15, 20);
    camera.lookAt(0, 0, 0);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const blueLight = new THREE.PointLight(0x3b82f6, 3, 50);
    blueLight.position.set(0, 5, 0);
    scene.add(blueLight);

    const cyanLight = new THREE.DirectionalLight(0x06b6d4, 1);
    cyanLight.position.set(10, 10, 10);
    scene.add(cyanLight);

    // AI Grid Floor (Logistics Map)
    const gridHelper = new THREE.GridHelper(40, 40, 0x3b82f6, 0x1e40af);
    gridHelper.position.y = -0.5;
    gridHelper.material.transparent = true;
    gridHelper.material.opacity = 0.4;
    scene.add(gridHelper);

    // Holographic City / Logistics Hubs (Low Poly Blocks)
    const hubsGroup = new THREE.Group();
    scene.add(hubsGroup);
    
    const hubGeo = new THREE.BoxGeometry(1, 1, 1);
    const hubMat = new THREE.MeshPhysicalMaterial({
        color: 0x1e3a8a,
        metalness: 0.9,
        roughness: 0.1,
        transmission: 0.5,
        emissive: 0x2563eb,
        emissiveIntensity: 0.2
    });

    const hubs = [];
    for (let i = 0; i < 12; i++) {
        const height = 1 + Math.random() * 3;
        const mesh = new THREE.Mesh(hubGeo, hubMat);
        mesh.scale.set(1 + Math.random(), height, 1 + Math.random());
        mesh.position.set(
            (Math.random() - 0.5) * 30,
            height / 2 - 0.5,
            (Math.random() - 0.5) * 30
        );
        hubsGroup.add(mesh);
        hubs.push(mesh.position.clone().setY(0));
    }

    // Dynamic Route Lines (connecting hubs)
    const lineMat = new THREE.LineBasicMaterial({
        color: 0x60a5fa,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending
    });
    
    const routes = [];
    for (let i = 0; i < hubs.length - 1; i++) {
        const points = [];
        points.push(hubs[i]);
        // Arc up for route path
        const midPoint = new THREE.Vector3().addVectors(hubs[i], hubs[i+1]).multiplyScalar(0.5);
        midPoint.y = 2 + Math.random() * 2; // arc height
        
        const curve = new THREE.QuadraticBezierCurve3(hubs[i], midPoint, hubs[i+1]);
        const curvePoints = curve.getPoints(20);
        const geometry = new THREE.BufferGeometry().setFromPoints(curvePoints);
        const line = new THREE.Line(geometry, lineMat);
        scene.add(line);
        routes.push(curve);
    }

    // Moving Fleet Vehicles (Data Packets traversing routes)
    const fleetGroup = new THREE.Group();
    scene.add(fleetGroup);

    const vehicleGeo = new THREE.SphereGeometry(0.2, 8, 8);
    const vehicleMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
    
    const vehicles = [];
    for (let i = 0; i < 15; i++) {
        const v = new THREE.Mesh(vehicleGeo, vehicleMat);
        v.userData = {
            routeIndex: Math.floor(Math.random() * routes.length),
            progress: Math.random(),
            speed: 0.005 + Math.random() * 0.01
        };
        fleetGroup.add(v);
        vehicles.push(v);
    }

    // AI Radar Scan Ring
    const radarGeo = new THREE.TorusGeometry(0.1, 0.05, 16, 64);
    const radarMat = new THREE.MeshBasicMaterial({
        color: 0x60a5fa,
        transparent: true,
        opacity: 0.8,
        side: THREE.DoubleSide
    });
    const radar = new THREE.Mesh(radarGeo, radarMat);
    radar.rotation.x = Math.PI / 2;
    radar.position.y = -0.4;
    scene.add(radar);

    let time = 0;
    function animate() {
        requestAnimationFrame(animate);
        time += 0.01;

        // Camera gentle sway
        camera.position.x = Math.sin(time * 0.3) * 5;
        camera.position.z = 20 + Math.cos(time * 0.2) * 5;
        camera.lookAt(0, 0, 0);

        // Radar expansion
        radar.scale.setScalar(radar.scale.x + 0.1);
        radar.material.opacity -= 0.005;
        if (radar.scale.x > 30) {
            radar.scale.setScalar(0.1);
            radar.material.opacity = 0.8;
        }

        // Animate Hubs pulsing
        hubsGroup.children.forEach((hub, idx) => {
            hub.material.emissiveIntensity = 0.1 + Math.abs(Math.sin(time * 3 + idx)) * 0.5;
        });

        // Move Vehicles along quadratic bezier routes
        vehicles.forEach(v => {
            v.userData.progress += v.userData.speed;
            if (v.userData.progress > 1) {
                v.userData.progress = 0;
                v.userData.routeIndex = Math.floor(Math.random() * routes.length);
            }
            const route = routes[v.userData.routeIndex];
            const pos = route.getPointAt(v.userData.progress);
            v.position.copy(pos);
            
            // Pulse vehicle size
            const pulse = 1 + Math.sin(time * 10 + v.userData.progress * 10) * 0.3;
            v.scale.setScalar(pulse);
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
