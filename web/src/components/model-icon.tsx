import Image from "next/image";

interface ModelIconProps {
  provider: string;
}

export const ModelIcon = ({ provider }: ModelIconProps) => {
  const iconMap: Record<string, { src: string; alt: string }> = {
    openai: { src: "/openai.svg", alt: "OpenAI" },
    anthropic: { src: "/anthropic.svg", alt: "Anthropic" },
    gemini: { src: "/google.svg", alt: "Google" },
  };

  if (iconMap[provider]) {
    const { src, alt } = iconMap[provider]!;
    return <Image src={src} alt={alt} width={20} height={20} className="w-5 h-5" />;
  }
  return <span className="text-lg">🤖</span>;
};