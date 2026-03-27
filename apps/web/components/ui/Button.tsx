import React, { ButtonHTMLAttributes } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    // Generate class names based on our CSS design system
    const baseClass = "btn";
    const variantClass = variant !== "primary" ? `btn--${variant}` : "";
    const sizeClass = size !== "md" ? `btn--${size}` : "";
    const loadingClass = isLoading ? "btn--loading" : "";
    
    const combinedClassName = [baseClass, variantClass, sizeClass, loadingClass, className]
      .filter(Boolean)
      .join(" ");

    return (
      <button
        ref={ref}
        className={combinedClassName}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <span className="spinner" aria-hidden="true" />}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
