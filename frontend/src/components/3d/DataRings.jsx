import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function Ring({ radius, speed, color, thickness = 0.02 }) {
    const ref = useRef()

    useFrame((state) => {
        const t = state.clock.getElapsedTime()
        ref.current.rotation.x = Math.PI / 2 + Math.sin(t * 0.5) * 0.1
        ref.current.rotation.z = t * speed
    })

    return (
        <mesh ref={ref}>
            <torusGeometry args={[radius, thickness, 16, 100]} />
            <meshBasicMaterial
                color={color}
                transparent
                opacity={0.8}
            />
        </mesh>
    )
}

export function DataRings() {
    return (
        <group>
            <Ring radius={2.5} speed={0.3} color="#00f3ff" thickness={0.015} />
            <Ring radius={3.2} speed={-0.2} color="#ff00ff" thickness={0.01} />
            <Ring radius={4.0} speed={0.15} color="#00ff88" thickness={0.008} />
        </group>
    )
}

export default DataRings
