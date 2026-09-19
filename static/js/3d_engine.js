import * as THREE from 'three';

class AICore {
    constructor(scene, isDark) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.isDark = isDark;
        
        // The core sphere
        const geometry = new THREE.IcosahedronGeometry(2, 2);
        this.material = new THREE.MeshPhysicalMaterial({
            color: 0x159653,
            emissive: 0x0a4a29,
            emissiveIntensity: 0.5,
            wireframe: true,
            transparent: true,
            opacity: 0.8,
            roughness: 0.2,
            metalness: 0.8
        });
        
        this.mesh = new THREE.Mesh(geometry, this.material);
        this.group.add(this.mesh);
        
        // Inner core
        const innerGeo = new THREE.IcosahedronGeometry(1.2, 1);
        this.innerMaterial = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.2
        });
        this.innerMesh = new THREE.Mesh(innerGeo, this.innerMaterial);
        this.group.add(this.innerMesh);

        // Core light
        this.light = new THREE.PointLight(0x1ba45e, 1, 20);
        this.group.add(this.light);

        // Position it somewhere central but out of the way for most scenes
        this.group.position.set(0, 10, -15);
        this.scene.add(this.group);

        this.state = 'IDLE'; // IDLE, LISTENING, PROCESSING, EXECUTING, ERROR
        this.targetScale = 1;
        this.pulseTime = 0;
    }

    setTheme(isDark) {
        this.isDark = isDark;
        this.material.color.setHex(isDark ? 0x1ba45e : 0x159653);
    }

    setState(state) {
        this.state = state;
        switch (state) {
            case 'IDLE':
                this.material.emissive.setHex(0x0a4a29);
                this.targetScale = 1.0;
                break;
            case 'LISTENING':
                this.material.emissive.setHex(0xf0ad4e);
                this.targetScale = 1.3;
                break;
            case 'PROCESSING':
                this.material.emissive.setHex(0x1d83a8);
                this.targetScale = 1.1;
                break;
            case 'SUCCESS':
            case 'EXECUTING':
                this.material.emissive.setHex(0x1ba45e);
                this.targetScale = 1.4;
                break;
            case 'ERROR':
                this.material.emissive.setHex(0xc7353d);
                this.targetScale = 0.9;
                break;
        }
    }

    update(delta, time) {
        this.pulseTime += delta;
        
        // Base rotation
        this.mesh.rotation.y += delta * 0.5;
        this.mesh.rotation.x += delta * 0.2;
        this.innerMesh.rotation.y -= delta * 0.8;

        // Scale interpolation
        const currentScale = this.group.scale.x;
        const newScale = THREE.MathUtils.lerp(currentScale, this.targetScale, 0.1);
        this.group.scale.set(newScale, newScale, newScale);

        // Pulsing effect based on state
        if (this.state === 'LISTENING') {
            const pulse = 1 + Math.sin(this.pulseTime * 8) * 0.1;
            this.group.scale.set(newScale * pulse, newScale * pulse, newScale * pulse);
        } else if (this.state === 'PROCESSING') {
            this.mesh.rotation.y += delta * 2.0; // spin faster
        }

        // Float up and down
        this.group.position.y = 10 + Math.sin(time) * 1.5;
    }
}

