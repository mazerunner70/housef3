import React, { useState, useEffect, useRef } from 'react';

export interface EditableCellOption {
  id: string;
  name: string;
}

export interface EditableCellDialogProps {
  value: string;
  displayValue?: string;
  options: EditableCellOption[];
  onSave: (newValue: string, newOptions?: EditableCellOption[]) => Promise<void> | void;
  onCancel: () => void;
  isOpen: boolean;
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
  dialogComponent?: React.ComponentType<EditableCellDialogProps> | null; // Dialog component for advanced editing
  onOptionsUpdate?: (newOptions: EditableCellOption[]) => void; // Callback when options are updated via dialog
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
  dialogComponent: DialogComponent = null,
  onOptionsUpdate,
}) => {
  const [editValue, setEditValue] = useState(value);
  const [isSaving, setIsSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const selectRef = useRef<HTMLSelectElement>(null);

  // Update edit value when prop value changes
  useEffect(() => {
    if (!isEditing) {
      setEditValue(value);
      setValidationError(null);
    }
  }, [value, isEditing]);

  // Ensure editValue is set when entering edit mode for select
  useEffect(() => {
    if (isEditing && type === 'select') {
      // If current value doesn't match any option ID, try to find by display value
      const hasMatchingOption = options.some(option => option.id === value);
      if (!hasMatchingOption && displayValue) {
        const matchingOption = options.find(option => option.name === displayValue);
        if (matchingOption) {
          setEditValue(matchingOption.id);
        } else {
          setEditValue(value || '');
        }
      } else {
        setEditValue(value || '');
      }
    }
  }, [isEditing, type, value, displayValue, options]);

  // Auto-focus when entering edit mode
  useEffect(() => {
    if (isEditing && autoFocus) {
      if (type === 'select' && selectRef.current) {
        selectRef.current.focus();
      } else if ((type === 'text' || type === 'number') && inputRef.current) {
        inputRef.current.focus();
        inputRef.current.select();
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

  const handleCellClick = () => {
    if (disabled) return;
    
    if (DialogComponent) {
      setIsDialogOpen(true);
    } else {
      onStartEdit();
    }
  };

  const handleDialogSave = async (newValue: string, newOptions?: EditableCellOption[]) => {
    try {
      if (newOptions && onOptionsUpdate) {
        onOptionsUpdate(newOptions);
      }
      await onSave(newValue);
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Error saving from dialog:', error);
      // Could propagate error to dialog component here if needed
    }
  };

  const handleDialogCancel = () => {
    setIsDialogOpen(false);
    if (onCancel) {
      onCancel();
    }
  };

  const renderInput = () => {
    const inputClassName = `editable-input ${validationError ? 'editable-input-error' : ''}`;

    switch (type) {
      case 'select':
        return (
          <select
            ref={selectRef}
            value={editValue}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            className={inputClassName}
            disabled={isSaving}
          >
            <option value="">{placeholder || "-- Select --"}</option>
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
            ref={inputRef}
            type="number"
            value={editValue}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            className={inputClassName}
            disabled={isSaving}
            placeholder={placeholder}
            min={min}
            max={max}
            step={step}
          />
        );
      case 'text':
      default:
        return (
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            className={inputClassName}
            disabled={isSaving}
            placeholder={placeholder}
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
    <>
      <div
        className={`editable-cell-container ${disabled ? 'disabled' : 'clickable'} ${className}`}
        onClick={handleCellClick}
        onKeyDown={disabled ? undefined : (e) => e.key === 'Enter' && handleCellClick()}
        tabIndex={disabled ? -1 : 0}
        role="button"
        aria-label={`Edit ${displayValue || value || 'value'}`}
      >
        <span className="editable-display-value">
          {displayValue || value || placeholder || 'N/A'}
        </span>
        {!disabled && (
          <span className="editable-edit-hint" title="Edit">✎</span>
        )}
      </div>
      
      {DialogComponent && (
        <DialogComponent
          value={value}
          displayValue={displayValue}
          options={options}
          onSave={handleDialogSave}
          onCancel={handleDialogCancel}
          isOpen={isDialogOpen}
        />
      )}
    </>
  );
};

export default EditableCell; 