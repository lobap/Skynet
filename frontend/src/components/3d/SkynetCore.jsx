import { useRef, useMemo, useState, useCallback, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { Html, Instances, Instance } from '@react-three/drei'

// Synaptic flash with spark effect
function SynapticFlash({ start, end, color }) {
    const lineRef = useRef()
    const [opacity, setOpacity] = useState(1)

    useFrame((_, delta) => {
        setOpacity(prev => Math.max(0, prev - delta * 3))
    })

    if (opacity <= 0) return null

    const points = [start, end]
    const geometry = new THREE.BufferGeometry().setFromPoints(points)

    return (
        <group>
            <line ref={lineRef}>
                <bufferGeometry attach="geometry" {...geometry} />
                <lineBasicMaterial
                    color={color}
                    transparent
                    opacity={opacity * 0.9}
                    linewidth={2}
                />
            </line>
            {/* Spark at midpoint */}
            <mesh position={[
                (start.x + end.x) / 2,
                (start.y + end.y) / 2,
                (start.z + end.z) / 2
            ]}>
                <sphereGeometry args={[0.05 * opacity, 8, 8]} />
                <meshBasicMaterial color={color} transparent opacity={opacity} />
            </mesh>
        </group>
    )
}

// 3D Neuron particle with dynamic scaling and color
function Neuron({ index, data, isThinking }) {
    const instanceRef = useRef()
    const { positions, homePositions, wallPositions, colors, sizes, phases, velocities, activeState } = data

    useFrame((state) => {
        if (!instanceRef.current) return
        const time = state.clock.getElapsedTime()
        const i = index
        const phase = phases[i]
        const isActive = activeState[i] > 0.5

        // Target position based on state
        const targetX = isActive ? wallPositions[i * 3] : homePositions[i * 3]
        const targetY = isActive ? wallPositions[i * 3 + 1] : homePositions[i * 3 + 1]
        const targetZ = isActive ? wallPositions[i * 3 + 2] : homePositions[i * 3 + 2]

        // Lerp toward target with organic movement
        const lerpSpeed = isActive ? 0.08 : 0.02
        const breathX = Math.sin(time * 0.8 + phase) * 0.015
        const breathY = Math.cos(time * 0.6 + phase * 1.3) * 0.015
        const breathZ = Math.sin(time * 0.5 + phase * 0.8) * 0.015

        positions[i * 3] = THREE.MathUtils.lerp(positions[i * 3], targetX, lerpSpeed) + breathX + velocities[i * 3]
        positions[i * 3 + 1] = THREE.MathUtils.lerp(positions[i * 3 + 1], targetY, lerpSpeed) + breathY + velocities[i * 3 + 1]
        positions[i * 3 + 2] = THREE.MathUtils.lerp(positions[i * 3 + 2], targetZ, lerpSpeed) + breathZ + velocities[i * 3 + 2]

        // Update instance position
        instanceRef.current.position.set(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2])

        // Dynamic scale (much smaller, pulsing)
        const pulseMag = isActive ? 0.4 : 0.15
        const pulseSpeed = isActive ? 5 : 1.5
        const baseScale = sizes[i] * 4  // Much smaller base
        const scaleX = baseScale * (1 + Math.sin(time * pulseSpeed + phase) * pulseMag)
        const scaleY = baseScale * (1 + Math.cos(time * pulseSpeed * 1.3 + phase) * pulseMag * 0.6)
        const scaleZ = baseScale * (1 + Math.sin(time * pulseSpeed * 0.8 + phase * 1.5) * pulseMag * 0.8)
        instanceRef.current.scale.set(scaleX, scaleY, scaleZ)

        // Dynamic color based on state
        if (isActive) {
            // Active: bright cyan/purple pulse
            const glow = 0.5 + Math.sin(time * 6 + phase) * 0.5
            instanceRef.current.color.setRGB(
                0.2 + glow * 0.3,
                0.8 + glow * 0.2,
                1.0
            )
        } else {
            // Idle: subtle gray with slight color tint
            const subtle = 0.3 + Math.sin(time * 0.5 + phase) * 0.1
            instanceRef.current.color.setRGB(
                subtle * 0.6,
                subtle * 0.7,
                subtle * 0.8
            )
        }

        // Dynamic rotation for organic feel
        instanceRef.current.rotation.x = time * 0.5 + phase
        instanceRef.current.rotation.y = time * 0.3 + phase * 0.7

        // Random velocity changes
        if (Math.random() < 0.005) {
            velocities[i * 3] = (Math.random() - 0.5) * 0.012
            velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.012
            velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.012
        }
    })

    // Set color from gradient
    const color = new THREE.Color(colors[index * 3], colors[index * 3 + 1], colors[index * 3 + 2])

    return (
        <Instance
            ref={instanceRef}
            position={[positions[index * 3], positions[index * 3 + 1], positions[index * 3 + 2]]}
            color={new THREE.Color(0.4, 0.5, 0.6)}  // Initial gray color
        />
    )
}

