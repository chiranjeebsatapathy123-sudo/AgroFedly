import * as THREE from 'three';

export class HeroScene {
    constructor(engine) {
        this.engine = engine;
        this.particles = [];
        this.cubes = [];
        this.group = new THREE.Group();
        
        // Base color theme depending on dark/light
        this.themeColor = engine.isDarkTheme ? 0x1ba45e : 0x159653;
        this.secondaryColor = engine.isDarkTheme ? 0x0f1d17 : 0xe5f5ea;
    }

    init() {
        this.engine.scene.add(this.group);
        this.engine.scene.fog = new THREE.FogExp2(this.engine.isDarkTheme ? 0x0a1410 : 0xf4f8f5, 0.05);
        this.engine.camera.position.set(0, 5, 15);
        this.engine.camera.lookAt(0, 0, 0);

        // Add abstract "Farm Fields" (floating planes with wireframes)
        const planeGeo = new THREE.PlaneGeometry(30, 30, 20, 20);
        // Slightly displace vertices for terrain feel
        const posAttribute = planeGeo.attributes.position;
        for(let i=0; i<posAttribute.count; i++) {
            const z = Math.random() * 0.5;
            posAttribute.setZ(i, z);
        }
        planeGeo.computeVertexNormals();

        const planeMat = new THREE.MeshStandardMaterial({
            color: this.themeColor,
            wireframe: true,
            transparent: true,
            opacity: 0.15
        });
        
        this.terrain = new THREE.Mesh(planeGeo, planeMat);
        this.terrain.rotation.x = -Math.PI / 2;
        this.terrain.position.y = -3;
        this.group.add(this.terrain);

        // Data nodes (Data particles)
        const sphereGeo = new THREE.IcosahedronGeometry(0.1, 1);
        const sphereMat = new THREE.MeshStandardMaterial({
            color: 0x88ff88,
            emissive: 0x22aa22,
            emissiveIntensity: 0.5
        });

        const numParticles = this.engine.reducedMotion ? 20 : 80;
        
        for (let i = 0; i < numParticles; i++) {
            const mesh = new THREE.Mesh(sphereGeo, sphereMat);
            mesh.position.set(
                (Math.random() - 0.5) * 20,
                (Math.random() - 0.5) * 10,
                (Math.random() - 0.5) * 20
            );
            mesh.userData = {
                speed: Math.random() * 0.02 + 0.005,
                angle: Math.random() * Math.PI * 2,
                radius: Math.random() * 10 + 2,
                yOffset: mesh.position.y
            };
            this.group.add(mesh);
            this.particles.push(mesh);
        }

        // Connecting lines material
        this.lineMat = new THREE.LineBasicMaterial({
            color: this.themeColor,
            transparent: true,
            opacity: 0.15
        });
        
        this.lineGeo = new THREE.BufferGeometry();
        this.lineMesh = new THREE.LineSegments(this.lineGeo, this.lineMat);
        this.group.add(this.lineMesh);

        // Parallax effect on mouse move
        this.mouseX = 0;
        this.mouseY = 0;
        this.targetX = 0;
        this.targetY = 0;
        
        this.mouseMoveHandler = (event) => {
            this.mouseX = (event.clientX - window.innerWidth / 2);
            this.mouseY = (event.clientY - window.innerHeight / 2);
        };
        
        document.addEventListener('mousemove', this.mouseMoveHandler);
    }

    update(delta, time) {
        if (!this.engine.reducedMotion) {
            // Update particles
            const positions = [];
            
            this.particles.forEach((p, i) => {
                p.userData.angle += p.userData.speed;
                p.position.x = Math.cos(p.userData.angle) * p.userData.radius;
                p.position.z = Math.sin(p.userData.angle) * p.userData.radius;
                p.position.y = p.userData.yOffset + Math.sin(time * 2 + i) * 0.5;
                
                positions.push(p.position);
            });

            // Update connecting lines
            const linePositions = [];
            for (let i = 0; i < positions.length; i++) {
                for (let j = i + 1; j < positions.length; j++) {
                    const dist = positions[i].distanceTo(positions[j]);
                    if (dist < 3.5) {
                        linePositions.push(
                            positions[i].x, positions[i].y, positions[i].z,
                            positions[j].x, positions[j].y, positions[j].z
                        );
                    }
                }
            }
            this.lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
        }

        // Smooth camera parallax
        this.targetX = this.mouseX * 0.005;
        this.targetY = this.mouseY * 0.005;
        
        this.engine.camera.position.x += (this.targetX - this.engine.camera.position.x) * 0.05;
        this.engine.camera.position.y += (-this.targetY + 5 - this.engine.camera.position.y) * 0.05;
        this.engine.camera.lookAt(0, 0, 0);
        
        // Gentle scene rotation
        this.group.rotation.y = time * 0.05;
    }

    onThemeChange(isDark) {
        this.engine.scene.fog.color.setHex(isDark ? 0x0a1410 : 0xf4f8f5);
        this.themeColor = isDark ? 0x1ba45e : 0x159653;
        this.terrain.material.color.setHex(this.themeColor);
        this.lineMat.color.setHex(this.themeColor);
    }

    dispose() {
        document.removeEventListener('mousemove', this.mouseMoveHandler);
    }
}
