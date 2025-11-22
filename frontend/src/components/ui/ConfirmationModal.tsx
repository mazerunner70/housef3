import React, { useEffect, useRef } from 'react';
import './ConfirmationModal.css';

interface ConfirmationModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    confirmButtonText?: string;
    cancelButtonText?: string;
    onConfirm: () => void;
    onCancel: () => void;
    isLoading?: boolean;
    type?: 'danger' | 'warning' | 'info';
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
    isOpen,
    title,
    message,
    confirmButtonText = 'Confirm',
    cancelButtonText = 'Cancel',
    onConfirm,
    onCancel,
    isLoading = false,
    type = 'warning'
}) => {
    const modalRef = useRef<HTMLDivElement>(null);
    const confirmButtonRef = useRef<HTMLButtonElement>(null);
    const previousActiveElementRef = useRef<HTMLElement | null>(null);

    // Focus management: Save previous focus and restore on close
    useEffect(() => {
        if (isOpen) {
            // Save the currently focused element
            previousActiveElementRef.current = document.activeElement as HTMLElement;

            // Focus the confirm button when modal opens
            setTimeout(() => {
                confirmButtonRef.current?.focus();
            }, 100);
        } else {
            // Restore focus when modal closes
            if (previousActiveElementRef.current) {
                previousActiveElementRef.current.focus();
            }
        }
    }, [isOpen]);

    // Focus trap: Keep focus within modal
    useEffect(() => {
        if (!isOpen) return;

        const handleTabKey = (e: KeyboardEvent) => {
            if (e.key !== 'Tab') return;

            const modal = modalRef.current;
            if (!modal) return;

            const focusableElements = modal.querySelectorAll<HTMLElement>(
                'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            if (e.shiftKey) {
                // Shift + Tab: moving backwards
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement?.focus();
                }
            } else {
                // Tab: moving forwards
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement?.focus();
                }
            }
        };

        document.addEventListener('keydown', handleTabKey);
        return () => document.removeEventListener('keydown', handleTabKey);
    }, [isOpen]);

    if (!isOpen) return null;

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget && !isLoading) {
            onCancel();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape' && !isLoading) {
            onCancel();
        } else if (e.key === 'Enter' && !isLoading) {
            // Allow Enter to confirm from anywhere in the modal
            const target = e.target as HTMLElement;
            // Don't trigger if user is on the cancel button
            if (!target.classList.contains('cancel-btn')) {
                onConfirm();
            }
        }
    };

    const getAriaDescribedBy = () => {
        return type === 'danger' || type === 'warning'
            ? 'confirmation-modal-warning-message'
            : 'confirmation-modal-message';
    };

    return (
        <div
            className="confirmation-modal-overlay"
            onClick={handleOverlayClick}
            onKeyDown={handleKeyDown}
            role="presentation"
        >
            <div
                ref={modalRef}
                className={`confirmation-modal ${type}`}
                role="alertdialog"
                aria-modal="true"
                aria-labelledby="confirmation-modal-title"
                aria-describedby={getAriaDescribedBy()}
            >
                <div className="confirmation-modal-header">
                    <h3 id="confirmation-modal-title">{title}</h3>
                    <button
                        className="close-btn"
                        onClick={onCancel}
                        disabled={isLoading}
                        aria-label="Close dialog"
                    >
                        ×
                    </button>
                </div>

                <div className="confirmation-modal-body">
                    <div
                        className="confirmation-icon"
                        aria-hidden="true"
                    >
                        {type === 'danger' && '⚠️'}
                        {type === 'warning' && '⚠️'}
                        {type === 'info' && 'ℹ️'}
                    </div>
                    <p id={getAriaDescribedBy()}>{message}</p>
                </div>

                <div className="confirmation-modal-actions">
                    <button
                        className="cancel-btn"
                        onClick={onCancel}
                        disabled={isLoading}
                        aria-label={cancelButtonText}
                    >
                        {cancelButtonText}
                    </button>
                    <button
                        ref={confirmButtonRef}
                        className={`confirm-btn ${type}`}
                        onClick={onConfirm}
                        disabled={isLoading}
                        aria-label={isLoading ? 'Processing' : confirmButtonText}
                    >
                        {isLoading ? 'Processing...' : confirmButtonText}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ConfirmationModal;

