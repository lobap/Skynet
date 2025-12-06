import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import { EffectComposer, Bloom, ChromaticAberration } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import { Suspense } from 'react'

import SkynetCore from './SkynetCore'
import DataRings from './DataRings'
import DataDust from './DataDust'

function Scene() {
    return (
        <>
            {/* Camera */}
            <PerspectiveCamera makeDefault position={[0, 0, 10]} fov={60} />
            <OrbitControls
                enableZoom={false}
                enablePan={false}
                autoRotate
                autoRotateSpeed={0.3}
                maxPolarAngle={Math.PI / 1.5}
                minPolarAngle={Math.PI / 3}
            />

            {/* Lighting */}
            <ambientLight intensity={0.1} />
            <pointLight position={[10, 10, 10]} intensity={0.5} color="#00f3ff" />
            <pointLight position={[-10, -10, -10]} intensity={0.3} color="#ff00ff" />

            {/* Fog for depth */}
            <fog attach="fog" args={['#050505', 5, 30]} />

            {/* Scene objects */}
            <SkynetCore />
            <DataRings />
            <DataDust />

            {/* Post-processing */}
            <EffectComposer>
                <Bloom
                    intensity={1.5}
                    luminanceThreshold={0.2}
                    luminanceSmoothing={0.9}
                    blendFunction={BlendFunction.ADD}
                />
                <ChromaticAberration
                    offset={[0.002, 0.002]}
                    blendFunction={BlendFunction.NORMAL}
                />
            </EffectComposer>
        </>
    )
}

export function Experience() {
    return (
        <Canvas
            gl={{
                antialias: true,
                alpha: true,
                powerPreference: 'high-performance'
            }}
            style={{ background: '#050505' }}
        >
            <Suspense fallback={null}>
                <Scene />
            </Suspense>
        </Canvas>
    )
}

export default Experience