export class AgroFedly3D {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.warn(`[AgroFedly3D] Canvas #${canvasId} not found.`);
            this.enabled = false;
            return;
        }

        this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        this.enabled = this.checkWebGL();
        
        if (!this.enabled) return;

        // Core Setup
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        
        // Camera targets for cinematic interpolation
        this.targetCameraPosition = new THREE.Vector3(0, 0, 5);
        this.targetCameraLookAt = new THREE.Vector3(0, 0, 0);
        this.currentLookAt = new THREE.Vector3(0, 0, 0);
        this.camera.position.copy(this.targetCameraPosition);

        try {
            this.renderer = new THREE.WebGLRenderer({
                canvas: this.canvas,
                alpha: true,
                antialias: !this.reducedMotion,
                powerPreference: "high-performance"
            });
        } catch (e) {
            console.warn("[AgroFedly3D] WebGLRenderer failed to initialize.", e);
            this.enabled = false;
            return;
        }
        
        // Adaptive Performance Engine
        this.setAdaptiveQuality();
        this.renderer.setSize(window.innerWidth, window.innerHeight);

        this.currentSceneController = null;
        this.persistentObjects = new Set(); // Objects that survive page transitions

        window.addEventListener('resize', this.onWindowResize.bind(this));

        // Theme Setup
        this.isDarkTheme = document.documentElement.classList.contains('dark-theme');
        this.setupGlobalLighting();

        // AI Core Persistent Object
        this.aiCore = new AICore(this.scene, this.isDarkTheme);
        this.persistentObjects.add(this.aiCore.group);
        this.persistentObjects.add(this.ambientLight);
        this.persistentObjects.add(this.directionalLight);

        this.observeThemeChanges();
        this.setupExperienceListeners();

        this.clock = new THREE.Clock();
        this.renderer.setAnimationLoop(this.animate.bind(this));
        
        // Voice Integration
        document.addEventListener('agrofedly:voice:state', (e) => {
            if (this.aiCore) this.aiCore.setState(e.detail.state);
        });

        // Persistent Engine initialized.
    }

    checkWebGL() {
        try {
            const canvas = document.createElement('canvas');
            return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
        } catch (e) {
            return false;
        }
    }

    setAdaptiveQuality() {
        // Initial setup
        const isMobile = window.innerWidth < 768;
        const pixelRatio = isMobile || this.reducedMotion ? 1 : Math.min(window.devicePixelRatio, 2);
        this.renderer.setPixelRatio(pixelRatio);
        this.renderer.shadowMap.enabled = !isMobile && !this.reducedMotion;
        if (this.renderer.shadowMap.enabled) {
            this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        }
        
        // Frame rate monitoring for dynamic downgrade
        this.frames = 0;
        this.lastTime = performance.now();
        this.fpsThreshold = 30; // downgrade if FPS drops below 30
        this.downgraded = false;
    }
    
    checkPerformance() {
        if (this.downgraded) return;
        this.frames++;
        const time = performance.now();
        if (time >= this.lastTime + 1000) {
            const fps = (this.frames * 1000) / (time - this.lastTime);
            if (fps < this.fpsThreshold && this.renderer.getPixelRatio() > 1) {
                console.warn(`[AgroFedly3D] FPS dropped to ${Math.round(fps)}. Downgrading 3D quality.`);
                this.renderer.setPixelRatio(1);
                this.renderer.shadowMap.enabled = false;
                this.downgraded = true;
            }
            this.lastTime = time;
            this.frames = 0;
        }
    }

    setupGlobalLighting() {
        if (this.ambientLight) this.scene.remove(this.ambientLight);
        if (this.directionalLight) this.scene.remove(this.directionalLight);

        const ambientColor = this.isDarkTheme ? 0x2a3b4c : 0xffffff;
        const ambientIntensity = this.isDarkTheme ? 0.3 : 0.7;
        this.ambientLight = new THREE.AmbientLight(ambientColor, ambientIntensity);
        this.scene.add(this.ambientLight);

        const dirColor = this.isDarkTheme ? 0x88bbff : 0xffffff;
        const dirIntensity = this.isDarkTheme ? 1.0 : 1.5;
        this.directionalLight = new THREE.DirectionalLight(dirColor, dirIntensity);
        this.directionalLight.position.set(10, 20, 10);
        if (this.renderer.shadowMap.enabled) {
            this.directionalLight.castShadow = true;
            this.directionalLight.shadow.mapSize.width = 1024;
            this.directionalLight.shadow.mapSize.height = 1024;
        }
        this.scene.add(this.directionalLight);
    }

    observeThemeChanges() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    const currentlyDark = document.documentElement.classList.contains('dark-theme');
                    if (this.isDarkTheme !== currentlyDark) {
                        this.isDarkTheme = currentlyDark;
                        this.setupGlobalLighting();
                        this.aiCore.setTheme(this.isDarkTheme);
                        if (this.currentSceneController && this.currentSceneController.onThemeChange) {
                            this.currentSceneController.onThemeChange(this.isDarkTheme);
                        }
                    }
                }
            });
        });
        observer.observe(document.documentElement, { attributes: true });
    }

    setupExperienceListeners() {
        document.addEventListener('agrofedly:page:leave', (e) => {
            // Trigger exit animations on current scene if it exists
            if (this.currentSceneController && this.currentSceneController.onPageLeave) {
                this.currentSceneController.onPageLeave(e.detail.nextUrl);
            }
            // Move camera back slightly for cinematic transition
            this.setCameraTarget(new THREE.Vector3(this.camera.position.x, this.camera.position.y + 5, this.camera.position.z + 10));
        });

        document.addEventListener('agrofedly:motion:change', (e) => {
            this.reducedMotion = e.detail.reducedMotion;
            this.setAdaptiveQuality();
        });
    }

    onWindowResize() {
        if (!this.enabled) return;
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.setAdaptiveQuality(); // Check if transitioned to mobile width
    }

    setCameraTarget(position, lookAt = new THREE.Vector3(0, 0, 0)) {
        this.targetCameraPosition.copy(position);
        this.targetCameraLookAt.copy(lookAt);
    }

    triggerCinematicPan(targetPos, targetLook, duration = 2.0) {
        if (!this.enabled) return;
        this.targetCameraPosition.copy(targetPos);
        this.targetCameraLookAt.copy(targetLook);
        
        // Disptach event to trigger UI fade or sync
        document.dispatchEvent(new CustomEvent('agrofedly:3d:cinematic_pan', { detail: { duration } }));
    }

    loadScene(SceneControllerClass) {
        if (!this.enabled) return;

        if (this.currentSceneController && this.currentSceneController.dispose) {
            this.currentSceneController.dispose();
        }
        
        // Remove non-persistent objects
        const objectsToRemove = [];
        this.scene.children.forEach(child => {
            if (!this.persistentObjects.has(child)) {
                objectsToRemove.push(child);
            }
        });

        objectsToRemove.forEach(obj => {
            this.scene.remove(obj);
            if(obj.geometry) obj.geometry.dispose();
            if(obj.material) {
                if(Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
                else obj.material.dispose();
            }
        });

        // Initialize new scene
        this.currentSceneController = new SceneControllerClass(this);
        this.currentSceneController.init();
    }

    animate() {
        if (!this.enabled) return;
        
        this.checkPerformance();
        
        const delta = this.clock.getDelta();
        const time = this.clock.getElapsedTime();

        // Update AI Core
        this.aiCore.update(delta, time);

        // Update active scene
        if (this.currentSceneController && this.currentSceneController.update) {
            this.currentSceneController.update(delta, time);
        }

        // Cinematic Camera Interpolation
        if (!this.reducedMotion) {
            this.camera.position.lerp(this.targetCameraPosition, 0.05);
            this.currentLookAt.lerp(this.targetCameraLookAt, 0.05);
            this.camera.lookAt(this.currentLookAt);
        } else {
            this.camera.position.copy(this.targetCameraPosition);
            this.currentLookAt.copy(this.targetCameraLookAt);
            this.camera.lookAt(this.currentLookAt);
        }

        this.renderer.render(this.scene, this.camera);
    }
}

