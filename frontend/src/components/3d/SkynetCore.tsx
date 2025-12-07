import { useRef, useMemo, useState, useCallback, useEffect, type RefObject } from 'react'
import { useFrame, useThree, type RootState } from '@react-three/fiber'
import * as THREE from 'three'
import { Html } from '@react-three/drei'

// Types
interface Synapse {
    id: number
    start: THREE.Vector3
    end: THREE.Vector3
    color: THREE.Color
}

interface Thought {
    id: number
    text: string
    position: THREE.Vector3
}

interface ParticleData {
    positions: Float32Array
    homePositions: Float32Array
    wallPositions: Float32Array
    colors: Float32Array
    sizes: Float32Array
    phases: Float32Array
    velocities: Float32Array
    activeState: Float32Array
}

interface SynapticFlashProps {
    start: THREE.Vector3
    end: THREE.Vector3
    color: THREE.Color
}

interface ThoughtNodeProps {
    text: string
    position: THREE.Vector3
    onComplete?: () => void
}

// Constants
const PARTICLE_COUNT = 2500
const CUBE_SIZE = 2.2

// Synaptic flash component
function SynapticFlash({ start, end, color }: SynapticFlashProps) {
    const [opacity, setOpacity] = useState(1)

    useFrame((_: RootState, delta: number) => {
        setOpacity((prev: number) => Math.max(0, prev - delta * 3))
    })

    if (opacity <= 0) return null

    const points = [start, end]
    const midpoint: [number, number, number] = [
        (start.x + end.x) / 2,
        (start.y + end.y) / 2,
        (start.z + end.z) / 2
    ]

    return (
        <group>
            <primitive object={new THREE.Line(
                new THREE.BufferGeometry().setFromPoints(points),
                new THREE.LineBasicMaterial({ color, transparent: true, opacity: opacity * 0.9 })
            )} />
            <mesh position={midpoint}>
                <sphereGeometry args={[0.03 * opacity, 6, 6]} />
                <meshBasicMaterial color={color} transparent opacity={opacity} />
            </mesh>
        </group>
    )
}

// Thought popup bubble
function ThoughtNode({ text, position, onComplete }: ThoughtNodeProps) {
    const [life, setLife] = useState(0)
    const [opacity, setOpacity] = useState(0)
    const [currentPos, setCurrentPos] = useState(position.clone())

    const targetPos = useMemo(() => {
        const theta = Math.random() * Math.PI * 2
        const phi = Math.acos(2 * Math.random() - 1) * 0.5
        return new THREE.Vector3(
            2.0 * Math.sin(phi) * Math.cos(theta),
            2.0 * Math.sin(phi) * Math.sin(theta),
            2.0 * Math.cos(phi)
        )
    }, [])

    useFrame((_: RootState, delta: number) => {
        setLife((prev: number) => {
            const newLife = prev + delta
            if (newLife < 0.5) setOpacity(newLife * 2)
            else if (newLife > 5) setOpacity(Math.max(0, (6 - newLife)))
            else setOpacity(1)
            if (newLife >= 6) { onComplete?.(); return prev }
            return newLife
        })
        setCurrentPos((prev: THREE.Vector3) => prev.clone().lerp(targetPos, 0.03))
    })

    if (life >= 6 || opacity <= 0) return null
    const displayText = text.length > 50 ? text.substring(0, 47) + '...' : text

    return (
        <Html
            position={[currentPos.x, currentPos.y, currentPos.z]}
            center
            style={{ opacity, transition: 'opacity 0.2s', pointerEvents: 'none' }}
        >
            <div style={{
                background: 'rgba(40, 40, 50, 0.85)',
                border: '1px solid rgba(100, 100, 110, 0.5)',
                borderRadius: '6px',
                padding: '8px 12px',
                color: 'white',
                fontSize: '11px',
                fontFamily: 'system-ui, sans-serif',
                maxWidth: '200px',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
            }}>
                {displayText}
            </div>
        </Html>
    )
}

