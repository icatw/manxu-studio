import type { ImgHTMLAttributes } from "react";

type ImageProps = ImgHTMLAttributes<HTMLImageElement> & {
  fill?: boolean;
  priority?: boolean;
  sizes?: string;
};

export default function Image({ fill = false, priority = false, sizes, style, loading, ...props }: ImageProps) {
  return (
    <img
      {...props}
      sizes={sizes}
      loading={priority ? "eager" : loading}
      style={
        fill
          ? { position: "absolute", inset: 0, width: "100%", height: "100%", ...style }
          : style
      }
    />
  );
}