// Scene Controllers
export class LandingSceneController {
    constructor(engine) {
        this.engine = engine;
        this.group = new THREE.Group();
        this.particles = null;
    }
    
    init() {
        this.engine.scene.add(this.group);
        
        // Setup a beautiful floating particle field for the landing page
        const particleGeo = new THREE.BufferGeometry();
        const particleCount = 2000;
        
        const posArray = new Float32Array(particleCount * 3);
        for(let i = 0; i < particleCount * 3; i++) {
            posArray[i] = (Math.random() - 0.5) * 60;
        }
        
        particleGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
        const particleMat = new THREE.PointsMaterial({
            size: 0.1,
            color: this.engine.isDarkTheme ? 0x1ba45e : 0x0a4a29,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending
        });
        
        this.particles = new THREE.Points(particleGeo, particleMat);
        this.group.add(this.particles);
        
        // Move camera to a nice vantage point
        this.engine.setCameraTarget(new THREE.Vector3(0, 0, 20), new THREE.Vector3(0, 0, 0));
        
        // Move the AI core to the center
        this.engine.aiCore.group.position.set(0, 0, 0);
    }
    
    update(delta, time) {
        if(this.particles) {
            this.particles.rotation.y += delta * 0.05;
            this.particles.rotation.x += delta * 0.02;
        }
    }
    
