import React, { useState, useRef, useEffect } from 'react';
import './CustomMultiSelect.css';

interface Option {
    value: string;
    label: string;
}

interface CustomMultiSelectProps {
    options: Option[];
    selectedValues: string[];
    onSelectionChange: (selectedValues: string[]) => void;
    placeholder?: string;
    className?: string;
    disabled?: boolean;
    id?: string;
    label?: string;
}

const CustomMultiSelect: React.FC<CustomMultiSelectProps> = ({
    options,
    selectedValues,
    onSelectionChange,
    placeholder = "Select options...",
    className = "",
    disabled = false,
    id,
    label
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [focusedIndex, setFocusedIndex] = useState(-1);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const optionsRef = useRef<HTMLDivElement[]>([]);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                setFocusedIndex(-1);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Handle keyboard navigation
    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (disabled) return;

        switch (event.key) {
            case 'Enter':
            case ' ':
                event.preventDefault();
                if (!isOpen) {
                    setIsOpen(true);
                    setFocusedIndex(0);
                } else if (focusedIndex >= 0) {
                    toggleOption(options[focusedIndex].value);
                }
                break;
            case 'Escape':
                event.preventDefault();
                setIsOpen(false);
                setFocusedIndex(-1);
                triggerRef.current?.focus();
                break;
            case 'ArrowDown':
                event.preventDefault();
                if (!isOpen) {
                    setIsOpen(true);
                    setFocusedIndex(0);
                } else {
                    setFocusedIndex(prev => Math.min(prev + 1, options.length - 1));
                }
                break;
            case 'ArrowUp':
                event.preventDefault();
                if (isOpen) {
                    setFocusedIndex(prev => Math.max(prev - 1, 0));
                }
                break;
            case 'Tab':
                if (isOpen) {
                    setIsOpen(false);
                    setFocusedIndex(-1);
                }
                break;
        }
    };

    const toggleOption = (value: string) => {
        if (disabled) return;

        const newSelectedValues = selectedValues.includes(value)
            ? selectedValues.filter(v => v !== value)
            : [...selectedValues, value];

        onSelectionChange(newSelectedValues);
    };

    const getDisplayText = () => {
        if (selectedValues.length === 0) {
            return placeholder;
        }

        if (selectedValues.length === 1) {
            const selectedOption = options.find(opt => opt.value === selectedValues[0]);
            return selectedOption ? selectedOption.label : selectedValues[0];
        }

        return `${selectedValues.length} selected`;
    };

    const getAriaLabel = () => {
        if (selectedValues.length === 0) {
            return `${label || 'Multi-select'}, no options selected`;
        }

        if (selectedValues.length === 1) {
            const selectedOption = options.find(opt => opt.value === selectedValues[0]);
            return `${label || 'Multi-select'}, ${selectedOption?.label || selectedValues[0]} selected`;
        }

        return `${label || 'Multi-select'}, ${selectedValues.length} options selected`;
    };

    return (
        <div className={`custom-multi-select ${className}`} ref={dropdownRef}>
            {label && (
                <label id={`${id}-label`} className="multi-select-label">
                    {label}
                </label>
            )}
            <button
                ref={triggerRef}
                id={id}
                className={`multi-select-trigger ${isOpen ? 'open' : ''} ${disabled ? 'disabled' : ''}`}
                onClick={() => !disabled && setIsOpen(!isOpen)}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                aria-haspopup="listbox"
                aria-expanded={isOpen}
                aria-label={getAriaLabel()}
                aria-labelledby={label ? `${id}-label` : undefined}
                type="button"
            >
                <span className="multi-select-text">{getDisplayText()}</span>
                <span className="multi-select-arrow" aria-hidden="true">▼</span>
            </button>

            {isOpen && (
                <div
                    className="multi-select-dropdown"
                    role="listbox"
                    aria-multiselectable="true"
                    aria-labelledby={label ? `${id}-label` : undefined}
                >
                    {options.length === 0 ? (
                        <div className="multi-select-option disabled" role="option" aria-disabled="true">
                            No options available
                        </div>
                    ) : (
                        options.map((option, index) => {
                            const isSelected = selectedValues.includes(option.value);
                            const isFocused = index === focusedIndex;
                            return (
                                <div
                                    key={option.value}
                                    ref={el => { if (el) optionsRef.current[index] = el; }}
                                    className={`multi-select-option ${isSelected ? 'selected' : ''} ${isFocused ? 'focused' : ''}`}
                                    onClick={() => toggleOption(option.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            toggleOption(option.value);
                                        }
                                    }}
                                    onMouseEnter={() => setFocusedIndex(index)}
                                    role="option"
                                    aria-selected={isSelected}
                                    aria-label={`${option.label}, ${isSelected ? 'selected' : 'not selected'}`}
                                    tabIndex={-1}
                                >
                                    <span className="option-checkbox" aria-hidden="true">
                                        {isSelected ? '☑️' : '☐'}
                                    </span>
                                    <span className="option-label">{option.label}</span>
                                </div>
                            );
                        })
                    )}
                </div>
            )}
        </div>
    );
};

export default CustomMultiSelect;