// Create particle data
function createParticleData(): ParticleData {
    const positions = new Float32Array(PARTICLE_COUNT * 3)
    const homePositions = new Float32Array(PARTICLE_COUNT * 3)
    const wallPositions = new Float32Array(PARTICLE_COUNT * 3)
    const colors = new Float32Array(PARTICLE_COUNT * 3)
    const sizes = new Float32Array(PARTICLE_COUNT)
    const phases = new Float32Array(PARTICLE_COUNT)
    const velocities = new Float32Array(PARTICLE_COUNT * 3)
    const activeState = new Float32Array(PARTICLE_COUNT)

    const limit = (CUBE_SIZE / 2) - 0.15

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        const angle = (i / PARTICLE_COUNT) * Math.PI * 2 * 8 + Math.random() * 0.5
        const radius = 0.3 + Math.random() * 0.7
        const height = (Math.random() - 0.5) * 2.2

        homePositions[i * 3] = Math.cos(angle) * radius
        homePositions[i * 3 + 1] = height
        homePositions[i * 3 + 2] = Math.sin(angle) * radius

        const face = Math.floor(Math.random() * 6)
        const u = (Math.random() - 0.5) * 2 * limit
        const v = (Math.random() - 0.5) * 2 * limit

        const wallIdx = i * 3
        switch (face) {
            case 0: wallPositions[wallIdx] = limit; wallPositions[wallIdx + 1] = u; wallPositions[wallIdx + 2] = v; break
            case 1: wallPositions[wallIdx] = -limit; wallPositions[wallIdx + 1] = u; wallPositions[wallIdx + 2] = v; break
            case 2: wallPositions[wallIdx] = u; wallPositions[wallIdx + 1] = limit; wallPositions[wallIdx + 2] = v; break
            case 3: wallPositions[wallIdx] = u; wallPositions[wallIdx + 1] = -limit; wallPositions[wallIdx + 2] = v; break
            case 4: wallPositions[wallIdx] = u; wallPositions[wallIdx + 1] = v; wallPositions[wallIdx + 2] = limit; break
            default: wallPositions[wallIdx] = u; wallPositions[wallIdx + 1] = v; wallPositions[wallIdx + 2] = -limit
        }

        positions[i * 3] = homePositions[i * 3]
        positions[i * 3 + 1] = homePositions[i * 3 + 1]
        positions[i * 3 + 2] = homePositions[i * 3 + 2]

        colors[i * 3] = 0.3
        colors[i * 3 + 1] = 0.35
        colors[i * 3 + 2] = 0.4

        sizes[i] = 0.015 + Math.random() * 0.02
        phases[i] = Math.random() * Math.PI * 2
        velocities[i * 3] = (Math.random() - 0.5) * 0.008
        velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.008
        velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.008
        activeState[i] = 0
    }

    return { positions, homePositions, wallPositions, colors, sizes, phases, velocities, activeState }
}

