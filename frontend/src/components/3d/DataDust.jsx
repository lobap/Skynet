import { Sparkles, Stars } from '@react-three/drei'

export function DataDust() {
    return (
        <>
            {/* Background stars */}
            <Stars
                radius={50}
                depth={50}
                count={2000}
                factor={4}
                saturation={0}
                fade
                speed={0.5}
            />

            {/* Floating sparkles near core */}
            <Sparkles
                count={200}
                scale={10}
                size={2}
                speed={0.3}
                opacity={0.5}
                color="#00f3ff"
            />

            {/* Secondary sparkles */}
            <Sparkles
                count={100}
                scale={15}
                size={1.5}
                speed={0.2}
                opacity={0.3}
                color="#ff00ff"
            />
        </>
    )
}

export default DataDust
