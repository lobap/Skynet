import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { MeshDistortMaterial, Icosahedron, Wireframe } from '@react-three/drei'
import * as THREE from 'three'

export function SkynetCore() {
    const meshRef = useRef()
    const wireRef = useRef()

    useFrame((state) => {
        const t = state.clock.getElapsedTime()

        // Subtle rotation
        if (meshRef.current) {
            meshRef.current.rotation.x = Math.sin(t * 0.1) * 0.1
            meshRef.current.rotation.y = t * 0.05
        }

        // Pulse emissive intensity
        if (wireRef.current) {
            const pulse = 0.5 + Math.sin(t * 2) * 0.3
            wireRef.current.material.emissiveIntensity = pulse
        }
    })

    return (
        <group ref={meshRef}>
            {/* Inner distorting sphere */}
            <Icosahedron args={[1.8, 4]} ref={wireRef}>
                <MeshDistortMaterial
                    color="#00f3ff"
                    emissive="#00f3ff"
                    emissiveIntensity={0.5}
                    wireframe
                    distort={0.2}
                    speed={2}
                    roughness={0}
                />
            </Icosahedron>

            {/* Solid core glow */}
            <mesh>
                <icosahedronGeometry args={[1.2, 2]} />
                <meshBasicMaterial
                    color="#001a1f"
                    transparent
                    opacity={0.8}
                />
            </mesh>
        </group>
    )
}

export default SkynetCore
