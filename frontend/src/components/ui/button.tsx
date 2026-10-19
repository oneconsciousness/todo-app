import type { ComponentProps } from "react";

const variants = {
  primary: "bg-primary text-on-primary hover:bg-primary-strong",
  secondary: "border border-rule-strong bg-sheet text-ink hover:border-ink",
  ghost: "text-ink-muted hover:bg-rule/40 hover:text-ink",
  danger: "bg-alert text-on-primary hover:bg-alert/90",
  binding: "border border-gilt/60 text-on-binding hover:border-gilt hover:text-gilt",
} as const;

/** The visual weight of a button. */
export type ButtonVariant = keyof typeof variants;

/** The classes of a button in one variant, so a link that acts as a button looks like one. */
export const buttonClass = (variant: ButtonVariant): string =>
  `inline-flex min-h-touch min-w-touch shrink-0 cursor-pointer items-center justify-center gap-2 rounded-control px-4 font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]}`;

/** Props for `Button`: a native button plus its variant. */
export interface ButtonProps extends ComponentProps<"button"> {
  readonly variant?: ButtonVariant;
}

/** A real button, at least 44px tall, in one of five weights. */
export function Button({
  variant = "secondary",
  type = "button",
  className = "",
  ...props
}: ButtonProps) {
  return <button type={type} className={`${buttonClass(variant)} ${className}`} {...props} />;
}
