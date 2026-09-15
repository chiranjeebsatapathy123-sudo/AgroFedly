import * as THREE from 'three';

export class LoginScene {
    constructor(engine) {
        this.engine = engine;
        this.group = new THREE.Group();
        this.particles = [];
        this.themeColor = engine.isDarkTheme ? 0x1ba45e : 0x159653;
        this.glowColor = engine.isDarkTheme ? 0x88ff88 : 0x44cc44;
    }

    init() {
        this.engine.scene.add(this.group);
        this.engine.scene.fog = new THREE.FogExp2(this.engine.isDarkTheme ? 0x0a1410 : 0xf4f8f5, 0.04);
        
        // Initial cinematic camera position (starts low, swoops to final)
        this.engine.camera.position.set(0, -20, 40);
        this.engine.setCameraTarget(new THREE.Vector3(0, 0, 15), new THREE.Vector3(0, 0, 0));
        
        // AI Core uses the global one
        if (this.engine.aiCore) {
            this.engine.aiCore.group.position.set(-6, 0, -5); // Positioned to the left to balance the login form on the right
        }

        // Core rings (we add rings around the global core in login)
        const ringGeo = new THREE.TorusGeometry(3, 0.05, 16, 100);
        const ringMat = new THREE.MeshBasicMaterial({ color: this.glowColor, transparent: true, opacity: 0.5 });
        
        this.ring1 = new THREE.Mesh(ringGeo, ringMat);
        if (this.engine.aiCore) this.ring1.position.copy(this.engine.aiCore.group.position);
        this.group.add(this.ring1);
        
        this.ring2 = new THREE.Mesh(ringGeo, ringMat);
        if (this.engine.aiCore) this.ring2.position.copy(this.engine.aiCore.group.position);
        this.group.add(this.ring2);

        // Ambient particles
        if (!this.engine.reducedMotion) {
            const particleGeo = new THREE.BufferGeometry();
            const particleCount = 200;
            const positions = new Float32Array(particleCount * 3);
            
            for (let i = 0; i < particleCount * 3; i+=3) {
                positions[i] = (Math.random() - 0.5) * 40;
                positions[i+1] = (Math.random() - 0.5) * 40;
                positions[i+2] = (Math.random() - 0.5) * 20 - 10;
            }
            
            particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            
            const particleMat = new THREE.PointsMaterial({
                color: this.glowColor,
                size: 0.1,
                transparent: true,
                opacity: 0.6
            });
            
            this.particleSystem = new THREE.Points(particleGeo, particleMat);
            this.group.add(this.particleSystem);
        }

        // Cinematic Entry Animation
        this.animTime = 0;
        this.isEntering = true;
    }

    update(delta, time) {
        // Rotate rings in opposite directions
        if (this.ring1 && this.ring2) {
            this.ring1.rotation.x = Math.PI / 2 + Math.sin(time * 0.5) * 0.5;
            this.ring1.rotation.y = time * 0.3;
            
            this.ring2.rotation.x = Math.PI / 4 + Math.cos(time * 0.4) * 0.5;
            this.ring2.rotation.y = -time * 0.2;
        }

        // Slowly drift particles
        if (this.particleSystem) {
            this.particleSystem.rotation.y = time * 0.02;
            this.particleSystem.rotation.x = time * 0.01;
        }
    }

    onThemeChange(isDark) {
        this.engine.scene.fog.color.setHex(isDark ? 0x0a1410 : 0xf4f8f5);
        this.themeColor = isDark ? 0x1ba45e : 0x159653;
        this.glowColor = isDark ? 0x88ff88 : 0x44cc44;
        
        if (this.ring1) this.ring1.material.color.setHex(this.glowColor);
        if (this.ring2) this.ring2.material.color.setHex(this.glowColor);
        if (this.particleSystem) this.particleSystem.material.color.setHex(this.glowColor);
    }

    dispose() {
        // Cleanup if necessary
    }
}
