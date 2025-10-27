import React from 'react';
import './Button.css'; // We'll create this CSS module next

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'tertiary' | 'danger';
    size?: 'standard' | 'compact';
    children: React.ReactNode;
}

const Button: React.FC<ButtonProps> = ({
    children,
    variant = 'primary',
    size = 'standard',
    className = '',
    ...props
}) => {
    const buttonClasses = `btn btn--${variant} btn--${size} ${className}`.trim();

    return (
        <button className={buttonClasses} {...props}>
            {children}
        </button>
    );
};

export default Button;

