import React, { useState, useEffect, useRef } from 'react';

export interface EditableCellOption {
  id: string;
  name: string;
}

interface EditableCellProps {
  value: string;
  displayValue?: string; // For cases where display differs from value (e.g., showing name but storing ID)
  options?: EditableCellOption[];
  onSave: (newValue: string) => Promise<void> | void;
  onCancel?: () => void;
  type: 'select' | 'text' | 'number';
  isEditing: boolean;
  onStartEdit: () => void;
  onEndEdit: () => void;
  className?: string;
  placeholder?: string;
  disabled?: boolean;
  maxLength?: number;
  min?: number;
  max?: number;
  step?: number;
  autoFocus?: boolean;
  validation?: (value: string) => string | null; // Returns error message or null
}

const EditableCell: React.FC<EditableCellProps> = ({
  value,
  displayValue,
  options = [],
  onSave,
  onCancel,
  type,
  isEditing,
  onStartEdit,
  onEndEdit,
  className = '',
  placeholder = '',
  disabled = false,
  maxLength,
  min,
  max,
  step,
  autoFocus = true,
  validation,
}) => {
  const [editValue, setEditValue] = useState(value);
  const [isSaving, setIsSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement>(null);

  // Update edit value when prop value changes
  useEffect(() => {
    if (!isEditing) {
      setEditValue(value);
      setValidationError(null);
    }
  }, [value, isEditing]);

  // Auto-focus when entering edit mode
  useEffect(() => {
    if (isEditing && autoFocus && inputRef.current) {
      inputRef.current.focus();
      if (type === 'text' || type === 'number') {
        (inputRef.current as HTMLInputElement).select();
      }
    }
  }, [isEditing, autoFocus, type]);

  const handleSave = async () => {
    // Validate if validation function is provided
    if (validation) {
      const error = validation(editValue);
      if (error) {
        setValidationError(error);
        return;
      }
    }

    // Don't save if value hasn't changed
    if (editValue === value) {
      handleCancel();
      return;
    }

    setIsSaving(true);
    setValidationError(null);

    try {
      await onSave(editValue);
      onEndEdit();
    } catch (error) {
      console.error('Error saving editable cell:', error);
      setValidationError(error instanceof Error ? error.message : 'Save failed');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditValue(value);
    setValidationError(null);
    onEndEdit();
    if (onCancel) {
      onCancel();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const newValue = e.target.value;
    setEditValue(newValue);
    
    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError(null);
    }
  };

  const renderInput = () => {
    const baseProps = {
      ref: inputRef,
      value: editValue,
      onChange: handleChange,
      onKeyDown: handleKeyDown,
      className: `editable-input ${validationError ? 'editable-input-error' : ''}`,
      disabled: isSaving,
      placeholder,
    };

    switch (type) {
      case 'select':
        return (
          <select {...baseProps}>
            <option value="">-- Select --</option>
            {options.map(option => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        );
      case 'number':
        return (
          <input
            type="number"
            {...baseProps}
            min={min}
            max={max}
            step={step}
          />
        );
      case 'text':
      default:
        return (
          <input
            type="text"
            {...baseProps}
            maxLength={maxLength}
          />
        );
    }
  };

  if (isEditing) {
    return (
      <div className={`editable-cell-container editing ${className}`}>
        <div className="editable-input-wrapper">
          {renderInput()}
          <div className="editable-actions">
            <button
              type="button"
              className="editable-action-save"
              onClick={handleSave}
              disabled={isSaving}
              title="Save (Enter)"
            >
              {isSaving ? '⏳' : '✓'}
            </button>
            <button
              type="button"
              className="editable-action-cancel"
              onClick={handleCancel}
              disabled={isSaving}
              title="Cancel (Escape)"
            >
              ✗
            </button>
          </div>
        </div>
        {validationError && (
          <div className="editable-validation-error">
            {validationError}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`editable-cell-container ${disabled ? 'disabled' : 'clickable'} ${className}`}
      onClick={disabled ? undefined : onStartEdit}
      onKeyDown={disabled ? undefined : (e) => e.key === 'Enter' && onStartEdit()}
      tabIndex={disabled ? -1 : 0}
      role="button"
      aria-label={`Edit ${displayValue || value || 'value'}`}
    >
      <span className="editable-display-value">
        {displayValue || value || placeholder || 'N/A'}
      </span>
      {!disabled && (
        <span className="editable-edit-hint">✎</span>
      )}
    </div>
  );
};

export default EditableCell; 