import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import { Suspense, type FC } from 'react'

import PositronicBrain from './SkynetCore'

const Scene: FC = () => (
    <>
        <PerspectiveCamera makeDefault position={[0, 0, 7]} fov={55} />
        <OrbitControls
            enableZoom={false}
            enablePan={false}
            autoRotate={false}
            maxPolarAngle={Math.PI / 1.5}
            minPolarAngle={Math.PI / 3}
        />

        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} color={0xffffff} />
        <directionalLight position={[-5, -5, -5]} intensity={0.4} color={0x88ccff} />
        <pointLight position={[0, 3, 3]} intensity={0.6} color={0x60a5fa} />

        <PositronicBrain />

        <EffectComposer>
            <Bloom
                intensity={0.6}
                luminanceThreshold={0.2}
                luminanceSmoothing={0.9}
                blendFunction={BlendFunction.ADD}
            />
        </EffectComposer>
    </>
)

export const Experience: FC = () => (
    <Canvas
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        style={{ background: 'transparent' }}
    >
        <Suspense fallback={null}>
            <Scene />
        </Suspense>
    </Canvas>
)

export default Experience