    onThemeChange(isDark) {
        if(this.particles) {
            this.particles.material.color.setHex(isDark ? 0x1ba45e : 0x0a4a29);
        }
    }
    
    dispose() {
        // Cleanup happens in engine.loadScene automatically, but we can do specific cleanup here
    }
}

export class LoginSceneController {
    constructor(engine) {
        this.engine = engine;
        this.group = new THREE.Group();
    }
    
    init() {
        this.engine.scene.add(this.group);
        
        // Create an abstract geometric representation of "security" or "gates"
        const geo = new THREE.TorusGeometry(8, 0.2, 16, 100);
        const mat = new THREE.MeshPhysicalMaterial({
            color: this.engine.isDarkTheme ? 0x1ba45e : 0x159653,
            wireframe: true,
            transparent: true,
            opacity: 0.3
        });
        
        this.ring1 = new THREE.Mesh(geo, mat);
        this.ring1.rotation.x = Math.PI / 2;
        this.group.add(this.ring1);
        
        this.ring2 = new THREE.Mesh(geo, mat);
        this.ring2.rotation.y = Math.PI / 2;
        this.group.add(this.ring2);
        
        // Move camera closer, off-center
        this.engine.setCameraTarget(new THREE.Vector3(10, 5, 15), new THREE.Vector3(0, 0, 0));
        
        // Move AI core inside the rings
        this.engine.aiCore.group.position.set(0, 0, 0);
    }
    
    update(delta, time) {
        if(this.ring1) this.ring1.rotation.z += delta * 0.2;
        if(this.ring2) this.ring2.rotation.x += delta * 0.3;
    }
    
    onThemeChange(isDark) {
        const color = isDark ? 0x1ba45e : 0x159653;
        if(this.ring1) this.ring1.material.color.setHex(color);
        if(this.ring2) this.ring2.material.color.setHex(color);
    }
}

window.LandingSceneController = LandingSceneController;
window.LoginSceneController = LoginSceneController;

// Workspace Scene Controllers
export class WorkspaceSceneController {
    constructor(engine, config={}) {
        this.engine = engine;
        this.group = new THREE.Group();
        this.accent = config.accent || 0x1ba45e;
    }
    init() {
        this.engine.scene.add(this.group);
    }
    update(delta, time) {}
    onThemeChange(isDark) {}
    dispose() {}
}

export class AgricultureScene extends WorkspaceSceneController {
    init() {
        super.init();
        const gridHelper = new THREE.GridHelper(40, 40, this.accent, 0x444444);
        gridHelper.material.opacity = 0.2;
        gridHelper.material.transparent = true;
        this.group.add(gridHelper);
        
        const geo = new THREE.BoxGeometry(0.5, 0.5, 0.5);
        const mat = new THREE.MeshPhysicalMaterial({ color: this.accent, wireframe: true });
        this.nodes = [];
        for(let i=0; i<10; i++) {
            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.set((Math.random()-0.5)*20, Math.random()*5, (Math.random()-0.5)*20);
            this.group.add(mesh);
            this.nodes.push(mesh);
        }
        this.engine.setCameraTarget(new THREE.Vector3(0, 5, 10), new THREE.Vector3(0, 0, 0));
    }
    update(delta, time) {
        this.group.rotation.y += delta * 0.05;
        this.nodes.forEach((node, i) => {
            node.position.y += Math.sin(time * 2 + i) * 0.01;
            node.rotation.x += delta * 0.5;
        });
    }
}