// Thought popup bubble
function ThoughtNode({ text, position, onComplete }) {
    const [life, setLife] = useState(0)
    const [opacity, setOpacity] = useState(0)
    const [currentPos, setCurrentPos] = useState(position.clone())
    const targetPos = useMemo(() => {
        const theta = Math.random() * Math.PI * 2
        const phi = Math.acos(2 * Math.random() - 1) * 0.5
        // Keep popups closer to center to stay in canvas
        return new THREE.Vector3(
            2.0 * Math.sin(phi) * Math.cos(theta),
            2.0 * Math.sin(phi) * Math.sin(theta),
            2.0 * Math.cos(phi)
        )
    }, [])

    useFrame((_, delta) => {
        setLife(prev => {
            const newLife = prev + delta
            if (newLife < 0.5) setOpacity(newLife * 2)
            else if (newLife > 5) setOpacity(Math.max(0, (6 - newLife) * 1))
            else setOpacity(1)
            if (newLife >= 6) { onComplete?.(); return prev }
            return newLife
        })
        if (currentPos && targetPos) {
            setCurrentPos(prev => prev.clone().lerp(targetPos, 0.03))
        }
    })

    if (life >= 6 || opacity <= 0) return null
    const displayText = text.length > 50 ? text.substring(0, 47) + '...' : text

    return (
        <Html position={[currentPos.x, currentPos.y, currentPos.z]} center
            style={{ opacity, transition: 'opacity 0.2s', pointerEvents: 'none' }}>
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

export function PositronicBrain() {
    const cubeRef = useRef()
    const particlesRef = useRef()
    const { size, viewport } = useThree()

    const PARTICLE_COUNT = 2500
    const CUBE_SIZE = 2.2  // Smaller cube

    // Mouse tracking for cursor-follow
    const mousePos = useRef({ x: 0, y: 0 })
    const targetRot = useRef({ x: 0, y: 0 })
    const currentRot = useRef({ x: 0, y: 0 })

    const [thoughts, setThoughts] = useState([])
    const [synapses, setSynapses] = useState([])
    const [isThinking, setIsThinking] = useState(false)
    const thinkingRef = useRef(false)

    // Track mouse globally
    useEffect(() => {
        const handleMouseMove = (e) => {
            mousePos.current.x = (e.clientX / window.innerWidth) * 2 - 1
            mousePos.current.y = -(e.clientY / window.innerHeight) * 2 + 1
        }
        window.addEventListener('mousemove', handleMouseMove)
        return () => window.removeEventListener('mousemove', handleMouseMove)
    }, [])

    // Generate particle data with home positions (cylinder) and wall positions
    const particleData = useMemo(() => {
        const positions = new Float32Array(PARTICLE_COUNT * 3)
        const homePositions = new Float32Array(PARTICLE_COUNT * 3)
        const wallPositions = new Float32Array(PARTICLE_COUNT * 3)
        const colors = new Float32Array(PARTICLE_COUNT * 3)
        const sizes = new Float32Array(PARTICLE_COUNT)
        const phases = new Float32Array(PARTICLE_COUNT)
        const velocities = new Float32Array(PARTICLE_COUNT * 3)
        const activeState = new Float32Array(PARTICLE_COUNT) // 0=idle, 1=thinking

        const baseColor = new THREE.Color(0x60a5fa)
        const limit = (CUBE_SIZE / 2) - 0.15

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            // Cylinder formation (home position)
            const angle = (i / PARTICLE_COUNT) * Math.PI * 2 * 8 + Math.random() * 0.5
            const radius = 0.3 + Math.random() * 0.7
            const height = (Math.random() - 0.5) * 2.2

            homePositions[i * 3] = Math.cos(angle) * radius
            homePositions[i * 3 + 1] = height
            homePositions[i * 3 + 2] = Math.sin(angle) * radius

            // Wall positions (thinking state)
            const face = Math.floor(Math.random() * 6)
            const u = (Math.random() - 0.5) * 2 * limit
            const v = (Math.random() - 0.5) * 2 * limit
            switch (face) {
                case 0: wallPositions[i * 3] = limit; wallPositions[i * 3 + 1] = u; wallPositions[i * 3 + 2] = v; break
                case 1: wallPositions[i * 3] = -limit; wallPositions[i * 3 + 1] = u; wallPositions[i * 3 + 2] = v; break
                case 2: wallPositions[i * 3] = u; wallPositions[i * 3 + 1] = limit; wallPositions[i * 3 + 2] = v; break
                case 3: wallPositions[i * 3] = u; wallPositions[i * 3 + 1] = -limit; wallPositions[i * 3 + 2] = v; break
                case 4: wallPositions[i * 3] = u; wallPositions[i * 3 + 1] = v; wallPositions[i * 3 + 2] = limit; break
                case 5: wallPositions[i * 3] = u; wallPositions[i * 3 + 1] = v; wallPositions[i * 3 + 2] = -limit; break
            }

            // Start at home
            positions[i * 3] = homePositions[i * 3]
            positions[i * 3 + 1] = homePositions[i * 3 + 1]
            positions[i * 3 + 2] = homePositions[i * 3 + 2]

            // Dynamic particle colors - cyan to purple gradient
            const colorPhase = (i / PARTICLE_COUNT)
            const color1 = new THREE.Color(0x00ffff)  // Cyan
            const color2 = new THREE.Color(0x8855ff)  // Purple
            const mixedColor = color1.clone().lerp(color2, colorPhase)
            const variation = 0.8 + Math.random() * 0.4
            colors[i * 3] = mixedColor.r * variation
            colors[i * 3 + 1] = mixedColor.g * variation
            colors[i * 3 + 2] = mixedColor.b * variation

            sizes[i] = 0.08 + Math.random() * 0.12
            phases[i] = Math.random() * Math.PI * 2
            velocities[i * 3] = (Math.random() - 0.5) * 0.01
            velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.01
            velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.01
            activeState[i] = 0
        }

        return { positions, homePositions, wallPositions, colors, sizes, phases, velocities, activeState }
    }, [])

    // Fire signal - exposed globally
    const fireSignal = useCallback((thoughtText = "") => {
        const text = thoughtText.toLowerCase()
        let color = 0x60a5fa

        if (text.includes("error") || text.includes("fail")) color = 0xf87171
        else if (text.includes("plan") || text.includes("think")) color = 0xd946ef
        else if (text.includes("code") || text.includes("function")) color = 0x34d399
        else if (text.includes("tool") || text.includes("command")) color = 0xfbbf24

        // Activate thinking state
        setIsThinking(true)
        thinkingRef.current = true

        // Activate random subset of particles
        const { activeState } = particleData
        const activateCount = Math.floor(PARTICLE_COUNT * 0.15)
        for (let i = 0; i < activateCount; i++) {
            const idx = Math.floor(Math.random() * PARTICLE_COUNT)
            activeState[idx] = 1
        }

        // Deactivate after delay
        setTimeout(() => {
            setIsThinking(false)
            thinkingRef.current = false
            for (let i = 0; i < PARTICLE_COUNT; i++) {
                activeState[i] = 0
            }
        }, 3000)

        // Add thought popup
        if (thoughtText.length > 2) {
            setThoughts(prev => [...prev, {
                id: Date.now(),
                text: thoughtText.substring(0, 48),
                position: new THREE.Vector3(0, 0, 0)
            }])
        }

        // Create synaptic flashes
        if (particlesRef.current) {
            const positions = particlesRef.current.geometry.attributes.position.array
            for (let j = 0; j < 5; j++) {
                const i1 = Math.floor(Math.random() * PARTICLE_COUNT) * 3
                const i2 = Math.floor(Math.random() * PARTICLE_COUNT) * 3
                setSynapses(prev => [...prev.slice(-30), {
                    id: Date.now() + j,
                    start: new THREE.Vector3(positions[i1], positions[i1 + 1], positions[i1 + 2]),
                    end: new THREE.Vector3(positions[i2], positions[i2 + 1], positions[i2 + 2]),
                    color: new THREE.Color(color)
                }])
            }
        }
    }, [particleData])

    // Expose globally
    useEffect(() => {
        window.positronicBrain = { fireSignal }
        return () => { delete window.positronicBrain }
    }, [fireSignal])

    // Animation loop - cursor follow and synapse generation only
    useFrame((state) => {
        const time = state.clock.getElapsedTime()

        // Phase 1: Cursor-following with inertia
        targetRot.current.x = mousePos.current.y * 0.4
        targetRot.current.y = mousePos.current.x * 0.6
        currentRot.current.x = THREE.MathUtils.lerp(currentRot.current.x, targetRot.current.x, 0.03)
        currentRot.current.y = THREE.MathUtils.lerp(currentRot.current.y, targetRot.current.y, 0.03)

        if (cubeRef.current) {
            cubeRef.current.rotation.x = currentRot.current.x + Math.sin(time * 0.2) * 0.02
            cubeRef.current.rotation.y = currentRot.current.y + Math.sin(time * 0.15) * 0.02
        }

        // Random synaptic flashes
        if (Math.random() < 0.06) {
            const { positions } = particleData
            const i1 = Math.floor(Math.random() * PARTICLE_COUNT) * 3
            const i2 = Math.floor(Math.random() * PARTICLE_COUNT) * 3

            const dist = Math.sqrt(
                Math.pow(positions[i1] - positions[i2], 2) +
                Math.pow(positions[i1 + 1] - positions[i2 + 1], 2) +
                Math.pow(positions[i1 + 2] - positions[i2 + 2], 2)
            )

            if (dist < 1.2) {
                setSynapses(prev => [...prev.slice(-40), {
                    id: Date.now(),
                    start: new THREE.Vector3(positions[i1], positions[i1 + 1], positions[i1 + 2]),
                    end: new THREE.Vector3(positions[i2], positions[i2 + 1], positions[i2 + 2]),
                    color: new THREE.Color(thinkingRef.current ? 0xffaa00 : 0x00ffff)
                }])
            }
        }
    })

    const removeThought = useCallback((id) => {
        setThoughts(prev => prev.filter(t => t.id !== id))
    }, [])

    return (
        <group ref={cubeRef}>
            {/* Glass Cube - layered crystal effect */}
            {/* Inner glow layer */}
            <mesh>
                <boxGeometry args={[CUBE_SIZE * 0.98, CUBE_SIZE * 0.98, CUBE_SIZE * 0.98]} />
                <meshBasicMaterial
                    color={0x00aaff}
                    transparent
                    opacity={0.05}
                    side={THREE.BackSide}
                    depthWrite={false}
                />
            </mesh>
            {/* Outer translucent layer */}
            <mesh>
                <boxGeometry args={[CUBE_SIZE, CUBE_SIZE, CUBE_SIZE]} />
                <meshBasicMaterial
                    color={0x88ccff}
                    transparent
                    opacity={0.08}
                    side={THREE.DoubleSide}
                    depthWrite={false}
                />
            </mesh>

            {/* Glowing wireframe edges */}
            <lineSegments>
                <edgesGeometry args={[new THREE.BoxGeometry(CUBE_SIZE, CUBE_SIZE, CUBE_SIZE)]} />
                <lineBasicMaterial color={0x00ffff} transparent opacity={0.7} />
            </lineSegments>
            {/* Second wireframe for depth */}
            <lineSegments>
                <edgesGeometry args={[new THREE.BoxGeometry(CUBE_SIZE * 1.01, CUBE_SIZE * 1.01, CUBE_SIZE * 1.01)]} />
                <lineBasicMaterial color={0x4488ff} transparent opacity={0.3} />
            </lineSegments>

            {/* 3D Particles (neurons) - Instanced Spheres */}
            <Instances limit={PARTICLE_COUNT} ref={particlesRef}>
                <icosahedronGeometry args={[0.04, 1]} />
                <meshBasicMaterial
                    color={0x00ffff}
                    transparent
                    opacity={0.9}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
                {Array.from({ length: PARTICLE_COUNT }).map((_, i) => (
                    <Neuron
                        key={i}
                        index={i}
                        data={particleData}
                        isThinking={isThinking}
                    />
                ))}
            </Instances>

            {/* Synaptic flashes */}
            {synapses.slice(-50).map(syn => (
                <SynapticFlash key={syn.id} {...syn} />
            ))}

            {/* Thought popups */}
            {thoughts.map(thought => (
                <ThoughtNode key={thought.id} {...thought} onComplete={() => removeThought(thought.id)} />
            ))}

            {/* Inner glow light */}
            <pointLight position={[0, 0, 0]} color={0x60a5fa} intensity={3} distance={10} />
            <pointLight position={[0, 0, 0]} color={0x88ccff} intensity={2} distance={15} />
        </group>
    )
}

export default PositronicBrain
