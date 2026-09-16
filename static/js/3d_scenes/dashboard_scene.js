import * as THREE from 'three';

export class DashboardScene {
    constructor(engine) {
        this.engine = engine;
        this.group = new THREE.Group();
        this.themeColor = engine.isDarkTheme ? 0x1ba45e : 0x159653;
        this.nodes = [];
        this.particles = [];
        this.paths = [];
    }

    init() {
        this.engine.scene.add(this.group);
        this.engine.scene.fog = new THREE.FogExp2(this.engine.isDarkTheme ? 0x0a1410 : 0xf4f8f5, 0.02);
        
        // Setup Camera
        this.engine.camera.position.set(0, 15, 40);
        this.engine.setCameraTarget(new THREE.Vector3(0, 20, 40), new THREE.Vector3(0, 0, 0));

        // Create Grid
        const gridColor = this.engine.isDarkTheme ? 0x1f382c : 0xdce6e0;
        this.grid = new THREE.GridHelper(80, 40, gridColor, gridColor);
        this.grid.position.y = -2;
        this.group.add(this.grid);

        // Define nodes in the supply chain
        const chain = [
            { id: 'farm', label: 'Farm', pos: new THREE.Vector3(-20, 0, -10), color: 0x228B22 },
            { id: 'produce', label: 'Produce', pos: new THREE.Vector3(-10, 0, 0), color: 0x32CD32 },
            { id: 'processing', label: 'Processing', pos: new THREE.Vector3(0, 0, 5), color: 0x808080 },
            { id: 'storage', label: 'Storage', pos: new THREE.Vector3(10, 0, 0), color: 0x4682B4 },
            { id: 'delivery', label: 'Delivery', pos: new THREE.Vector3(20, 0, -10), color: 0xFFA500 }
        ];

        // Create nodes
        chain.forEach((nodeInfo, index) => {
            // Base platform
            const platformGeo = new THREE.CylinderGeometry(3, 3, 0.5, 32);
            const platformMat = new THREE.MeshStandardMaterial({ color: nodeInfo.color, roughness: 0.8 });
            const platform = new THREE.Mesh(platformGeo, platformMat);
            platform.position.copy(nodeInfo.pos);
            
            // Add a simple geometric representation above the platform
            let iconMesh;
            if (nodeInfo.id === 'farm') {
                iconMesh = new THREE.Mesh(new THREE.ConeGeometry(1.5, 3, 4), new THREE.MeshStandardMaterial({color: 0x00FF00}));
            } else if (nodeInfo.id === 'produce') {
                iconMesh = new THREE.Mesh(new THREE.SphereGeometry(1.2, 16, 16), new THREE.MeshStandardMaterial({color: 0xFF6347}));
            } else if (nodeInfo.id === 'processing') {
                iconMesh = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), new THREE.MeshStandardMaterial({color: 0xA9A9A9}));
            } else if (nodeInfo.id === 'storage') {
                iconMesh = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, 3, 16), new THREE.MeshStandardMaterial({color: 0xADD8E6}));
            } else {
                iconMesh = new THREE.Mesh(new THREE.BoxGeometry(3, 1.5, 1.5), new THREE.MeshStandardMaterial({color: 0xFFD700}));
            }
            
            iconMesh.position.set(0, 2, 0);
            platform.add(iconMesh);
            
            // Add slight hover animation data
            platform.userData = { 
                baseY: nodeInfo.pos.y,
                hoverPhase: Math.random() * Math.PI * 2
            };

            this.group.add(platform);
            this.nodes.push(platform);

            // Create Path to next node
            if (index < chain.length - 1) {
                const nextNode = chain[index + 1];
                const points = [
                    new THREE.Vector3(nodeInfo.pos.x, 0.5, nodeInfo.pos.z),
                    new THREE.Vector3(nextNode.pos.x, 0.5, nextNode.pos.z)
                ];
                const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
                const lineMat = new THREE.LineBasicMaterial({ 
                    color: this.engine.isDarkTheme ? 0x334433 : 0xcccccc,
                    transparent: true,
                    opacity: 0.5
                });
                const line = new THREE.Line(lineGeo, lineMat);
                this.group.add(line);
                
                // Save path for particles
                this.paths.push({
                    start: points[0],
                    end: points[1],
                    length: points[0].distanceTo(points[1])
                });
            }
        });

        // Create Particles flowing along paths
        if (!this.engine.reducedMotion) {
            const particleGeo = new THREE.SphereGeometry(0.2, 8, 8);
            const particleMat = new THREE.MeshBasicMaterial({ color: 0x1ba45e });
            
            for (let i = 0; i < 15; i++) {
                const p = new THREE.Mesh(particleGeo, particleMat);
                // Assign to a random path
                p.userData.pathIndex = Math.floor(Math.random() * this.paths.length);
                p.userData.progress = Math.random(); // 0 to 1
                p.userData.speed = (0.2 + Math.random() * 0.3); // units per second
                this.group.add(p);
                this.particles.push(p);
            }
        }

        this.scrollY = 0;
        this.scrollHandler = () => {
            this.scrollY = window.scrollY;
        };
        document.addEventListener('scroll', this.scrollHandler);
    }

    update(delta, time) {
        // Gently bob the nodes
        this.nodes.forEach(node => {
            node.position.y = node.userData.baseY + Math.sin(time + node.userData.hoverPhase) * 0.5;
        });

        // Move particles along paths
        this.particles.forEach(p => {
            const path = this.paths[p.userData.pathIndex];
            p.userData.progress += (p.userData.speed * delta) / path.length;
            
            if (p.userData.progress >= 1) {
                p.userData.progress = 0;
                // Move to next path
                p.userData.pathIndex = (p.userData.pathIndex + 1) % this.paths.length;
            }
            
            const currentPath = this.paths[p.userData.pathIndex];
            p.position.lerpVectors(currentPath.start, currentPath.end, p.userData.progress);
        });

        // Gentle camera/scene rotation
        this.group.rotation.y = Math.sin(time * 0.05) * 0.1;
        
        // Scroll parallax
        const targetY = this.scrollY * -0.015;
        this.group.position.y += (targetY - this.group.position.y) * 0.1;
    }

    onThemeChange(isDark) {
        this.engine.scene.fog.color.setHex(isDark ? 0x0a1410 : 0xf4f8f5);
        this.themeColor = isDark ? 0x1ba45e : 0x159653;
        
        const gridColor = isDark ? 0x1f382c : 0xdce6e0;
        this.group.remove(this.grid);
        this.grid = new THREE.GridHelper(80, 40, gridColor, gridColor);
        this.grid.position.y = -2;
        this.group.add(this.grid);
    }

    dispose() {
        document.removeEventListener('scroll', this.scrollHandler);
    }
}