export class KitchenScene extends WorkspaceSceneController {
    init() {
        super.init();
        this.accent = 0xf59e0b;
        const geo = new THREE.CylinderGeometry(1, 1, 0.2, 32);
        const mat = new THREE.MeshPhysicalMaterial({ color: this.accent, transparent: true, opacity: 0.6 });
        this.stations = [];
        for(let i=0; i<4; i++) {
            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(Math.cos(i * Math.PI/2) * 5, -2, Math.sin(i * Math.PI/2) * 5);
            this.group.add(mesh);
            this.stations.push(mesh);
        }
        this.engine.setCameraTarget(new THREE.Vector3(0, 5, 10), new THREE.Vector3(0, 0, 0));
    }
    update(delta, time) {
        this.group.rotation.y += delta * 0.1;
    }
}

export class RedistributionScene extends WorkspaceSceneController {
    init() {
        super.init();
        this.accent = 0x8b5cf6;
        const mat = new THREE.LineBasicMaterial({ color: this.accent, transparent: true, opacity: 0.5 });
        this.lines = new THREE.Group();
        for(let i=0; i<20; i++) {
            const points = [];
            points.push(new THREE.Vector3(0, 0, 0));
            points.push(new THREE.Vector3((Math.random()-0.5)*20, (Math.random()-0.5)*10, (Math.random()-0.5)*20));
            const geo = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geo, mat);
            this.lines.add(line);
        }
        this.group.add(this.lines);
        this.engine.setCameraTarget(new THREE.Vector3(0, 5, 10), new THREE.Vector3(0, 0, 0));
    }
    update(delta, time) {
        this.lines.rotation.y += delta * 0.1;
    }
}

export class LogisticsScene extends WorkspaceSceneController {
    init() {
        super.init();
        this.accent = 0x3b82f6;
        const geo = new THREE.SphereGeometry(0.2, 8, 8);
        const mat = new THREE.MeshBasicMaterial({ color: this.accent });
        this.vehicles = [];
        for(let i=0; i<5; i++) {
            const mesh = new THREE.Mesh(geo, mat);
            this.group.add(mesh);
            this.vehicles.push({ mesh, angle: i });
        }
        this.engine.setCameraTarget(new THREE.Vector3(0, 5, 10), new THREE.Vector3(0, 0, 0));
    }
    update(delta, time) {
        this.vehicles.forEach(v => {
            v.angle += delta * 0.5;
            v.mesh.position.set(Math.cos(v.angle)*10, 0, Math.sin(v.angle)*10);
        });
    }
}

export class AdminScene extends WorkspaceSceneController {
    init() {
        super.init();
        this.accent = 0xef4444;
        const geo = new THREE.IcosahedronGeometry(2, 1);
        const mat = new THREE.MeshPhysicalMaterial({ color: this.accent, wireframe: true });
        this.core = new THREE.Mesh(geo, mat);
        this.group.add(this.core);
        this.engine.setCameraTarget(new THREE.Vector3(0, 0, 10), new THREE.Vector3(0, 0, 0));
    }
    update(delta, time) {
        this.core.rotation.x += delta * 0.2;
        this.core.rotation.y += delta * 0.3;
    }
}

window.AgricultureScene = AgricultureScene;
window.KitchenScene = KitchenScene;
window.RedistributionScene = RedistributionScene;
window.LogisticsScene = LogisticsScene;
window.AdminScene = AdminScene;