// Main component
export function PositronicBrain() {
    const cubeRef = useRef<THREE.Group>(null)
    const meshRef = useRef<THREE.InstancedMesh>(null)
    const colorRef = useRef<THREE.InstancedBufferAttribute>(null)

    const mousePos = useRef({ x: 0, y: 0 })
    const targetRot = useRef({ x: 0, y: 0 })
    const currentRot = useRef({ x: 0, y: 0 })
    const thinkingRef = useRef(false)

    const [thoughts, setThoughts] = useState<Thought[]>([])
    const [synapses, setSynapses] = useState<Synapse[]>([])

    const dummy = useMemo(() => new THREE.Object3D(), [])
    const particleData = useMemo(createParticleData, [])
    const initialColors = useMemo(() => {
        const c = new Float32Array(PARTICLE_COUNT * 3)
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            c[i * 3] = 0.3
            c[i * 3 + 1] = 0.35
            c[i * 3 + 2] = 0.4
        }
        return c
    }, [])

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            mousePos.current.x = (e.clientX / window.innerWidth) * 2 - 1
            mousePos.current.y = -(e.clientY / window.innerHeight) * 2 + 1
        }
        window.addEventListener('mousemove', handleMouseMove)
        return () => window.removeEventListener('mousemove', handleMouseMove)
    }, [])

    const fireSignal = useCallback((thoughtText = "") => {
        thinkingRef.current = true

        const { activeState, positions } = particleData
        const activateCount = Math.floor(PARTICLE_COUNT * 0.15)
        for (let i = 0; i < activateCount; i++) {
            activeState[Math.floor(Math.random() * PARTICLE_COUNT)] = 1
        }

        setTimeout(() => {
            thinkingRef.current = false
            for (let i = 0; i < PARTICLE_COUNT; i++) activeState[i] = 0
        }, 3000)

        if (thoughtText.length > 2) {
            setThoughts((prev: Thought[]) => [...prev, {
                id: Date.now(),
                text: thoughtText.substring(0, 48),
                position: new THREE.Vector3(0, 0, 0)
            }])
        }

        for (let j = 0; j < 5; j++) {
            const i1 = Math.floor(Math.random() * PARTICLE_COUNT) * 3
            const i2 = Math.floor(Math.random() * PARTICLE_COUNT) * 3
            setSynapses((prev: Synapse[]) => [...prev.slice(-30), {
                id: Date.now() + j,
                start: new THREE.Vector3(positions[i1], positions[i1 + 1], positions[i1 + 2]),
                end: new THREE.Vector3(positions[i2], positions[i2 + 1], positions[i2 + 2]),
                color: new THREE.Color(0x00ffff)
            }])
        }
    }, [particleData])

    useEffect(() => {
        (window as any).positronicBrain = { fireSignal }
        return () => { delete (window as any).positronicBrain }
    }, [fireSignal])

    useFrame((state: RootState) => {
        const time = state.clock.getElapsedTime()
        const { positions, homePositions, wallPositions, sizes, phases, velocities, activeState } = particleData

        targetRot.current.x = mousePos.current.y * 0.4
        targetRot.current.y = mousePos.current.x * 0.6
        currentRot.current.x = THREE.MathUtils.lerp(currentRot.current.x, targetRot.current.x, 0.03)
        currentRot.current.y = THREE.MathUtils.lerp(currentRot.current.y, targetRot.current.y, 0.03)

        if (cubeRef.current) {
            cubeRef.current.rotation.x = currentRot.current.x + Math.sin(time * 0.2) * 0.02
            cubeRef.current.rotation.y = currentRot.current.y + Math.sin(time * 0.15) * 0.02
        }

        if (!meshRef.current) return

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const phase = phases[i]
            const isActive = activeState[i] > 0.5
            const idx = i * 3

            const targetX = isActive ? wallPositions[idx] : homePositions[idx]
            const targetY = isActive ? wallPositions[idx + 1] : homePositions[idx + 1]
            const targetZ = isActive ? wallPositions[idx + 2] : homePositions[idx + 2]

            const lerpSpeed = isActive ? 0.08 : 0.02
            positions[idx] = THREE.MathUtils.lerp(positions[idx], targetX, lerpSpeed) + Math.sin(time * 0.8 + phase) * 0.01 + velocities[idx]
            positions[idx + 1] = THREE.MathUtils.lerp(positions[idx + 1], targetY, lerpSpeed) + Math.cos(time * 0.6 + phase) * 0.01 + velocities[idx + 1]
            positions[idx + 2] = THREE.MathUtils.lerp(positions[idx + 2], targetZ, lerpSpeed) + Math.sin(time * 0.5 + phase) * 0.01 + velocities[idx + 2]

            dummy.position.set(positions[idx], positions[idx + 1], positions[idx + 2])
            const scale = sizes[i] * 60 * (1 + Math.sin(time * (isActive ? 5 : 1.5) + phase) * (isActive ? 0.4 : 0.15))
            dummy.scale.setScalar(scale)
            dummy.rotation.set(time * 0.3 + phase, time * 0.2 + phase * 0.7, 0)
            dummy.updateMatrix()
            meshRef.current.setMatrixAt(i, dummy.matrix)

            if (colorRef.current) {
                if (isActive) {
                    const glow = 0.5 + Math.sin(time * 6 + phase) * 0.5
                    colorRef.current.setXYZ(i, 0.2 + glow * 0.3, 0.8 + glow * 0.2, 1.0)
                } else {
                    const subtle = 0.3 + Math.sin(time * 0.5 + phase) * 0.1
                    colorRef.current.setXYZ(i, subtle * 0.6, subtle * 0.7, subtle * 0.8)
                }
            }

            if (Math.random() < 0.003) {
                velocities[idx] = (Math.random() - 0.5) * 0.01
                velocities[idx + 1] = (Math.random() - 0.5) * 0.01
                velocities[idx + 2] = (Math.random() - 0.5) * 0.01
            }
        }

        meshRef.current.instanceMatrix.needsUpdate = true
        if (colorRef.current) colorRef.current.needsUpdate = true

        if (Math.random() < 0.05) {
            const i1 = Math.floor(Math.random() * PARTICLE_COUNT) * 3
            const i2 = Math.floor(Math.random() * PARTICLE_COUNT) * 3
            const dist = Math.hypot(positions[i1] - positions[i2], positions[i1 + 1] - positions[i2 + 1], positions[i1 + 2] - positions[i2 + 2])
            if (dist < 1.0) {
                setSynapses((prev: Synapse[]) => [...prev.slice(-30), {
                    id: Date.now(),
                    start: new THREE.Vector3(positions[i1], positions[i1 + 1], positions[i1 + 2]),
                    end: new THREE.Vector3(positions[i2], positions[i2 + 1], positions[i2 + 2]),
                    color: new THREE.Color(thinkingRef.current ? 0xffaa00 : 0x00ffff)
                }])
            }
        }
    })

    const removeThought = useCallback((id: number) => {
        setThoughts((prev: Thought[]) => prev.filter((t: Thought) => t.id !== id))
    }, [])

    return (
        <group ref={cubeRef}>
            <mesh>
                <boxGeometry args={[CUBE_SIZE * 0.98, CUBE_SIZE * 0.98, CUBE_SIZE * 0.98]} />
                <meshBasicMaterial color={0x00aaff} transparent opacity={0.05} side={THREE.BackSide} depthWrite={false} />
            </mesh>
            <mesh>
                <boxGeometry args={[CUBE_SIZE, CUBE_SIZE, CUBE_SIZE]} />
                <meshBasicMaterial color={0x88ccff} transparent opacity={0.08} side={THREE.DoubleSide} depthWrite={false} />
            </mesh>

            <lineSegments>
                <edgesGeometry args={[new THREE.BoxGeometry(CUBE_SIZE, CUBE_SIZE, CUBE_SIZE)]} />
                <lineBasicMaterial color={0x00ffff} transparent opacity={0.7} />
            </lineSegments>
            <lineSegments>
                <edgesGeometry args={[new THREE.BoxGeometry(CUBE_SIZE * 1.01, CUBE_SIZE * 1.01, CUBE_SIZE * 1.01)]} />
                <lineBasicMaterial color={0x4488ff} transparent opacity={0.3} />
            </lineSegments>

            <instancedMesh ref={meshRef} args={[undefined, undefined, PARTICLE_COUNT]} frustumCulled={false}>
                <icosahedronGeometry args={[0.02, 1]} />
                <meshBasicMaterial vertexColors transparent opacity={0.9} blending={THREE.AdditiveBlending} depthWrite={false} />
                <instancedBufferAttribute ref={colorRef} attach="geometry-attributes-color" args={[initialColors, 3]} />
            </instancedMesh>

            {synapses.slice(-30).map(syn => <SynapticFlash key={syn.id} {...syn} />)}
            {thoughts.map(thought => <ThoughtNode key={thought.id} {...thought} onComplete={() => removeThought(thought.id)} />)}

            <pointLight position={[0, 0, 0]} color={0x60a5fa} intensity={2} distance={8} />
            <pointLight position={[0, 0, 0]} color={0x88ccff} intensity={1.5} distance={12} />
        </group>
    )
}

export default PositronicBrain
