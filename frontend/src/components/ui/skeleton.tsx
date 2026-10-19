/** Props for `Skeleton`. */
export interface SkeletonProps {
  readonly className?: string;
}

/** A placeholder bar that breathes while content loads; it stays still under reduced motion. */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={`block rounded-control bg-rule/70 motion-safe:animate-shimmer ${className}`}
    />
  );
}
