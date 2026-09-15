import * as THREE from 'three';

export class DashboardScene {
    constructor(engine) {
        this.engine = engine;
        this.group = new THREE.Group();
        this.themeColor = engine.isDarkTheme ? 0x1ba45e : 0x159653;
        this.dataNodes = [];
    }

    init() {
        this.engine.scene.add(this.group);
        this.engine.scene.fog = new THREE.FogExp2(this.engine.isDarkTheme ? 0x0a1410 : 0xf4f8f5, 0.03);
        
        // Use central engine for camera (start from a wider angle and swoop in)
        this.engine.camera.position.set(0, 5, 30);
        this.engine.setCameraTarget(new THREE.Vector3(0, 15, 20), new THREE.Vector3(0, 0, 0));

        // Move the global AI core to a specific spot for the dashboard
        if (this.engine.aiCore) {
            this.engine.aiCore.group.position.set(10, 2, -5);
        }

        // Grid helper to anchor the data environment
        const gridColor = this.engine.isDarkTheme ? 0x1f382c : 0xdce6e0;
        this.grid = new THREE.GridHelper(50, 25, gridColor, gridColor);
        this.grid.position.y = -5;
        this.group.add(this.grid);

        // Abstract Data Pillars representing statistics
        const pillarGeo = new THREE.BoxGeometry(1, 1, 1);
        const pillarMat = new THREE.MeshStandardMaterial({
            color: this.themeColor,
            transparent: true,
            opacity: 0.8
        });

        // Create a few pillars
        if (!this.engine.reducedMotion) {
            for (let i = 0; i < 8; i++) {
                const mesh = new THREE.Mesh(pillarGeo, pillarMat);
                
                const height = Math.random() * 8 + 2;
                mesh.scale.y = height;
                
                mesh.position.set(
                    (Math.random() - 0.5) * 30,
                    (height / 2) - 5, // Rest on the grid
                    (Math.random() - 0.5) * 20 - 10
                );
                
                mesh.userData = {
                    targetHeight: height,
                    currentHeight: 0.1,
                    speed: Math.random() * 2 + 1
                };
                
                // Start flat
                mesh.scale.y = 0.1;
                
                this.group.add(mesh);
                this.dataNodes.push(mesh);
            }
        }

        this.targetY = 0;
        this.scrollY = 0;
        
        this.scrollHandler = () => {
            this.scrollY = window.scrollY;
        };
        document.addEventListener('scroll', this.scrollHandler);
    }

    update(delta, time) {
        // Animate pillars growing
        this.dataNodes.forEach(node => {
            if (node.scale.y < node.userData.targetHeight) {
                node.scale.y += delta * node.userData.speed * 5;
                node.position.y = (node.scale.y / 2) - 5;
            }
        });

        // Gentle camera rotation
        this.group.rotation.y = Math.sin(time * 0.05) * 0.2;
        
        // Scroll parallax
        this.targetY = this.scrollY * -0.01;
        this.group.position.y += (this.targetY - this.group.position.y) * 0.1;
    }

    onThemeChange(isDark) {
        this.engine.scene.fog.color.setHex(isDark ? 0x0a1410 : 0xf4f8f5);
        this.themeColor = isDark ? 0x1ba45e : 0x159653;
        
        const gridColor = isDark ? 0x1f382c : 0xdce6e0;
        
        // Unfortunately, GridHelper colors cannot be easily updated after creation.
        // Recreate it for simplicity.
        this.group.remove(this.grid);
        this.grid = new THREE.GridHelper(50, 25, gridColor, gridColor);
        this.grid.position.y = -5;
        this.group.add(this.grid);

        this.dataNodes.forEach(node => {
            node.material.color.setHex(this.themeColor);
        });
    }

    dispose() {
        document.removeEventListener('scroll', this.scrollHandler);
    }
}
